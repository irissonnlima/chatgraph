import hashlib


def generate_idempotency_key(  # noqa: PLR0913, PLR0917
    chat_id: str,
    session_id: int | None,
    role: str,
    event_type: str,
    route: str,
    message_payload: str = '',
) -> str:
    """Gera SHA-256 determinístico. Retorna hex string."""
    session_str = 'None' if session_id is None else str(session_id)
    raw = '|'.join([
        chat_id,
        session_str,
        role,
        event_type,
        route,
        message_payload,
    ])
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()
