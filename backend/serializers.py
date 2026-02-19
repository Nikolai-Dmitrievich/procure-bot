from rest_framework import serializers
from backend.models import (
    ProductInfo, Product, Shop, ProductParameter, Contact, Order, OrderItem
)


class PartnerUpdateSerializer(serializers.Serializer):
    """Сериализатор для обновления прайса партнера"""
    url = serializers.URLField(required=False)
    price_file = serializers.FileField(required=False)

    def validate(self, data):
        if not (data.get('url') or data.get('price_file')):
            raise serializers.ValidationError("Требуется URL ИЛИ файл")
        return data


class ContactSerializer(serializers.ModelSerializer):
    """Сериализатор контактной информации"""
    user_name = serializers.CharField(source='user.username', read_only=True)
    full_address = serializers.SerializerMethodField()

    class Meta:
        model = Contact
        fields = '__all__'
        extra_kwargs = {
            'user': {'write_only': True}
        }

    def get_full_address(self, obj):
        return f"{obj.street}, {obj.city}" if obj.street else obj.city


class ProductSerializer(serializers.ModelSerializer):
    """Сериализатор продукта"""
    category_name = serializers.CharField(
        source='category.name',
        read_only=True
        )

    class Meta:
        model = Product
        fields = ['id', 'name', 'description', 'category_name']


class OrderItemSerializer(serializers.ModelSerializer):
    """Сериализатор позиции заказа"""
    product_name = serializers.CharField(
        source='product_info.product.name', read_only=True
    )
    product_model = serializers.CharField(
        source='product_info.model', read_only=True
    )
    shop_name = serializers.CharField(
        source='product_info.shop.name', read_only=True
    )

    class Meta:
        model = OrderItem
        fields = ['product_name', 'product_model', 'shop_name', 'quantity']


class OrderSerializer(serializers.ModelSerializer):
    """Сериализатор заказа с вложенными позициями"""
    ordered_items = OrderItemSerializer(many=True, read_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id',
            'ordered_items',
            'total_price',
            'dt',
            'state',
            'contact'
            ]

    def get_total_price(self, obj):
        return sum(
            item.quantity * item.product_info.price
            for item in obj.ordered_items.all()
        )


class ShopSerializer(serializers.ModelSerializer):
    """Сериализатор магазина"""

    class Meta:
        model = Shop
        fields = ['id', 'name']


class ProductParameterSerializer(serializers.ModelSerializer):
    """Сериализатор параметров продукта"""
    parameter = serializers.CharField(source='parameter.name')

    class Meta:
        model = ProductParameter
        fields = ['parameter', 'value']


class ProductInfoSerializer(serializers.ModelSerializer):
    """Детальный сериализатор информации о продукте"""
    product = ProductSerializer()
    shop = ShopSerializer()
    parameters = ProductParameterSerializer(
        source='product_parameters', many=True
    )
    in_stock = serializers.SerializerMethodField()

    class Meta:
        model = ProductInfo
        fields = [
            'id', 'model', 'external_id', 'quantity', 'price', 'price_rrc',
            'in_stock', 'product', 'shop', 'parameters'
        ]

    def get_in_stock(self, obj):
        return obj.quantity > 0


class BasketSerializer(serializers.Serializer):
    """Сериализатор корзины"""
    product_info_id = serializers.IntegerField()
    quantity = serializers.IntegerField(default=1, min_value=1)
