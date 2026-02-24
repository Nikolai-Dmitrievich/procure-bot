from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Prefetch
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import filters
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.generics import (
    ListAPIView,
    RetrieveAPIView,
    ListCreateAPIView
    )
from rest_framework.decorators import api_view, permission_classes
from rest_framework.throttling import AnonRateThrottle
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import (
    extend_schema_view,
    extend_schema,
    OpenApiTypes,
    OpenApiParameter,
)

from backend.serializers import (
    ContactSerializer,
    OrderSerializer,
    ProductInfoSerializer,
    BasketSerializer,
    PartnerUpdateSerializer,
)
from backend.services import BasketService, redis_client
from .models import Order, OrderItem, Shop, ProductInfo, Contact
from .tasks import partner_export, partner_import, send_email
from users.models import User


@extend_schema_view(
    post=extend_schema(
        tags=['Поставщики'],
        request=PartnerUpdateSerializer,
        responses={200: OpenApiTypes.ANY},
    )
)
class PartnerUpdate(APIView):
    """
    Обновление прайса от поставщика (JSON/YAML).
    Принимает URL прайса или загруженный файл.
    Запускает асинхронную задачу импорта через Celery.
    """
    serializer_class = PartnerUpdateSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        if request.user.type != 'shop':
            return Response(
                {'status': False, 'error': 'Only for shops'},
                status=403
            )

        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        url = serializer.validated_data.get('url')
        price_file = serializer.validated_data.get('price_file')

        if price_file:
            file_content = b''
            for chunk in price_file.chunks():
                file_content += chunk
            
            task = partner_import.delay(file_content, request.user.id)

        else:
            task = partner_import.delay(url, request.user.id)

        return Response({
            'status': True,
            'task_id': task.id,
            'message': 'Импорт запущен в фоне!'
        }, status=202)


@extend_schema_view(
    get=extend_schema(
        tags=['Товары'],
        parameters=[
            OpenApiParameter(
                name='shop',
                type=int,
                location=OpenApiParameter.QUERY
                ),
            OpenApiParameter(
                name='price',
                type=int,
                location=OpenApiParameter.QUERY
                ),
        ]
    )
)
class ProductListView(ListAPIView):
    """
    Список товаров с фильтрацией, поиском и сортировкой.
    Поддерживает фильтрацию по цене, количеству, магазину.
    Поиск по названию продукта и модели.
    """
    throttle_classes = [AnonRateThrottle]
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


