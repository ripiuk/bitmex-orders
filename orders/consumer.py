import json
import asyncio
import typing as typ
from collections import namedtuple

import websockets
from channels.db import database_sync_to_async
from websockets.client import WebSocketClientProtocol
from channels.generic.websocket import AsyncWebsocketConsumer

from orders.models import Account


class ReceivedDataValidationError(Exception):
    """Inappropriate data structure, value or type"""


class BitmexInstrumentConsumer(AsyncWebsocketConsumer):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        Actions = namedtuple('Actions', ('subscribe', 'unsubscribe'))
        self.actions = Actions(subscribe='subscribe', unsubscribe='unsubscribe')
        self.group_bitmex_ws: typ.Dict[str, WebSocketClientProtocol] = {}

    async def connect(self):
        await self.accept()

    async def disconnect(self, code):
        for group_name in self.group_bitmex_ws.keys():
            await self.channel_layer.group_discard(
                group_name,
                self.channel_name,
            )

    async def receive(self, text_data=None, bytes_data=None):
        try:
            received_data = await self._validate_received_data(text_data=text_data)
        except ReceivedDataValidationError:
            return

        action = received_data['action']
        account = received_data['account']

        if action == self.actions.subscribe:
            await self._subscribe_user(account)
        elif action == self.actions.unsubscribe:
            await self._unsubscribe_user(account)
        else:
            await self.send(
                text_data=json.dumps({
                    'status': 400,
                    'error': f'This action command: {action!r} is not implemented yet.',
                })
            )

    async def _validate_received_data(self, text_data: str) -> dict:
        """Received data validation

        :param text_data: received data
        :return: validated data
        :raise ReceivedDataValidationError: if data is not valid
        """
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError as err:
            await self.send(
                text_data=json.dumps({
                    'status': 400, 'error': f'Failed to decode incoming data: {err}',
                })
            )
            raise ReceivedDataValidationError

        action = data.get('action')
        account = data.get('account')

        if not action or not account:
            await self.send(
                text_data=json.dumps({
                    'status': 400, 'error': f'Got unknown data format: {text_data}',
                })
            )
            raise ReceivedDataValidationError

        if not isinstance(account, str) or not await self._is_account_exists(account):
            await self.send(
                text_data=json.dumps({
                    'status': 400, 'error': f'Account {account!r} does not exists',
                })
            )
            raise ReceivedDataValidationError

        if action not in self.actions:
            await self.send(
                text_data=json.dumps({
                    'status': 400,
                    'error': f'Got unknown action command: {action!r}. '
                             'Available commands are: '
                             f'{list(self.actions)}',
                })
            )
            raise ReceivedDataValidationError

        return data

    async def _subscribe_user(self, account: str) -> None:
        """Subscribe current user to bitmex instrument WS
            using needed account credentials

        :param account: needed account name from DB
        """
        await self.channel_layer.group_add(account, self.channel_name)

        if not (
                group_ws := self.group_bitmex_ws.get(account)
        ) or (
                group_ws
                and isinstance(group_ws, WebSocketClientProtocol)
                and not group_ws.open
        ):
            await self.bitmex_connect(account_name=account)
            await self.send(
                text_data=json.dumps({
                    'success': True, 'subscribe': 'instrument', 'account': account,
                })
            )
        else:
            await self.send(
                text_data=json.dumps({
                    'success': False, 'subscribe': 'instrument', 'account': account,
                })
            )

    async def _unsubscribe_user(self, account: str) -> None:
        """Subscribe current user from bitmex instrument WS

        :param account: account name
        :return:
        """
        if account not in self.group_bitmex_ws:
            await self.send(
                text_data=json.dumps({
                    'success': False, 'unsubscribe': 'instrument', 'account': account,
                })
            )
            return
        await self.channel_layer.group_discard(account, self.channel_name)
        await self.send(
            text_data=json.dumps({
                'success': True, 'unsubscribe': 'instrument', 'account': account,
            })
        )
        self.group_bitmex_ws.pop(account, None)

    async def send_message(self, event):
        message = event['message']
        message = json.dumps(message) if not isinstance(message, str) else message
        await self.send(text_data=message)

    @database_sync_to_async
    def _is_account_exists(self, account_name: str) -> bool:
        return Account.objects.filter(name=account_name).exists()

    async def bitmex_connect(self, account_name: str) -> None:
        """Connect to Bitmex instrument WS

        :param account_name: account name from DB
        """
        # TODO: Add API credentials here
        ws_url = "wss://testnet.bitmex.com/realtime?subscribe=instrument"

        async def monitor_data():
            async with websockets.connect(ws_url) as ws:
                self.group_bitmex_ws[account_name] = ws
                while True:
                    if not ws.open:
                        # Websocket is not connected. Trying to reconnect.
                        ws = await websockets.connect(ws_url)

                    message = await ws.recv()

                    try:
                        message = json.loads(message)
                    except json.JSONDecodeError as err:
                        await self.send(
                            text_data=json.dumps({
                                'status': 400,
                                'error': f'Failed to decode Bitmex data. '
                                         f'Message: {message}. Err: {err}',
                            })
                        )
                        continue
                    for instrument_info in self._transform_bitmex_msg(
                            message=message,
                            account=account_name):
                        await self.channel_layer.group_send(
                            account_name,
                            {
                                'type': 'send_message',
                                'message': instrument_info,
                            }
                        )
                    await asyncio.sleep(3)

        asyncio.create_task(monitor_data())

    @staticmethod
    def _transform_bitmex_msg(message: dict, account: str) -> \
            typ.List[typ.Optional[dict]]:
        """Transform bitmex message with instrument info

        :param message: bitmex instrument message
        :param account: account name
        :return: transformed message
        """
        if not message or not isinstance(message, dict) \
                or not isinstance(message.get('data'), list):
            return []
        return [
            {
                'timestamp': instrument_info.get('timestamp'),
                'account': account,
                'symbol': instrument_info.get('symbol'),
                'price': price,
            }
            for instrument_info in message['data']
            if (price := instrument_info.get('lastPrice'))
        ]
