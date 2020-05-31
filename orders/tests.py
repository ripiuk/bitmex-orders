from unittest import mock

from django.urls import reverse
from django.test import TestCase
from rest_framework.views import status
from rest_framework.test import APITestCase, APIClient
from bravado.exception import HTTPUnauthorized

from orders.models import Account, Order, Side
from orders.serializers import OrderSerializer


class SideTest(TestCase):
    side_case = Side.BUY

    def setUp(self) -> None:
        self._account = Account.objects.create(
            name='test',
            api_key='test_key',
            api_secret='test_secret_key',
        )

        self.order = Order.objects.create(
            order_id='123-123-123-123',
            symbol='XBTUSD',
            volume=1,
            side=SideTest.side_case,
            price=123,
            account=self._account,
        )

    def test_created_side_is_str(self):
        order = self.order
        self.assertIsInstance(order.side, str)
        self.assertEqual(str(order.side), SideTest.side_case)

    def test_retrieved_side_is_str(self):
        order = Order.objects.last()
        self.assertIsInstance(order.side, str)
        self.assertEqual(str(order.side), SideTest.side_case)


class BaseViewTest(APITestCase):
    client = APIClient()
    account_name = 'test'

    def setUp(self) -> None:
        self.account = Account.objects.create(
            name=BaseViewTest.account_name,
            api_key='test api key',
            api_secret='test secret key',
        )


class OrdersViewTest(BaseViewTest):

    def test_without_account_parameter(self):
        response = self.client.get(reverse("orders"))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('error', response.data)
        self.assertIn('account', response.data['error'])

    def test_with_not_existing_account(self):
        account_name = 'not existing'
        response = self.client.get(reverse("orders"), {'account': account_name})

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('error', response.data)
        self.assertIn(account_name, response.data['error'])

    def test_without_orders(self):
        response = self.client.get(reverse("orders"), {'account': self.account_name})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_with_orders_for_another_account(self):
        Order.objects.create(
            order_id='123-123-123-123',
            symbol='XBTUSD',
            volume=1,
            side=Side.BUY,
            price=123,
            account=Account.objects.create(
                name='another_account',
                api_key='test api key',
                api_secret='test secret key',
            ),
        )

        response = self.client.get(reverse("orders"), {'account': self.account_name})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_all_orders_for_account(self):
        Order.objects.create(
            order_id='123-123-123-123',
            symbol='XBTUSD',
            volume=1,
            side=Side.BUY,
            price=123,
            account=self.account,
        )

        response = self.client.get(reverse("orders"), {'account': self.account_name})
        expected = Order.objects.all()
        serialized = OrderSerializer(expected, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serialized.data)


class OrderDetailViewTest(BaseViewTest):

    def test_get_order_without_account_parameter(self):
        response = self.client.get(reverse(
            "order-detail",
            kwargs={'order_id': 'some order_id'},
        ))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('error', response.data)
        self.assertIn('account', response.data['error'])

    def test_get_order_with_not_existing_account(self):
        account_name = 'not existing'
        response = self.client.get(
            reverse(
                "order-detail",
                kwargs={'order_id': 'some order_id'}),
            {'account': account_name},
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('error', response.data)
        self.assertIn(account_name, response.data['error'])

    @mock.patch('orders.views.bitmex')
    def test_get_order_bad_account_credentials(self, mock_bitmex):
        mock_result = mock.MagicMock()
        mock_result.Order.Order_getOrders.return_value.\
            result.side_effect = HTTPUnauthorized(mock.MagicMock())
        mock_bitmex.return_value = mock_result

        response = self.client.get(
            reverse(
                "order-detail",
                kwargs={'order_id': 'some order_id'}),
            {'account': self.account_name},
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('error', response.data)

    @mock.patch('orders.views.bitmex')
    def test_get_order_empty_response_from_bitmex(self, mock_bitmex):
        mock_result = mock.MagicMock()
        mock_result.Order.Order_getOrders.return_value. \
            result.return_value = [], mock.MagicMock()
        mock_bitmex.return_value = mock_result

        response = self.client.get(
            reverse(
                "order-detail",
                kwargs={'order_id': 'some order_id'}),
            {'account': self.account_name},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('error', response.data)

    @mock.patch('orders.views.bitmex')
    def test_get_order_good_response_from_bitmex(self, mock_bitmex):
        expected_data = [{
            'test_key1': 'test_value1',
            'test_key2': 'test_value2',
            'test_key3': 'test_value3',
        }]
        mock_result = mock.MagicMock()
        mock_result.Order.Order_getOrders.return_value. \
            result.return_value = expected_data, mock.MagicMock()
        mock_bitmex.return_value = mock_result

        response = self.client.get(
            reverse(
                "order-detail",
                kwargs={'order_id': 'some order_id'}),
            {'account': self.account_name},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, expected_data)

    def test_delete_order_without_account_parameter(self):
        response = self.client.delete(reverse(
            "order-detail",
            kwargs={'order_id': 'some order_id'},
        ))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('error', response.data)
        self.assertIn('account', response.data['error'])
