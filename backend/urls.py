from django.urls import path
from . import views


urlpatterns = [
    path('basket/', views.BasketView.as_view(), name='basket'),
    path(
        'basket/clear/',
        views.BasketClearView.as_view(),
        name='basket-clear'
        ),
    path(
        'contacts/',
        views.ContactListCreateView.as_view(),
        name='contacts-list'
        ),
    path(
        'contacts/<int:pk>/',
        views.ContactUpdateDeleteView.as_view(),
        name='contacts-detail'
        ),
    path(
        'partners/update/',
        views.PartnerUpdate.as_view(),
        name='partner_update'
        ),
    path(
        'partners/orders/',
        views.PartnerOrders.as_view(),
        name='partner_orders'
        ),
    path(
        'partners/state/',
        views.PartnerState.as_view(),
        name='partner_state'
        ),
    path('products/', views.ProductListView.as_view()),
    path('products/<int:pk>/', views.ProductDetailView.as_view()),
    path(
        'orders/create/',
        views.OrderCreateView.as_view(),
        name='order_create'
        ),
    path('orders/', views.OrderListView.as_view()),
    path(
        'orders/<int:pk>/',
        views.OrderDetailView.as_view(),
        name='order_detail'
        ),
    path(
        'orders/<int:pk>/status/',
        views.OrderStatusUpdateView.as_view(),
        name='order_status'
        ),
    path('admin/stats/', views.admin_stats, name='admin-stats'),
    path('admin/low-stock/', views.low_stock_list, name='admin-low-stock'),
    path('api/v1/partners/export/', views.PartnerExport.as_view()),
]
