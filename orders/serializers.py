from rest_framework import serializers

from orders.models import Account, Order


class _AccountSerializer(serializers.ModelSerializer):
    account = serializers.CharField(read_only=True)

    class Meta:
        model = Account


class OrderSerializer(serializers.ModelSerializer):
    account = serializers.CharField(source='account.name', read_only=True)

    class Meta:
        model = Order
        fields = (
            'order_id',
            'symbol',
            'volume',
            'timestamp',
            'side',
            'price',
            'account',
        )
