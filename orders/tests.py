from django.test import TestCase
from orders.models import Account, Order, Side


class SideTest(TestCase):
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
            side=Side.BUY,
            price=123,
            account=self._account,
        )

    def test_created_side_is_str(self):
        order = self.order
        self.assertIsInstance(order.side, str)
        self.assertEqual(str(order.side), Side.BUY)

    def test_retrieved_side_is_str(self):
        order = Order.objects.last()
        self.assertIsInstance(order.side, str)
        self.assertEqual(str(order.side), Side.BUY)
