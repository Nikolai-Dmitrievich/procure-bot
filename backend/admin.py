from django.contrib import admin
from .models import (
    ProductInfo, Shop, Category, Product, Order, OrderItem, Contact,
    Parameter, ProductParameter
)
from .tasks import send_email
from django.utils.html import format_html


class ProductParameterInline(admin.TabularInline):
    """Инлайн для параметров товара"""
    model = ProductParameter
    extra = 1
    fields = ('parameter', 'value')


@admin.register(ProductInfo)
class ProductInfoAdmin(admin.ModelAdmin):
    """Админка для ProductInfo"""
    list_display = [
        'product',
        'shop',
        'model',
        'price',
        'quantity',
        'get_low_stock'
        ]
    list_filter = ['shop', 'quantity', 'price']
    search_fields = ['product__name', 'model', 'external_id']
    list_editable = ['price', 'quantity']
    inlines = [ProductParameterInline]
    list_per_page = 50

    def get_low_stock(self, obj):
        """Отображает статус запаса"""
        return "Низкий" if obj.quantity < 10 else "В наличии"
    get_low_stock.short_description = 'Запас'


class OrderItemInline(admin.TabularInline):
    """Инлайн для позиций заказа"""
    model = OrderItem
    fields = ('product_info', 'quantity')
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Админка для заказов"""
    list_display = ['id', 'user', 'state', 'dt', 'get_total_price']
    list_filter = ['state', 'dt']
    search_fields = ['user__email', 'id']
    inlines = [OrderItemInline]
    list_per_page = 20
    actions = ['confirm_orders', 'send_orders']

    def get_total_price(self, obj):
        """Рассчитывает общую сумму заказа"""
        total = sum(
            item.quantity * item.product_info.price
            for item in obj.ordered_items.all()
            )
        return f"{total:,.0f}₽"
    get_total_price.short_description = 'Сумма'

    @admin.action(description='Подтвердить заказы')
    def confirm_orders(self, request, queryset):
        """Массовое подтверждение заказов"""
        count = queryset.update(state='confirmed')
        self.message_user(request, f'Подтверждено заказов: {count}')

    @admin.action(description='Отправить заказы')
    def send_orders(self, request, queryset):
        """Массовое изменение статуса + отправка писем"""
        order_ids = [order.id for order in queryset]
        count = queryset.update(state='sent')
        send_email.delay(order_ids)
        self.message_user(request, f'Отправлено заказов: {count}')


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    """Админка для магазинов"""
    list_display = ['name', 'state', 'user']
    list_filter = ['state']
    search_fields = ['name']


 



@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['get_image_preview', 'name', 'category']
    
    def get_image_preview(self, obj):
        if obj.image and obj.image.url:
            return format_html(
                '<img src="{}" style="width:80px;height:80px;object-fit:cover;border-radius:5px;">',
                obj.image.url
            )
        return 'Нет'
    get_image_preview.short_description = 'Фото'

