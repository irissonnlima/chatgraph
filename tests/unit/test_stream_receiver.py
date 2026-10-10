# ruff: noqa: PLR2004, PLR6301 - testes em classe e literais nos asserts, como no
# resto da suíte.
import asyncio
import copy
import logging

import pytest
from websockets.asyncio.client import ClientConnection

from chatgraph.stream.errors import InvalidDeliveryError
from tests.unit.stream_fake_router import (
    ConnScript,
    eventually,
    make_deliver,
    stream_client,
)


def acks(conn) -> list[dict]:
    return conn.of_type('ack')


def nacks(conn) -> list[dict]:
    return conn.of_type('nack')


def without(frame: dict, key: str) -> dict:
    copied = copy.deepcopy(frame)
    del copied[key]
    return copied


def with_user_id(frame: dict, user_id: str) -> dict:
    copied = copy.deepcopy(frame)
    copied['user_state']['chat_id']['user_id'] = user_id
    return copied


def raise_invalid_observation(frame: dict):
    raise InvalidDeliveryError('invalid_observation')


def raise_key_error(frame: dict):
    raise KeyError('campo')


@pytest.mark.unit
class TestAckBeforeConsumer:
    @pytest.mark.asyncio
    async def test_ack_is_sent_while_sink_only_stores(
        self, fake_router, stream_settings
    ):
        async with stream_client(fake_router, stream_settings) as (
            client,
            sink,
        ):
            await client.connect()
            conn = fake_router.conns[0]
            sent = make_deliver('d1', 'm1', text='olá')

            await conn.send(sent)
            await eventually(lambda: acks(conn))

        assert acks(conn) == [
            {'type': 'ack', 'delivery_id': 'd1', 'msg_id': 'm1'}
        ]
        assert len(sink.items) == 1
        item = sink.items[0]
        assert item['user_state']['chat_id'] == sent['user_state']['chat_id']
        assert item['menu'] == 'rh'
        assert item['message'] == sent['message']
        assert item['platform_state'] == sent['platform_state']


@pytest.mark.unit
class TestDedupe:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ('second_menu', 'expected_items'),
        [('rh', 1), ('geral', 2)],
    )
    async def test_same_msg_id_dedupes_only_within_the_same_menu(
        self, fake_router, stream_settings, second_menu, expected_items
    ):
        async with stream_client(
            fake_router, stream_settings, menus=('rh', 'geral')
        ) as (client, sink):
            await client.connect()
            conn = fake_router.conns[0]

            await conn.send(make_deliver('d1', 'm1', menu='rh'))
            await conn.send(make_deliver('d2', 'm1', menu=second_menu))
            await eventually(lambda: len(acks(conn)) == 2)

        assert [a['delivery_id'] for a in acks(conn)] == ['d1', 'd2']
        assert len(sink.items) == expected_items

    @pytest.mark.asyncio
    async def test_duplicate_on_second_connection_is_acked_without_item(
        self, fake_router, stream_settings
    ):
        async with stream_client(fake_router, stream_settings) as (
            client,
            sink,
        ):
            await client.connect()
            first = fake_router.conns[0]
            await first.send(make_deliver('d1', 'm1'))
            await eventually(lambda: acks(first))

            first.abort()
            await eventually(lambda: len(fake_router.conns) == 2)
            second = fake_router.conns[1]
            await eventually(lambda: client._current is not None)
            await second.send(make_deliver('d2', 'm1'))
            await eventually(lambda: acks(second))

        assert acks(second)[0]['delivery_id'] == 'd2'
        assert len(sink.items) == 1

    @pytest.mark.asyncio
    async def test_simultaneous_duplicate_on_two_connections_yields_one_item(
        self, fake_router, stream_settings, monkeypatch
    ):
        real_send = ClientConnection.send

        async def slow_send(self, message):
            await asyncio.sleep(0.02)
            await real_send(self, message)

        monkeypatch.setattr(ClientConnection, 'send', slow_send)

        async def send_both() -> None:
            first = fake_router.conns[0]
            second = fake_router.conns[1]
            await asyncio.gather(
                first.send(make_deliver('d-a', 'm1')),
                second.send(make_deliver('d-b', 'm1')),
            )

        fake_router.scripts = [
            ConnScript(),
            ConnScript(on_hello=send_both, welcome_delay=0.1),
        ]
        async with stream_client(fake_router, stream_settings) as (
            client,
            sink,
        ):
            await client.connect()
            first = fake_router.conns[0]

            await first.send({'type': 'goaway', 'reason': 'shutdown'})
            await eventually(lambda: len(fake_router.conns) == 2)
            second = fake_router.conns[1]
            await eventually(lambda: acks(first) and acks(second))

        assert [a['delivery_id'] for a in acks(first)] == ['d-a']
        assert [a['delivery_id'] for a in acks(second)] == ['d-b']
        assert len(sink.items) == 1


@pytest.mark.unit
class TestQueueFull:
    @pytest.mark.asyncio
    async def test_nack_retryable_when_full_and_ack_after_release(
        self, fake_router, stream_settings
    ):
        async with stream_client(
            fake_router, stream_settings, queue_size=1
        ) as (client, sink):
            await client.connect()
            conn = fake_router.conns[0]

            await conn.send(make_deliver('d1', 'm1'))
            await conn.send(make_deliver('d2', 'm2'))
            await eventually(lambda: acks(conn) and nacks(conn))

            client.release_slot()
            await conn.send(make_deliver('d3', 'm3'))
            await eventually(lambda: len(acks(conn)) == 2)

        assert nacks(conn) == [
            {
                'type': 'nack',
                'delivery_id': 'd2',
                'msg_id': 'm2',
                'retryable': True,
                'error': 'queue_full',
            }
        ]
        assert [a['delivery_id'] for a in acks(conn)] == ['d1', 'd3']
        assert [i['msg_id'] for i in sink.items] == ['m1', 'm3']


