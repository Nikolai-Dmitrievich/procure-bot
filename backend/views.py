import json
from django.conf import settings
from django.core.validators import URLValidator
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from requests import get
from django.core.exceptions import ValidationError
from rest_framework.response import Response
from backend.serializers import ContactSerializer, OrderSerializer, ProductInfoSerializer
from django.db.models import Prefetch
from .models import Order, OrderItem, Shop, Category, Product, ProductInfo, Parameter, ProductParameter, Contact
from rest_framework import filters, status
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from backend.services import BasketService, redis_client
from django.core.mail import send_mail

class PartnerUpdate(APIView):
    """
    Класс для обновления прайса от поставщика JSON
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        
        if request.user.type != 'shop':
            return Response({'status': False, 'error': 'Only for shops'}, status=403)
        
        url = request.data.get('url')
        if url:
            validate_url = URLValidator()
            try:
                validate_url(url)
                stream = get(url).content.decode('utf-8')
                data = json.loads(stream)
            except ValidationError as e:
                return Response({'status': False, 'error': str(e)})
            except json.JSONDecodeError as e:
                return Response({'status': False, 'error': f'Invalid JSON: {str(e)}'})
            
            shop, _ = Shop.objects.get_or_create(
                name=data['shop'], 
                user=request.user,
                defaults={'state': 'active'}
            )
            
            for category in data['categories']:
                category_object, _ = Category.objects.get_or_create(
                    id=category['id'], 
                    defaults={'name': category['name']}
                )
                category_object.shops.add(shop)
            
            ProductInfo.objects.filter(shop=shop).delete()
            
            for item in data['goods']:
                product, _ = Product.objects.get_or_create(
                    name=item['name'], 
                    defaults={'category_id': item['category']}
                )
                
                product_info = ProductInfo.objects.create(
                    product=product,
                    external_id=item['id'],
                    model=item.get('model', ''),
                    price=item['price'],
                    price_rrc=item['price_rrc'],
                    quantity=item['quantity'],
                    shop=shop
                )
                
                for name, value in item['parameters'].items():
                    parameter_object, _ = Parameter.objects.get_or_create(name=name)
                    ProductParameter.objects.create(
                        product_info=product_info,
                        parameter=parameter_object,
                        value=str(value)
                    )

            return Response({
                'status': True
            })

        return Response({'status': False, 'error': 'URL not provided'})
    
class ProductListView(ListAPIView):
    queryset = ProductInfo.objects.select_related(
        'product__category', 'shop'
    ).prefetch_related(
        Prefetch('product_parameters__parameter')
    )
    serializer_class = ProductInfoSerializer
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter
    ]
    filterset_fields = ['price', 'quantity', 'shop']
    search_fields = ['product__name', 'model']
    ordering_fields = ['price', 'quantity']


class BasketView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        basket = BasketService.get(request.user.id)
        return Response({"basket": basket})
    
    def post(self, request):
        product_info_id = request.data.get('product_info_id')
        if not product_info_id:
            return Response({"error": "product_info_id required"}, status=400)
        quantity = request.data.get('quantity', 1)
        BasketService.add(request.user.id, product_info_id, quantity)
        return Response({"status": "added"})
    
    def delete(self, request):
        product_info_id = request.data.get('product_info_id')
        if not product_info_id:
            return Response({"error": "product_info_id required"}, status=400)
        BasketService.remove(request.user.id, product_info_id)
        return Response({"status": "removed"})
    
class ProductDetailView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, pk):
        product_info = get_object_or_404(ProductInfo, pk=pk)
        serializer = ProductInfoSerializer(product_info)
        return Response(serializer.data)
    
class ContactView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        contacts = Contact.objects.filter(user=request.user)
        serializer = ContactSerializer(contacts, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        data = request.data.copy()
        data['user'] = request.user.id
        serializer = ContactSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        contact = get_object_or_404(Contact, pk=pk, user=request.user)
        contact.delete()
        return Response({'status': 'deleted'})

class OrderCreateView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        basket = BasketService.get(request.user.id)
        if not basket:
            return Response({"error": "Корзина пуста"}, status=400)
        
        contact_id = request.data.get('contact_id')
        contact = get_object_or_404(Contact, id=contact_id, user=request.user)
        
        total_price = 0
        order_items = []
        for product_id_str, qty_str in basket.items():
            product_info = get_object_or_404(ProductInfo, id=product_id_str)
            qty = int(qty_str)
            total_price += qty * product_info.price
            order_items.append(OrderItem(product_info=product_info, quantity=qty))
        
        order = Order.objects.create(
            user=request.user,
            contact=contact,
            state='new'
        )
        
        for item in order_items:
            item.order = order
            item.save()
        
        from backend.services import redis_client
        redis_client.delete(f'basket_{request.user.id}')
        try:
            send_mail(
                f'Подтверждение заказа №{order.id}',
                f'Ваш заказ №{order.id} на сумму {total_price}₽ создан!',
                settings.DEFAULT_FROM_EMAIL,
                [request.user.email],
                fail_silently=True,
            )
        except Exception as e:
            print(f"Email не отправлен для заказа #{order.id}: {e}")
            
        return Response({
            'order_id': order.id,
            'total_price': float(total_price),
            'status': 'created'
        })

class OrderListView(ListAPIView):
    serializer_class = OrderSerializer
    
    def get_queryset(self):
        return Order.objects.filter(
            user=self.request.user
        ).select_related('contact').prefetch_related(
            'ordered_items__product_info'
        ).order_by('-dt')
    
class OrderDetailView(RetrieveAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    def get_object(self):
        order = get_object_or_404(
            Order.objects.select_related('contact').prefetch_related('ordered_items__product_info__product'),
            id=self.kwargs['pk'],
            user=self.request.user
        )
        return order
    
class OrderStatusUpdateView(APIView):
    permission_classes = [IsAuthenticated]
    
    def patch(self, request, pk):
        order = get_object_or_404(Order, id=pk, user=request.user)
        new_state = request.data.get('state')
        if new_state in ['new', 'confirmed', 'sent', 'delivered']:
            order.state = new_state
            order.save()
            return Response({'status': new_state})
        return Response({'error': 'Invalid state'}, status=400)


class PartnerState(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        if request.user.type != 'shop': 
            return Response({'error': 'Только для магазинов'}, status=403)
        shop = request.user.shop
        return Response({'state': shop.state})
    
    def post(self, request):
        state = request.data.get('state')
        Shop.objects.filter(user=request.user).update(state=state)
        return Response({'status': True})

class PartnerOrders(ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    def get_queryset(self):
        if self.request.user.type != 'shop':
            return Order.objects.none()
        return Order.objects.filter(
            ordered_items__product_info__shop__user=self.request.user
        ).select_related('contact').prefetch_related(
            'ordered_items__product_info__product'
        ).order_by('-dt')


