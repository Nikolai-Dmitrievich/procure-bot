from rest_framework import serializers
from backend.models import ProductInfo, Product, Shop, ProductParameter, Contact, Order, OrderItem


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = '__all__'


class ProductSerializer(serializers.ModelSerializer):

    class Meta:
        model = Product
        fields = ['id', 'name', 'description']


class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    class Meta:
        model = OrderItem
        fields = '__all__'


class OrderSerializer(serializers.ModelSerializer):
    order_item = OrderItemSerializer(many=True, read_only=True)
    class Meta:
        model = Order
        fields = '__all__'


class ShopSerializer(serializers.ModelSerializer):

    class Meta:
        model = Shop
        fields = ['id', 'name']

class ProductParameterSerializer(serializers.ModelSerializer):

    parameter = serializers.CharField(source='parameter.name')
    class Meta:
        model = ProductParameter
        fields = ['parameter', 'value']

class ProductInfoSerializer(serializers.ModelSerializer):
    
    product = ProductSerializer()
    shop = ShopSerializer()
    parameters = ProductParameterSerializer(source='product_parameters', many=True)
    
    class Meta:
        model = ProductInfo
        fields = [
            'id', 'model', 'external_id', 'quantity', 'price', 'price_rrc',
            'product', 'shop', 'parameters'
        ]