@pytest.mark.unit
class TestInvalidDeliver:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ('frame', 'convert', 'error'),
        [
            (
                without(make_deliver('bad', 'bad'), 'user_state'),
                None,
                'invalid_payload',
            ),
            (
                without(make_deliver('bad', 'bad'), 'message'),
                None,
                'invalid_payload',
            ),
            (
                with_user_id(make_deliver('bad', 'bad'), ''),
                None,
                'invalid_payload',
            ),
            (
                make_deliver('bad', 'bad', menu='financeiro'),
                None,
                'menu_not_served',
            ),
            (
                make_deliver('bad', 'bad'),
                raise_invalid_observation,
                'invalid_observation',
            ),
            (make_deliver('bad', 'bad'), raise_key_error, 'invalid_payload'),
            (make_deliver('bad', 'bad', menu=['rh']), None, 'invalid_payload'),
        ],
        ids=[
            'no_user_state',
            'no_message',
            'empty_user_id',
            'menu_not_declared',
            'invalid_observation',
            'convert_key_error',
            'menu_not_string',
        ],
    )
    async def test_nack_not_retryable_and_connection_survives(
        self, fake_router, stream_settings, frame, convert, error
    ):
        def convert_bad_only(item: dict):
            if item['msg_id'] == 'bad':
                return convert(item)
            return item

        async with stream_client(
            fake_router,
            stream_settings,
            convert=convert_bad_only if convert else None,
        ) as (client, sink):
            await client.connect()
            conn = fake_router.conns[0]

            await conn.send(frame)
            await eventually(lambda: nacks(conn))
            await conn.send(make_deliver('d-ok', 'm-ok'))
            await eventually(lambda: acks(conn))

        assert nacks(conn) == [
            {
                'type': 'nack',
                'delivery_id': 'bad',
                'msg_id': 'bad',
                'retryable': False,
                'error': error,
            }
        ]
        assert [i['msg_id'] for i in sink.items] == ['m-ok']

    @pytest.mark.asyncio
    async def test_invalid_observation_logs_warning_without_observation(
        self, fake_router, stream_settings, caplog
    ):
        caplog.set_level(logging.DEBUG, logger='chatgraph.system')
        async with stream_client(
            fake_router, stream_settings, convert=raise_invalid_observation
        ) as (client, _):
            await client.connect()
            conn = fake_router.conns[0]

            await conn.send(make_deliver('d1', 'm1'))
            await eventually(lambda: nacks(conn))

        warnings = [
            r.getMessage()
            for r in caplog.records
            if r.levelno == logging.WARNING
            and 'observation invalid' in r.getMessage()
        ]
        assert warnings == [
            'Stream deliver observation invalid menu=rh msg_id=m1'
        ]

    @pytest.mark.asyncio
    async def test_deliver_without_delivery_id_gets_no_ack_nor_nack(
        self, fake_router, stream_settings
    ):
        async with stream_client(fake_router, stream_settings) as (
            client,
            sink,
        ):
            await client.connect()
            conn = fake_router.conns[0]

            await conn.send(without(make_deliver('x', 'm1'), 'delivery_id'))
            await conn.send(make_deliver('d2', 'm2'))
            await eventually(lambda: acks(conn))

        assert [a['delivery_id'] for a in acks(conn)] == ['d2']
        assert nacks(conn) == []
        assert [i['msg_id'] for i in sink.items] == ['m2']


@pytest.mark.unit
class TestLargeDeliver:
    @pytest.mark.asyncio
    async def test_deliver_above_1_mib_is_acked_and_delivered(
        self, fake_router, stream_settings
    ):
        big = make_deliver('d1', 'm1', text='x' * int(1.5 * 1024 * 1024))
        async with stream_client(fake_router, stream_settings) as (
            client,
            sink,
        ):
            await client.connect()
            conn = fake_router.conns[0]

            await conn.send(big)
            await eventually(lambda: acks(conn), timeout=5.0)

        assert len(sink.items) == 1
        assert len(sink.items[0]['message']['text_message']['detail']) == (
            int(1.5 * 1024 * 1024)
        )


@pytest.mark.unit
class TestAckTimeout:
    @pytest.mark.asyncio
    async def test_stuck_ack_write_times_out_and_connection_is_replaced(
        self, fake_router, stream_settings, monkeypatch, caplog
    ):
        caplog.set_level(logging.DEBUG, logger='chatgraph.system')
        fake_router.default = ConnScript(heartbeat_s=1)
        never = asyncio.Event()

        async def stuck_send(data):
            await never.wait()

        async with stream_client(fake_router, stream_settings) as (
            client,
            sink,
        ):
            await client.connect()
            first = fake_router.conns[0]
            monkeypatch.setattr(client._current._ws, 'send', stuck_send)
            started = asyncio.get_running_loop().time()

            await first.send(make_deliver('d1', 'm1'))
            await eventually(
                lambda: any(
                    'Stream ack write failed' in r.getMessage()
                    for r in caplog.records
                )
            )
            elapsed = asyncio.get_running_loop().time() - started
            await eventually(lambda: len(fake_router.conns) == 2)
            await eventually(
                lambda: (
                    client._current is not None
                    and client._current.id == 'conn-1'
                )
            )

        assert elapsed < 0.1 + 0.3
        assert len(sink.items) == 1
        assert acks(first) == []
