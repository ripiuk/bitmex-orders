from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from orders.serializers import OrderSerializer
from orders.models import Account, Order


class Orders(APIView):
    """Views/create orders for the account"""

    def get(self, request):
        """Get all orders for the account"""
        if 'account' not in request.query_params:
            return Response(
                data={'error': 'Missed mandatory \'account\' parameter for the request'},
                status=status.HTTP_404_NOT_FOUND,
            )

        orders = Order.objects.all()
        serializer = OrderSerializer(orders, many=True)

        account = self.request.query_params['account']
        if not Account.objects.filter(name=account).exists():
            return Response(
                data={'error': f'Can not find this account name: {account!r}'},
                status=status.HTTP_404_NOT_FOUND,
            )

        account = Account.objects.get(name=account)
        orders = get_object_or_404(orders, account=account)
        self.check_object_permissions(self.request, orders)
        return Response(serializer.data)
