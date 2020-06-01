from django.urls import path
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter

from orders.consumer import BitmexInstrumentConsumer


application = ProtocolTypeRouter({
    'websocket': AuthMiddlewareStack(
        URLRouter([
            path('instrument/', BitmexInstrumentConsumer)
        ])
    )
})
