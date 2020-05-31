import json

from bitmex import bitmex
from rest_framework import status
from django.http import HttpResponse
from rest_framework.views import APIView
from django.http.request import QueryDict
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from bravado.exception import HTTPNotFound, HTTPUnauthorized

from orders.serializers import OrderSerializer
from orders.models import Account, Order


class Orders(APIView):
    """Views/create orders for an account"""

    def get(self, request):
        """Get all orders for an account"""
        try:
            account_name = request.query_params.get('account')
            account = _get_account_(account_name)
        except AccountNotFound as err:
            return Response(
                data={'error': str(err)},
                status=status.HTTP_404_NOT_FOUND,
            )

        orders = Order.objects.all()
        serializer = OrderSerializer(orders, many=True)
        orders = get_object_or_404(orders, account=account)
        self.check_object_permissions(request, orders)
        return Response(serializer.data)


class OrderDetail(APIView):
    """View/delete order for an account"""

    @staticmethod
    def get(request, order_id):
        """Show order info for an account"""
        account_name = request.query_params.get('account')
        try:
            account = _get_account_(account_name)
        except AccountNotFound as err:
            return Response(
                data={'error': str(err)},
                status=status.HTTP_404_NOT_FOUND,
            )

        client = bitmex(
            test=True,
            api_key=account.api_key,
            api_secret=account.api_secret,
        )
        filter_ = json.dumps({'orderID': order_id})
        try:
            result, _ = client.Order.Order_getOrders(filter=filter_).result()
        except HTTPUnauthorized as err:
            return Response(
                data={'error': str(err)},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not result:
            return Response(
                data={
                    'error': f'Can not find any order with order id: {order_id!r} '
                             f'for the account name: {account.name!r}'
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(result)

    @staticmethod
    def delete(request, order_id):
        """Remove/Cancel order for an account"""
        try:
            account_name = request.query_params.get('account')
            account = _get_account_(account_name)
        except AccountNotFound as err:
            return Response(
                data={'error': str(err)},
                status=status.HTTP_404_NOT_FOUND,
            )

        client = bitmex(
            test=True,
            api_key=account.api_key,
            api_secret=account.api_secret,
        )
        try:
            result, _ = client.Order.Order_cancel(orderID=order_id).result()
        except HTTPNotFound as err:
            return Response(
                data={'error': str(err)},
                status=status.HTTP_404_NOT_FOUND,
            )
        except HTTPUnauthorized as err:
            return Response(
                data={'error': str(err)},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        else:
            orders = Order.objects.filter(order_id=order_id, account__name=account.name)
            if not orders.exists():
                return Response(
                    data={
                        'error': f'Can not find any order with order id: {order_id!r} '
                                 f'for the account name: {account.name!r}'
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )
        orders.delete()
        return HttpResponse(status=204)


class AccountNotFound(Exception):
    """Can not find an account"""


def _get_account_(account_name: QueryDict) -> Account:
    """Get account model by account name

    :param account_name: needed account name
    :return: needed account model
    :raise AccountNotFound: if account does not exists
    """
    if not account_name:
        raise AccountNotFound('Missed mandatory \'account\' parameter for the request')

    try:
        account = Account.objects.get(name=account_name)
    except Account.DoesNotExist:
        raise AccountNotFound(f'Can not find this account name: {account_name!r}')
    return account
