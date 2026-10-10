# ruff: noqa: PLC2701, PLR6301, PLR2004 - testes em classe, literais nos asserts e
# import do privado sob teste, como no resto da suíte.
import asyncio
import logging
import threading

import pytest
import pytest_asyncio

from chatgraph.stream.errors import StreamClosedError
from chatgraph.stream.runtime import THREAD_NAME, _IoThread
from tests.unit.stream_fake_router import eventually


def io_threads() -> list[threading.Thread]:
    return [t for t in threading.enumerate() if t.name == THREAD_NAME]


@pytest_asyncio.fixture
async def runtime():
    thread = _IoThread()
    thread.start()
    yield thread
    thread.stop()


@pytest.mark.unit
class TestIoThreadCall:
    @pytest.mark.asyncio
    async def test_coroutine_runs_on_the_io_thread(self, runtime):
        async def where() -> str:
            return threading.current_thread().name

        name = await runtime.call(where())

        assert name == THREAD_NAME
        assert threading.current_thread().name != THREAD_NAME

    @pytest.mark.asyncio
    async def test_exception_from_the_coroutine_reaches_the_caller(
        self, runtime
    ):
        async def boom() -> None:
            raise ValueError('boom')

        with pytest.raises(ValueError, match='boom'):
            await runtime.call(boom())

    @pytest.mark.asyncio
    async def test_call_after_stop_fails_immediately_and_closes_coroutine(
        self, runtime
    ):
        runtime.stop()
        started = []

        async def never() -> None:
            started.append(True)

        coro = never()
        with pytest.raises(StreamClosedError):
            await asyncio.wait_for(runtime.call(coro), 1.0)

        assert started == []
        assert coro.cr_frame is None

    @pytest.mark.asyncio
    async def test_call_before_start_fails_immediately(self):
        coro = asyncio.sleep(10)

        with pytest.raises(StreamClosedError):
            await asyncio.wait_for(_IoThread().call(coro), 1.0)

    @pytest.mark.asyncio
    async def test_stop_with_pending_call_raises_closed_not_cancelled(
        self, runtime
    ):
        started = threading.Event()

        async def pending() -> None:
            started.set()
            await asyncio.sleep(30)

        task = asyncio.create_task(runtime.call(pending()))
        await eventually(started.is_set)

        runtime.stop()

        with pytest.raises(StreamClosedError):
            await asyncio.wait_for(task, 1.0)
        assert io_threads() == []

    @pytest.mark.asyncio
    async def test_cancelling_the_caller_cancels_the_io_coroutine(
        self, runtime
    ):
        started = threading.Event()
        finished = threading.Event()

        async def pending() -> None:
            started.set()
            try:
                await asyncio.sleep(30)
            finally:
                finished.set()

        task = asyncio.create_task(runtime.call(pending()))
        await eventually(started.is_set)

        task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task
        await eventually(finished.is_set)


@pytest.mark.unit
class TestIoThreadLifecycle:
    @pytest.mark.asyncio
    async def test_start_returns_with_running_loop_and_stop_ends_thread(self):
        runtime = _IoThread()

        runtime.start()
        assert runtime.loop.is_running()
        assert len(io_threads()) == 1
        runtime.stop()

        assert io_threads() == []
        assert runtime.loop.is_closed()

    @pytest.mark.asyncio
    async def test_stop_is_idempotent(self, runtime):
        runtime.stop()
        runtime.stop()

        assert io_threads() == []

    @pytest.mark.asyncio
    async def test_loop_exception_handler_logs_task_crash(
        self, runtime, caplog
    ):
        caplog.set_level(logging.ERROR, logger='chatgraph.system')

        runtime.loop.call_soon_threadsafe(
            runtime.loop.call_exception_handler,
            {'message': 'x', 'exception': RuntimeError('boom')},
        )

        await eventually(
            lambda: any(
                'Stream task crashed' in r.getMessage()
                and 'boom' in r.getMessage()
                for r in caplog.records
            )
        )
