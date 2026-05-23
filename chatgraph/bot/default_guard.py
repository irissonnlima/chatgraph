from ..models.userstate import AuthLevel
from ..types.end_types import TransferToMenu
from ..types.usercall import UserCall


async def default_guard(
    usercall: UserCall, auth_level: str
) -> TransferToMenu | None:
    await usercall.load_userstate()
    user = usercall.user
    last_route = usercall.route.split('.')[-1] if usercall.route else 'start'
    usercall.logger.debug(
        f"default_guard | auth_level='{auth_level}' | menu='{usercall.menu.name if usercall.menu else None}' | rota='{last_route}'"
    )

    if not user:
        raise ValueError('Usuário não encontrado no UserCall!')

    if usercall.user.identity.auth_level == AuthLevel.BLOCKED:
        usercall.logger.info(
            f"default_guard | acesso negado (usuário bloqueado) | rota='{last_route}'"
        )
        return TransferToMenu('menu_id_positiva', '')

    obs = {
        'pending_menu': usercall.menu.name if usercall.menu else None,
        'pending_route': last_route,
        'pending_auth_level': auth_level,
    }

    if auth_level == 'internal':
        if not user.internal:
            usercall.logger.info(
                f"default_guard | acesso negado (sem vínculo interno) | rota='{last_route}'"
            )
            await usercall.add_observation(obs)
            return TransferToMenu('menu_id_positiva', '')
        usercall.logger.debug(
            f"default_guard | acesso liberado (interno com vínculo) | rota='{last_route}'"
        )
        return None

    required_level = AuthLevel.from_value(auth_level)
    if required_level > user.identity.auth_level:
        usercall.logger.info(
            f"default_guard | acesso negado | requerido='{auth_level}' | atual='{user.identity.auth_level.value}' | rota='{last_route}'"
        )
        await usercall.add_observation(obs)
        return TransferToMenu('menu_id_positiva', '')

    usercall.logger.debug(
        f"default_guard | acesso liberado | rota='{last_route}'"
    )
    return None
