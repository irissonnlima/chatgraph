# ruff: noqa: PLR6301, PLR2004 - testes em classe e literais nos asserts, como no
# resto da suíte.
import importlib.util
import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from chatgraph.models.message import Message
from chatgraph.models.userstate import ChatID, Menu, UserState
from chatgraph.types.usercall import UserCall

BOT_PATH = Path(__file__).parents[2] / 'examples' / 'stream' / 'bot.py'


def load_bot():
    spec = importlib.util.spec_from_file_location(
        'stream_example_bot', BOT_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.unit
class TestStreamExampleBot:
    @pytest.mark.asyncio
    async def test_echo_records_observation_and_sends_formatted_text(
        self, monkeypatch
    ):
        monkeypatch.setenv('STREAM_ECHO_POD', 'router-a')
        router_client = AsyncMock()
        usercall = UserCall(
            user_state=UserState(
                chat_id=ChatID(user_id='user-1', company_id='company-1'),
                platform='voll',
                menu=Menu(name='rh'),
            ),
            message=Message(text_message='ola'),
            router_client=router_client,
        )

        result = await load_bot().start(usercall)

        assert result is None
        observation = router_client.update_session_observation.await_args.args[
            1
        ]
        assert json.loads(observation) == {
            'bot': 'rh',
            'pod': 'router-a',
            'text': 'ola',
        }
        sent = router_client.send_message.await_args.args[0]
        assert sent.text_message.detail == 'rh|router-a|ola'

    @pytest.mark.asyncio
    async def test_pod_defaults_to_empty_without_env(self, monkeypatch):
        monkeypatch.delenv('STREAM_ECHO_POD', raising=False)
        router_client = AsyncMock()
        usercall = UserCall(
            user_state=UserState(
                chat_id=ChatID(user_id='user-1', company_id='company-1'),
                platform='voll',
                menu=Menu(name='geral'),
            ),
            message=Message(text_message='oi'),
            router_client=router_client,
        )

        await load_bot().start(usercall)

        sent = router_client.send_message.await_args.args[0]
        assert sent.text_message.detail == 'geral||oi'
