from django.urls import include, path

from orders.views import Orders, OrderDetail

urlpatterns = [
    path('orders/', Orders.as_view(), name='orders'),
    path('orders/<str:order_id>/', OrderDetail.as_view(), name='order-detail'),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework'))
]
