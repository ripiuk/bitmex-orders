from django.db import models
from django.utils.translation import gettext_lazy


class Account(models.Model):
    """Contains connecting parameters for the Bitmex exchange platform wallets"""
    name = models.CharField(unique=True, max_length=128, null=False, blank=False)
    api_key = models.CharField(max_length=256, null=False, blank=False)
    api_secret = models.CharField(max_length=256, null=False, blank=False)

    def __str__(self):
        return self.name


class Side(models.TextChoices):
    # TODO: move it inside the Order class?
    BUY = 'Buy', gettext_lazy('Buy this order')
    SELL = 'Sell', gettext_lazy('Sell this order')


class Order(models.Model):
    """Contains detailed information about orders"""
    order_id = models.CharField(max_length=128, null=False, blank=False)
    symbol = models.CharField(max_length=8, null=False, blank=False)
    volume = models.PositiveIntegerField(null=False, blank=False)
    timestamp = models.DateTimeField(auto_now_add=False, auto_now=True)
    side = models.CharField(max_length=9, blank=False, choices=Side.choices)
    price = models.FloatField(blank=False)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, null=False)

    def __str__(self):
        return f'{self.order_id} {self.account.name} {self.side} ' \
               f'{self.volume} {self.price} {self.symbol}'