@extend_schema_view(
    get=extend_schema(tags=['Корзина']),
    post=extend_schema(
        tags=['Корзина'],
        request=BasketSerializer,
        responses={200: OpenApiTypes.ANY}
    ),
    delete=extend_schema(
        tags=['Корзина'],
        operation_id='basket_remove',
        request=BasketSerializer,
        responses={200: OpenApiTypes.ANY}
    )
)
class BasketView(APIView):
    """Управление корзиной покупок пользователя"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        basket = BasketService.get(request.user.id)
        if not basket:
            return Response({
                "basket": {},
                "total_price": 0,
                "items_count": 0
            })

        basket_items = {}
        total_price = 0

        for product_id_str, qty_str in basket.items():
            try:
                product_info = ProductInfo.objects.select_related(
                    'product__category', 'shop'
                ).get(id=product_id_str)

                qty = int(qty_str)
                item_total = qty * product_info.price
                total_price += item_total

                basket_items[product_id_str] = {
                    'quantity': qty,
                    'name': product_info.product.name,
                    'model': product_info.model or 'Нет модели',
                    'category': product_info.product.category.name,
                    'shop': product_info.shop.name,
                    'price': float(product_info.price),
                    'total': float(item_total),
                    'in_stock': product_info.quantity >= qty
                }
            except ProductInfo.DoesNotExist:
                BasketService.remove(request.user.id, product_id_str)
                continue

        return Response({
            'basket': basket_items,
            'total_price': float(total_price),
            'items_count': len(basket_items)
        })

    def post(self, request):
        serializer = BasketSerializer(data=request.data)
        if serializer.is_valid():
            product_info_id = serializer.validated_data['product_info_id']
            quantity = serializer.validated_data.get('quantity', 1)
            BasketService.add(request.user.id, product_info_id, quantity)
            return Response({"status": "added"})
        return Response(serializer.errors, status=400)


@extend_schema(
    tags=['Корзина'],
    operation_id='basket_clear',
    methods=['DELETE'],
    responses={200: OpenApiTypes.ANY}
)
class BasketClearView(APIView):
    """Очистка корзины пользователя"""
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        BasketService.clear(request.user.id)
        return Response({"status": "basket_cleared"})


@extend_schema_view(
    get=extend_schema(
        tags=['Товары'],
        responses={200: ProductInfoSerializer}
    )
)
class ProductDetailView(APIView):
    """Детальная информация о товаре"""
    throttle_classes = [AnonRateThrottle]

    def get(self, request, pk):
        product_info = get_object_or_404(ProductInfo, pk=pk)
        serializer = ProductInfoSerializer(product_info)
        return Response(serializer.data)


@extend_schema_view(
    get=extend_schema(
        tags=['Контакты'],
        operation_id='contacts_list',
        responses={200: ContactSerializer(many=True)}
    ),
    post=extend_schema(
        tags=['Контакты'],
        operation_id='contacts_create',
        request=ContactSerializer,
        responses={201: ContactSerializer}
    )
)
class ContactListCreateView(ListCreateAPIView):
    """
    Список и создание контактов пользователя.
    Только свои контакты доступны для просмотра/создания.
    """
    serializer_class = ContactSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Contact.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


@extend_schema_view(
    patch=extend_schema(
        tags=['Контакты'],
        operation_id='contacts_update',
        request=ContactSerializer,
        responses={200: ContactSerializer}
    ),
    delete=extend_schema(
        tags=['Контакты'],
        operation_id='contacts_delete',
        responses={200: OpenApiTypes.ANY}
    )
)
class ContactUpdateDeleteView(APIView):
    """Обновление и удаление контакта пользователя."""
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        contact = get_object_or_404(Contact, pk=pk, user=request.user)
        serializer = ContactSerializer(
            contact,
            data=request.data,
            partial=True
            )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    def delete(self, request, pk):
        contact = get_object_or_404(Contact, pk=pk, user=request.user)
        contact.delete()
        return Response({'status': 'deleted'})


@extend_schema_view(
    post=extend_schema(
        tags=['Заказы'],
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'contact_id': {'type': 'integer', 'example': 1}
                },
                'required': ['contact_id']
            }
        },
        responses={200: OpenApiTypes.ANY}
    )
)
class OrderCreateView(APIView):
    """
    Создание заказа из корзины.
    Проверяет наличие товаров на складе, создает OrderItem,
    уменьшает остатки, отправляет email-уведомление.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        basket = BasketService.get(request.user.id)
        if not basket:
            return Response({"error": "Корзина пуста"}, status=400)

        contact_id = request.data.get('contact_id')
        contact = get_object_or_404(Contact, id=contact_id, user=request.user)

        total_price = 0
        product_quantities = []

        for product_id_str, qty_str in basket.items():
            product_info = get_object_or_404(ProductInfo, id=product_id_str)
            qty = int(qty_str)

            if product_info.quantity < qty:
                return Response({
                    "error": f"Недостаточно '{product_info.product.name}'",
                    "available": product_info.quantity,
                    "needed": qty
                }, status=400)

            total_price += qty * product_info.price
            product_quantities.append((product_info, qty))

        with transaction.atomic():
            order = Order.objects.create(
                user=request.user,
                contact=contact,
                state='new'
            )

            for product_info, quantity in product_quantities:
                product_info = ProductInfo.objects.select_for_update().get(
                    id=product_info.id
                )
                product_info.quantity -= quantity
                product_info.save(update_fields=['quantity'])

                order_item = OrderItem(
                    order=order,
                    product_info=product_info,
                    quantity=quantity
                )
                order_item.save()

        redis_client.delete(f'basket_{request.user.id}')
        send_email.delay(order.id)

        return Response({
            'order_id': order.id,
            'total_price': float(total_price),
            'status': 'created'
        })


@extend_schema_view(
    get=extend_schema(
        tags=['Заказы'],
        responses={200: OrderSerializer(many=True)}
    )
)
class OrderListView(ListAPIView):
    """Список заказов пользователя."""
    serializer_class = OrderSerializer

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).select_related(
            'contact', 'user'
        ).prefetch_related(
            'ordered_items__product_info__product__category',
            'ordered_items__product_info__shop'
        ).order_by('-dt')


