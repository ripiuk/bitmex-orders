import json
from unittest import mock
import urllib.parse as urlparse
from urllib.parse import urlencode

from django.urls import reverse
from django.test import TestCase
from rest_framework.views import status
from rest_framework.test import APITestCase, APIClient
from bravado.exception import HTTPUnauthorized, HTTPNotFound, HTTPBadRequest

from orders.models import Account, Order, Side
from orders.serializers import OrderSerializer


def _add_query_parameters_to_url(url: str, params: dict) -> str:
    url_parts = list(urlparse.urlparse(url))
    query = dict(urlparse.parse_qsl(url_parts[4]))
    query.update(params)
    url_parts[4] = urlencode(query)
    return urlparse.urlunparse(url_parts)


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
    base_post_data = {
        'symbol': 'XBTUSD',
        'volume': 1,
        'side': 'Buy',
    }

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

    def test_create_order_without_account_parameter(self):
        response = self.client.post(reverse("orders"))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('error', response.data)
        self.assertIn('account', response.data['error'])

    def test_create_order_with_not_existing_account(self):
        account_name = 'not existing'
        url = _add_query_parameters_to_url(
            reverse("orders"),
            {'account': account_name},
        )
        response = self.client.post(url, follow=True)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('error', response.data)
        self.assertIn(account_name, response.data['error'])

    @mock.patch('orders.views.bitmex')
    def test_create_order_bad_account_credentials(self, mock_bitmex):
        mock_result = mock.MagicMock()
        mock_result.Order.Order_new.return_value. \
            result.side_effect = HTTPUnauthorized(mock.MagicMock())
        mock_bitmex.return_value = mock_result

        url = _add_query_parameters_to_url(
            reverse("orders"),
            {'account': self.account_name},
        )
        response = self.client.post(url, data=self.base_post_data, follow=True)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('error', response.data)

    @mock.patch('orders.views.bitmex')
    def test_create_order_not_found(self, mock_bitmex):
        mock_result = mock.MagicMock()
        mock_result.Order.Order_new.return_value. \
            result.side_effect = HTTPNotFound(mock.MagicMock())
        mock_bitmex.return_value = mock_result

        url = _add_query_parameters_to_url(
            reverse("orders"),
            {'account': self.account_name},
        )
        response = self.client.post(url, data=self.base_post_data, follow=True)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('error', response.data)

    @mock.patch('orders.views.bitmex')
    def test_create_order_bad_request(self, mock_bitmex):
        mock_result = mock.MagicMock()
        mock_result.Order.Order_new.return_value. \
            result.side_effect = HTTPBadRequest(mock.MagicMock())
        mock_bitmex.return_value = mock_result

        url = _add_query_parameters_to_url(
            reverse("orders"),
            {'account': self.account_name},
        )
        response = self.client.post(url, data=self.base_post_data, follow=True)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    @mock.patch('orders.views.bitmex')
    def test_create_order_without_mandatory_fields(self, mock_bitmex):
        mock_result = mock.MagicMock()
        mock_result.Order.Order_new.return_value. \
            result.return_value = {}, ''
        mock_bitmex.return_value = mock_result

        url = _add_query_parameters_to_url(
            reverse("orders"),
            {'account': self.account_name},
        )
        response = self.client.post(url, data={}, follow=True)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    @mock.patch('orders.views.bitmex')
    def test_create_order_not_valid_data(self, mock_bitmex):
        mock_result = mock.MagicMock()
        mock_result.Order.Order_new.return_value. \
            result.return_value = {}, ''
        mock_bitmex.return_value = mock_result

        url = _add_query_parameters_to_url(
            reverse("orders"),
            {'account': self.account_name},
        )
        response = self.client.post(
            url,
            data=json.dumps(self.base_post_data),
            follow=True,
            content_type='application/json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('order_id', response.data)

    @mock.patch('orders.views.bitmex')
    def test_create_order_valid_data(self, mock_bitmex):
        order_id = '123-123'
        mock_result = mock.MagicMock()
        mock_result.Order.Order_new.return_value. \
            result.return_value = {'orderID': order_id}, ''
        mock_bitmex.return_value = mock_result

        url = _add_query_parameters_to_url(
            reverse("orders"),
            {'account': self.account_name},
        )
        response = self.client.post(
            url,
            data=json.dumps(self.base_post_data),
            follow=True,
            content_type='application/json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.base_post_data['symbol'], response.data['symbol'])
        self.assertEqual(self.base_post_data['volume'], response.data['volume'])
        self.assertEqual(self.base_post_data['side'], response.data['side'])
        self.assertEqual(self.account_name, response.data['account'])
        self.assertEqual(None, response.data['price'])
        self.assertEqual(order_id, response.data['order_id'])
        self.assertTrue(Order.objects.filter(id=response.data['id']).exists())


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

    def test_delete_order_with_not_existing_account(self):
        account_name = 'not existing'
        url = _add_query_parameters_to_url(
            reverse("order-detail", kwargs={'order_id': 'some order_id'}),
            {'account': account_name},
        )
        response = self.client.delete(url, follow=True)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('error', response.data)
        self.assertIn(account_name, response.data['error'])

    @mock.patch('orders.views.bitmex')
    def test_delete_order_not_found(self, mock_bitmex):
        mock_result = mock.MagicMock()
        mock_result.Order.Order_cancel.return_value.\
            result.side_effect = HTTPNotFound(mock.MagicMock())
        mock_bitmex.return_value = mock_result

        url = _add_query_parameters_to_url(
            reverse("order-detail", kwargs={'order_id': 'some order_id'}),
            {'account': self.account_name},
        )
        response = self.client.delete(url, follow=True)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('error', response.data)

    @mock.patch('orders.views.bitmex')
    def test_delete_order_bad_account_credentials(self, mock_bitmex):
        mock_result = mock.MagicMock()
        mock_result.Order.Order_cancel.return_value.\
            result.side_effect = HTTPUnauthorized(mock.MagicMock())
        mock_bitmex.return_value = mock_result

        url = _add_query_parameters_to_url(
            reverse("order-detail", kwargs={'order_id': 'some order_id'}),
            {'account': self.account_name},
        )
        response = self.client.delete(url, follow=True)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('error', response.data)

    @mock.patch('orders.views.bitmex')
    def test_delete_not_existing_order(self, mock_bitmex):
        mock_result = mock.MagicMock()
        mock_result.Order.Order_cancel.return_value. \
            result.return_value = None
        mock_bitmex.return_value = mock_result

        url = _add_query_parameters_to_url(
            reverse("order-detail", kwargs={'order_id': 'some order_id'}),
            {'account': self.account_name},
        )
        response = self.client.delete(url, follow=True)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('error', response.data)

    @mock.patch('orders.views.bitmex')
    def test_delete_order(self, mock_bitmex):
        order_id = '123-123-123-123'
        Order.objects.create(
            order_id=order_id,
            symbol='XBTUSD',
            volume=1,
            side=Side.BUY,
            price=123,
            account=self.account,
        )

        mock_result = mock.MagicMock()
        mock_result.Order.Order_cancel.return_value. \
            result.return_value = None
        mock_bitmex.return_value = mock_result

        url = _add_query_parameters_to_url(
            reverse("order-detail", kwargs={'order_id': order_id}),
            {'account': self.account_name},
        )
        response = self.client.delete(url, follow=True)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Order.objects.filter(order_id=order_id).exists())
