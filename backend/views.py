import json
from django.core.validators import URLValidator
from django.http import JsonResponse
from rest_framework.views import APIView
from requests import get
from django.core.exceptions import ValidationError

from .models import Shop, Category, Product, ProductInfo, Parameter, ProductParameter

class PartnerUpdate(APIView):
    """
    Класс для обновления прайса от поставщика JSON
    """
    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Only for shops'}, status=403)
        
        url = request.data.get('url')
        if url:
            validate_url = URLValidator()
            try:
                validate_url(url)
                stream = get(url).content.decode('utf-8')
                data = json.loads(stream)
            except ValidationError as e:
                return JsonResponse({'Status': False, 'Error': str(e)})
            except json.JSONDecodeError as e:
                return JsonResponse({'Status': False, 'Error': f'Invalid JSON: {str(e)}'})
            
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

            return JsonResponse({
                'Status': True
            })

        return JsonResponse({'Status': False, 'Errors': 'URL not provided'})