import logging
import os

LOG_DIR = "chatgraph_logs"
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(message)s | %(funcName)s | %(name)s"


class UserLoggerManager:
    _loggers: dict[str, logging.Logger] = {}

    @classmethod
    def get_user_logger(cls, user_id: str, company_id: str) -> logging.Logger:
        key = f"{user_id}_{company_id}"
        if key in cls._loggers:
            return cls._loggers[key]

        os.makedirs(LOG_DIR, exist_ok=True)

        logger = logging.getLogger(key)
        logger.setLevel(logging.DEBUG)

        if not logger.handlers:
            handler = logging.FileHandler(
                os.path.join(LOG_DIR, f"{key}.log"), encoding="utf-8"
            )
            handler.setLevel(logging.DEBUG)
            handler.setFormatter(logging.Formatter(LOG_FORMAT))
            logger.addHandler(handler)

        cls._loggers[key] = logger
        return logger

    @classmethod
    def get_system_logger(cls) -> logging.Logger:
        key = "chatgraph.system"
        if key in cls._loggers:
            return cls._loggers[key]

        os.makedirs(LOG_DIR, exist_ok=True)

        logger = logging.getLogger(key)
        logger.setLevel(logging.DEBUG)

        if not logger.handlers:
            handler = logging.FileHandler(
                os.path.join(LOG_DIR, "system.log"), encoding="utf-8"
            )
            handler.setLevel(logging.DEBUG)
            handler.setFormatter(logging.Formatter(LOG_FORMAT))
            logger.addHandler(handler)

        cls._loggers[key] = logger
        return logger
