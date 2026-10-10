# ruff: noqa: PLR2004, PLR6301 - testes em classe e literais nos asserts, como no
# resto da suíte.
import asyncio
import base64
import logging

import pytest

from chatgraph.stream.errors import StreamClosedError, StreamRejectedError
from tests.unit.stream_fake_router import (
    ConnScript,
    eventually,
    make_deliver,
    stream_client,
)


def system_records(caplog) -> list[logging.LogRecord]:
    return [r for r in caplog.records if r.name == 'chatgraph.system']


@pytest.mark.unit
class TestHandshake:
    @pytest.mark.asyncio
    async def test_authorization_and_hello(self, fake_router, stream_settings):
        async with stream_client(
            fake_router,
            stream_settings,
            menus=(' rh', 'geral', 'rh'),
            queue_size=7,
        ) as (client, _):
            await client.connect()

        expected = base64.b64encode(b'chatgraph:tok-1').decode()
        assert fake_router.attempts[0].authorization == f'Basic {expected}'
        assert fake_router.conns[0].frames[0][1] == {
            'type': 'hello',
            'menus': ['rh', 'geral'],
            'version': '1.0',
            'max_inflight': 7,
        }

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ('status', 'detail'),
        [
            (401, '401 unauthorized'),
            (403, '403 forbidden'),
            (404, '404 (router não está em modo stream?)'),
        ],
    )
    async def test_boot_rejected_by_status_does_not_retry(
        self, fake_router, stream_settings, status, detail
    ):
        fake_router.default = ConnScript(status=status)
        async with stream_client(fake_router, stream_settings) as (client, _):
            started = asyncio.get_running_loop().time()
            with pytest.raises(StreamRejectedError) as exc_info:
                await asyncio.wait_for(client.connect(), 2.0)
            elapsed = asyncio.get_running_loop().time() - started

            await asyncio.sleep(0.1)

        assert detail in str(exc_info.value)
        assert elapsed < 1.0
        assert len(fake_router.attempts) == 1

    @pytest.mark.asyncio
    async def test_boot_rejected_by_1008_close(
        self, fake_router, stream_settings
    ):
        fake_router.default = ConnScript(
            close_after_hello=(1008, 'menu_not_allowed: rh')
        )
        async with stream_client(fake_router, stream_settings) as (client, _):
            with pytest.raises(StreamRejectedError) as exc_info:
                await asyncio.wait_for(client.connect(), 2.0)

            await asyncio.sleep(0.1)

        assert 'menu_not_allowed: rh' in str(exc_info.value)
        assert len(fake_router.attempts) == 1

    @pytest.mark.asyncio
    async def test_boot_503_logs_reason_as_info_and_never_error(
        self, fake_router, stream_settings, caplog
    ):
        caplog.set_level(logging.DEBUG, logger='chatgraph.system')
        draining = ConnScript(status=503, body='{"error":"draining"}')
        fake_router.scripts = [draining, draining]

        async with stream_client(fake_router, stream_settings) as (client, _):
            await client.connect()

        records = system_records(caplog)
        short = [r for r in records if 'class=short' in r.getMessage()]
        assert len(short) == 2
        assert all(r.levelno == logging.INFO for r in short)
        assert all(
            'reason={"error":"draining"}' in r.getMessage() for r in short
        )
        assert not [r for r in records if r.levelno >= logging.ERROR]

    @pytest.mark.asyncio
    async def test_boot_1013_logs_reason_as_info_and_never_error(
        self, fake_router, stream_settings, caplog
    ):
        caplog.set_level(logging.DEBUG, logger='chatgraph.system')
        draining = ConnScript(close_after_hello=(1013, 'draining'))
        fake_router.scripts = [draining, draining]

        async with stream_client(fake_router, stream_settings) as (client, _):
            await client.connect()

        records = system_records(caplog)
        short = [r for r in records if 'class=short' in r.getMessage()]
        assert len(short) == 2
        assert all(r.levelno == logging.INFO for r in short)
        assert all('reason=draining' in r.getMessage() for r in short)
        assert not [r for r in records if r.levelno >= logging.ERROR]

    @pytest.mark.asyncio
    async def test_deliver_before_welcome_is_acked_and_delivered(
        self, fake_router, stream_settings
    ):
        fake_router.default = ConnScript(
            deliver_before_welcome=make_deliver('d1', 'm1'),
            welcome_delay=0.05,
        )
        async with stream_client(fake_router, stream_settings) as (
            client,
            sink,
        ):
            await client.connect()
            conn = fake_router.conns[0]
            await eventually(lambda: conn.of_type('ack'))

        assert conn.of_type('ack') == [
            {'type': 'ack', 'delivery_id': 'd1', 'msg_id': 'm1'}
        ]
        assert len(sink.items) == 1

    @pytest.mark.asyncio
    async def test_close_during_boot_backoff_raises_closed(
        self, fake_router, stream_settings
    ):
        fake_router.default = ConnScript(status=500)
        async with stream_client(fake_router, stream_settings) as (client, _):
            boot = asyncio.create_task(client.connect())
            await eventually(lambda: len(fake_router.attempts) >= 2)

            await client.close()

            with pytest.raises(StreamClosedError):
                await boot

    @pytest.mark.asyncio
    async def test_reconnect_rejected_after_boot_logs_error_per_attempt(
        self, fake_router, stream_settings, caplog
    ):
        caplog.set_level(logging.DEBUG, logger='chatgraph.system')
        rejected = ConnScript(status=401)
        fake_router.scripts = [ConnScript(), rejected, rejected]

        async with stream_client(fake_router, stream_settings) as (client, _):
            await client.connect()
            fake_router.conns[0].abort()

            await eventually(lambda: len(fake_router.attempts) >= 4)
            await eventually(
                lambda: (
                    client._current is not None
                    and client._current.id == 'conn-3'
                )
            )

        errors = [
            r
            for r in system_records(caplog)
            if r.levelno >= logging.ERROR
            and 'Stream rejected, retrying' in r.getMessage()
        ]
        assert len(errors) == 2
        assert all('status=401' in r.getMessage() for r in errors)
