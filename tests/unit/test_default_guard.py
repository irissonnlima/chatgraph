from unittest.mock import AsyncMock, MagicMock

import pytest

from chatgraph.bot.default_guard import default_guard
from chatgraph.models.userstate import AuthLevel, User, UserIdentity, UserInternal
from chatgraph.types.end_types import TransferToMenu


def _make_usercall(user: User) -> MagicMock:
    usercall = MagicMock()
    usercall.user = user
    usercall.menu = None
    usercall.route = 'test_route'
    usercall.add_observation = AsyncMock()
    usercall.logger = MagicMock()
    return usercall


@pytest.mark.unit
class TestDefaultGuard:

    @pytest.mark.asyncio
    async def test_t1_read_level_with_internal_user_returns_none(self):
        user = User(internal=UserInternal(matricula='12345'), identity=UserIdentity(auth_level=AuthLevel.READ))
        usercall = _make_usercall(user)

        result = await default_guard(usercall, 'read')

        assert result is None
        usercall.add_observation.assert_not_called()

    @pytest.mark.asyncio
    async def test_t2_internal_level_no_internal_user_returns_transfer(self):
        user = User(internal=None)
        usercall = _make_usercall(user)

        result = await default_guard(usercall, 'internal')

        assert isinstance(result, TransferToMenu)
        assert result.menu == 'menu_id_positiva'
        assert result.user_message == ''
        usercall.add_observation.assert_called_once_with({
            'pending_menu': None,
            'pending_route': usercall.route,
            'pending_auth_level': 'internal',
        })

    @pytest.mark.asyncio
    async def test_t3_read_level_auth_unknown_returns_transfer(self):
        user = User(identity=UserIdentity(auth_level=AuthLevel.UNKNOWN))
        usercall = _make_usercall(user)

        result = await default_guard(usercall, 'read')

        assert isinstance(result, TransferToMenu)
        assert result.menu == 'menu_id_positiva'
        usercall.add_observation.assert_called_once_with({
            'pending_menu': None,
            'pending_route': usercall.route,
            'pending_auth_level': 'read',
        })

    @pytest.mark.asyncio
    async def test_t4_read_level_auth_read_returns_none(self):
        user = User(identity=UserIdentity(auth_level=AuthLevel.READ))
        usercall = _make_usercall(user)

        result = await default_guard(usercall, 'read')

        assert result is None
        usercall.add_observation.assert_not_called()

    @pytest.mark.asyncio
    async def test_t5_read_level_auth_write_returns_none(self):
        user = User(identity=UserIdentity(auth_level=AuthLevel.WRITE))
        usercall = _make_usercall(user)

        result = await default_guard(usercall, 'read')

        assert result is None
        usercall.add_observation.assert_not_called()

    @pytest.mark.asyncio
    async def test_t6_internal_level_with_internal_user_returns_none(self):
        user = User(internal=UserInternal(matricula='12345'))
        usercall = _make_usercall(user)

        result = await default_guard(usercall, 'internal')

        assert result is None
        usercall.add_observation.assert_not_called()
