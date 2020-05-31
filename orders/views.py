import json

from bitmex import bitmex
from django.conf import settings
from rest_framework import status
from django.http import HttpResponse
from rest_framework.views import APIView
from django.http.request import QueryDict
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from bravado.exception import HTTPNotFound, HTTPUnauthorized, HTTPBadRequest

from orders.serializers import OrderSerializer
from orders.models import Account, Order


BITMEX_TEST_MODE = settings.DEBUG


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

    @staticmethod
    def post(request):
        """Create new order for an account"""
        try:
            account_name = request.query_params.get('account')
            account = _get_account_(account_name)
        except AccountNotFound as err:
            return Response(
                data={'error': str(err)},
                status=status.HTTP_404_NOT_FOUND,
            )

        client = bitmex(
            test=BITMEX_TEST_MODE,
            api_key=account.api_key,
            api_secret=account.api_secret,
        )
        try:
            # FIXME: it always raises error:
            #  "Account has insufficient Available Balance"
            result, _ = client.Order.Order_new(
                symbol=request.data['symbol'],
                orderQty=request.data['volume'],
                side=request.data['side'],
                ordType='Market',
            ).result()
        except HTTPUnauthorized as err:
            return Response(
                data={'error': str(err)},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        except HTTPNotFound as err:
            return Response(
                data={'error': str(err)},
                status=status.HTTP_404_NOT_FOUND,
            )
        except HTTPBadRequest as err:
            return Response(
                data={'error': str(err)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except KeyError as err:
            return Response(
                data={'error': f'Missed mandatory field {err}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = OrderSerializer(
            data={
                **request.data,
                'order_id': result.get('orderID'),
                'price': result.get('price'),
                'account': account.id,
            }
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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
            test=BITMEX_TEST_MODE,
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
            test=BITMEX_TEST_MODE,
            api_key=account.api_key,
            api_secret=account.api_secret,
        )
        try:
            client.Order.Order_cancel(orderID=order_id).result()
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
