from django.urls import include, path

from orders.views import Orders

urlpatterns = [
    path('', Orders.as_view(), name='orders'),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework'))
]
