import logging

from .user_logger import UserLoggerManager

logger_httpx = logging.getLogger('httpx')
logger_httpx.setLevel(logging.ERROR)

get_system_logger = UserLoggerManager.get_system_logger
get_user_logger = UserLoggerManager.get_user_logger
set_level = UserLoggerManager.set_level
remove_user_logger = UserLoggerManager.remove_user_logger
