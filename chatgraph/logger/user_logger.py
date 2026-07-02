import logging
import os
import sys

LOG_DIR = "chatgraph_logs"
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(message)s | %(funcName)s | %(name)s"

_ENV_LEVEL = os.getenv("CHATGRAPH_LOG_LEVEL", "").upper()
_DEFAULT_LEVEL: int = getattr(logging, _ENV_LEVEL, logging.INFO)


class ChatIDFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        chat_id = getattr(record, 'chat_id', None)
        if chat_id:
            record.msg = f'[ChatID: {chat_id}] - {record.msg}'
        return True


class UserLoggerManager:
    _loggers: dict[str, logging.Logger] = {}
    _level: int = _DEFAULT_LEVEL

    @classmethod
    def set_level(cls, level: int | str) -> None:
        if isinstance(level, str):
            numeric = getattr(logging, level.upper(), None)
            if numeric is None:
                raise ValueError(f"Nível de log inválido: '{level}'")
            level = numeric
        cls._level = level
        for logger in cls._loggers.values():
            logger.setLevel(level)
            for handler in logger.handlers:
                handler.setLevel(level)

    @classmethod
    def get_user_logger(cls, user_id: str, company_id: str) -> logging.Logger:
        key = f"{user_id}_{company_id}"
        if key in cls._loggers:
            return cls._loggers[key]

        os.makedirs(LOG_DIR, exist_ok=True)

        logger = logging.getLogger(key)
        logger.setLevel(cls._level)

        if not logger.handlers:
            handler = logging.FileHandler(
                os.path.join(LOG_DIR, f"{key}.log"), encoding="utf-8"
            )
            handler.setLevel(cls._level)
            handler.setFormatter(logging.Formatter(LOG_FORMAT))
            logger.addHandler(handler)
            stream_handler = logging.StreamHandler(sys.stdout)
            stream_handler.setLevel(cls._level)
            stream_handler.setFormatter(logging.Formatter(LOG_FORMAT))
            logger.addHandler(stream_handler)
            logger.addFilter(ChatIDFilter())

        cls._loggers[key] = logger
        return logger

    @classmethod
    def remove_user_logger(cls, user_id: str, company_id: str) -> None:
        key = f"{user_id}_{company_id}"
        logger = cls._loggers.pop(key, None)
        if logger:
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)

    @classmethod
    def get_system_logger(cls) -> logging.Logger:
        key = "chatgraph.system"
        if key in cls._loggers:
            return cls._loggers[key]

        os.makedirs(LOG_DIR, exist_ok=True)

        logger = logging.getLogger(key)
        logger.setLevel(cls._level)

        if not logger.handlers:
            handler = logging.FileHandler(
                os.path.join(LOG_DIR, "system.log"), encoding="utf-8"
            )
            handler.setLevel(cls._level)
            handler.setFormatter(logging.Formatter(LOG_FORMAT))
            logger.addHandler(handler)
            stream_handler = logging.StreamHandler(sys.stdout)
            stream_handler.setLevel(cls._level)
            stream_handler.setFormatter(logging.Formatter(LOG_FORMAT))
            logger.addHandler(stream_handler)

        cls._loggers[key] = logger
        return logger
