import json
import traceback
import uuid
from datetime import datetime, timezone
from typing import Optional

from ..history.store import HistoryStore
from ..logger.user_logger import UserLoggerManager
from ..models.log_envelope import (
    ErrorLogPayload,
    EventType,
    LogEnvelope,
    error_code_from_exception,
    is_error_logged,
)
from ..models.message import Message
from ..models.platform_state import PlatformState
from ..models.userstate import UserState
from ..services.router_http_client import RouterHTTPClient
from ..types.usercall import UserCall
from .log_publisher import LogPublisher

_logger = UserLoggerManager.get_system_logger()


def build_usercall(
    message: dict,
    router_client: RouterHTTPClient,
    history_store: Optional[HistoryStore],
) -> UserCall:
    user_state = message.get('user_state', {})
    message_data = message.get('message', {})
    observation = user_state.get('observation', '{}')

    if isinstance(observation, str):
        observation = json.loads(observation)

    user_state_models = UserState.from_dict(user_state)
    message_models = Message.from_dict(message_data)

    platform_state_data = message.get('platform_state', {})
    if not isinstance(platform_state_data, dict):
        platform_state_data = None
    platform_state = PlatformState.from_dict(platform_state_data)

    return UserCall(
        user_state=user_state_models,
        message=message_models,
        router_client=router_client,
        platform_state=platform_state,
        history_store=history_store,
    )


async def publish_edge_error(
    log_publisher: Optional[LogPublisher],
    exc: Exception,
    usercall: Optional[UserCall],
) -> None:
    # O pipeline já publica o erro da rota com o contexto do
    # usercall; aqui a borda cobre o que falha antes disso (decode,
    # parse, transform) sem duplicar o evento.
    if log_publisher is None or is_error_logged(exc):
        return
    try:
        error_message = f'{exc}\n{"".join(traceback.format_exception(exc))}'
        if usercall is not None:
            menu = usercall.menu
            menu_name = menu.name if menu and menu.name else 'unknown'
            user_state = usercall.user_state
            platform = user_state.platform if user_state else ''
            envelope = LogEnvelope(
                event_id=str(uuid.uuid4()),
                event_type=EventType.ERROR,
                timestamp=datetime.now(timezone.utc).isoformat(),
                request_id='',
                session_id=usercall.session_id or 0,
                chat_user_id=usercall.user_id,
                chat_company_id=usercall.company_id,
                platform=platform,
                origin=f'chatgraph:{menu_name}',
                error=str(exc),
                payload=ErrorLogPayload(
                    error_code=error_code_from_exception(exc),
                    error_message=error_message,
                    context_menu_id=menu.id if menu and menu.id else 0,
                    context_menu_name=menu_name,
                    context_route=usercall.route or '',
                ).to_dict(),
            )
        else:
            envelope = LogEnvelope(
                event_id=str(uuid.uuid4()),
                event_type=EventType.ERROR,
                timestamp=datetime.now(timezone.utc).isoformat(),
                request_id='',
                origin='chatgraph:unknown',
                error=str(exc),
                payload=ErrorLogPayload(
                    error_code=error_code_from_exception(exc),
                    error_message=error_message,
                ).to_dict(),
            )
        await log_publisher.publish_error(envelope)
    except Exception as pub_err:
        _logger.warning(f'Falha ao publicar log_error: {pub_err}')