@extend_schema_view(
    get=extend_schema(
        tags=['Заказы'],
        responses={200: OrderSerializer}
    )
)
class OrderDetailView(RetrieveAPIView):
    """Детальная информация о заказе."""
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        order = get_object_or_404(
            Order.objects.select_related('contact').prefetch_related(
                'ordered_items__product_info__product'
            ),
            id=self.kwargs['pk'],
            user=self.request.user
        )
        return order


@extend_schema_view(
    patch=extend_schema(
        tags=['Заказы'],
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'state': {
                        'type': 'string',
                        'enum': ['new', 'confirmed', 'sent', 'delivered']
                    }
                }
            }
        },
        responses={200: OpenApiTypes.ANY}
    )
)
class OrderStatusUpdateView(APIView):
    """
    Обновление статуса заказа.
    Доступно только для заказов с товарами своего магазина.
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        order = get_object_or_404(
            Order.objects.filter(
                ordered_items__product_info__shop__user=request.user
            ),
            id=pk
        )
        new_state = request.data.get('state')
        if new_state in ['new', 'confirmed', 'sent', 'delivered']:
            order.state = new_state
            order.save()
            return Response({'status': new_state})
        return Response({'error': 'Invalid state'}, status=400)


@extend_schema_view(
    get=extend_schema(tags=['Поставщики'], responses={200: OpenApiTypes.ANY}),
    post=extend_schema(
        tags=['Поставщики'],
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'state': {'type': 'boolean'}
                }
            }
        }
    )
)
class PartnerState(APIView):
    """Управление состоянием магазина-поставщика"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.type != 'shop':
            return Response({'error': 'Только для магазинов'}, status=403)
        shop = request.user.shop
        return Response({
            'id': shop.id,
            'name': shop.name,
            'state': shop.state,
            'state_display': shop.get_state_display(),
            'owner': request.user.username
        })

    def post(self, request):
        state = request.data.get('state')
        Shop.objects.filter(user=request.user).update(state=state)
        return Response({'status': True})


@extend_schema_view(
    get=extend_schema(
        tags=['Поставщики'],
        responses={200: OrderSerializer(many=True)}
    )
)
class PartnerOrders(ListAPIView):
    """Заказы для магазина-поставщика."""
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.type != 'shop':
            return Order.objects.none()
        return Order.objects.filter(
            ordered_items__product_info__shop__user=self.request.user
        ).select_related('contact', 'user').prefetch_related(
            'ordered_items__product_info__product__category',
            'ordered_items__product_info__shop'
        ).order_by('-dt')


@extend_schema(tags=['Admin'])
@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_stats(request):
    """
    Админская статистика.
    Склад: общее количество товаров, доступных, с низким остатком.
    Заказы: количество, выручка.
    Пользователи и магазины.
    """
    stats = {
        'warehouse': {
            'total_products': ProductInfo.objects.count(),
            'available': ProductInfo.objects.filter(quantity__gt=0).count(),
            'low_stock': ProductInfo.objects.filter(quantity__lt=10).count(),
        },
        'orders': {
            'total': Order.objects.count(),
            'revenue': 0.0
        },
        'shops': Shop.objects.count(),
        'users': {
            'total': User.objects.count(),
            'shops': User.objects.filter(type='shop').count(),
        }
    }
    return Response(stats)


@extend_schema(tags=['Admin'])
@api_view(['GET'])
@permission_classes([IsAdminUser])
def low_stock_list(request):
    """
    Список товаров с низким остатком (<10).
    Ограничено 20 товарами, содержит информацию о магазине и цене.
    """
    products = ProductInfo.objects.filter(quantity__lt=10).select_related(
        'product', 'shop'
    )[:20]
    return Response([{
        'id': p.id,
        'name': p.product.name,
        'shop': p.shop.name,
        'price': p.price,
        'stock': p.quantity
    } for p in products])


@extend_schema_view(
    post=extend_schema(
        tags=['Поставщики'],
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'shop_id': {'type': 'integer'}
                }
            }
        },
        responses={202: OpenApiTypes.ANY}
    )
)
class PartnerExport(APIView):
    """Экспорт прайса магазина в фоновом режиме"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.type != 'shop':
            return Response({'error': 'Только магазины'}, status=403)
        task = partner_export.delay(request.user.shop.id)
        return Response({
            'task_id': task.id,
            'message': 'Экспорт запущен!'
        }, 202)
