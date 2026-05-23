import logging
import os
import sys
from unittest.mock import patch, MagicMock

import pytest

from chatgraph.logger.user_logger import UserLoggerManager

user_logger_module = sys.modules["chatgraph.logger.user_logger"]


@pytest.fixture(autouse=True)
def restore_log_level():
    original = UserLoggerManager._level
    yield
    UserLoggerManager._level = original


@pytest.mark.unit
class TestUserLoggerManager:

    def setup_method(self):
        # Limpar registry entre testes para isolamento
        for lgr in list(UserLoggerManager._loggers.values()):
            for handler in lgr.handlers[:]:
                handler.close()
                lgr.removeHandler(handler)
        UserLoggerManager._loggers.clear()

    def test_get_user_logger_returns_logger(self, tmp_path, monkeypatch):
        monkeypatch.setattr(user_logger_module, "LOG_DIR", str(tmp_path))
        logger = UserLoggerManager.get_user_logger("user1", "company1")
        assert isinstance(logger, logging.Logger)

    def test_get_user_logger_creates_log_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(user_logger_module, "LOG_DIR", str(tmp_path))
        UserLoggerManager.get_user_logger("user1", "company1")
        assert os.path.exists(os.path.join(str(tmp_path), "user1_company1.log"))

    def test_get_user_logger_singleton(self, tmp_path, monkeypatch):
        monkeypatch.setattr(user_logger_module, "LOG_DIR", str(tmp_path))
        logger1 = UserLoggerManager.get_user_logger("user1", "company1")
        logger2 = UserLoggerManager.get_user_logger("user1", "company1")
        assert logger1 is logger2

    def test_get_user_logger_no_duplicate_handlers(self, tmp_path, monkeypatch):
        monkeypatch.setattr(user_logger_module, "LOG_DIR", str(tmp_path))
        UserLoggerManager.get_user_logger("user1", "company1")
        UserLoggerManager._loggers.clear()
        logger = UserLoggerManager.get_user_logger("user1", "company1")
        assert len(logger.handlers) == 2

    def test_get_system_logger_returns_logger(self, tmp_path, monkeypatch):
        monkeypatch.setattr(user_logger_module, "LOG_DIR", str(tmp_path))
        logger = UserLoggerManager.get_system_logger()
        assert isinstance(logger, logging.Logger)

    def test_get_system_logger_creates_system_log(self, tmp_path, monkeypatch):
        monkeypatch.setattr(user_logger_module, "LOG_DIR", str(tmp_path))
        UserLoggerManager.get_system_logger()
        assert os.path.exists(os.path.join(str(tmp_path), "system.log"))

    def test_get_system_logger_singleton(self, tmp_path, monkeypatch):
        monkeypatch.setattr(user_logger_module, "LOG_DIR", str(tmp_path))
        logger1 = UserLoggerManager.get_system_logger()
        logger2 = UserLoggerManager.get_system_logger()
        assert logger1 is logger2

    def test_different_users_get_different_loggers(self, tmp_path, monkeypatch):
        monkeypatch.setattr(user_logger_module, "LOG_DIR", str(tmp_path))
        logger1 = UserLoggerManager.get_user_logger("user1", "company1")
        logger2 = UserLoggerManager.get_user_logger("user2", "company1")
        assert logger1 is not logger2

    def test_log_format(self, tmp_path, monkeypatch):
        monkeypatch.setattr(user_logger_module, "LOG_DIR", str(tmp_path))
        logger = UserLoggerManager.get_user_logger("user1", "company1")
        handler = logger.handlers[0]
        assert handler.formatter._fmt == "%(asctime)s | %(levelname)s | %(message)s | %(funcName)s | %(name)s"

    def test_set_level_string_info(self):
        UserLoggerManager.set_level("INFO")
        assert UserLoggerManager._level == logging.INFO

    def test_set_level_int_warning(self):
        UserLoggerManager.set_level(logging.WARNING)
        assert UserLoggerManager._level == logging.WARNING

    def test_set_level_invalid_string_raises(self):
        with pytest.raises(ValueError):
            UserLoggerManager.set_level("invalido")

    def test_set_level_updates_existing_loggers(self, tmp_path, monkeypatch):
        monkeypatch.setattr(user_logger_module, "LOG_DIR", str(tmp_path))
        logger = UserLoggerManager.get_user_logger("user_existing", "company1")
        UserLoggerManager.set_level(logging.WARNING)
        assert logger.level == logging.WARNING
        assert all(h.level == logging.WARNING for h in logger.handlers)

    def test_set_level_applies_to_new_loggers(self, tmp_path, monkeypatch):
        monkeypatch.setattr(user_logger_module, "LOG_DIR", str(tmp_path))
        UserLoggerManager.set_level(logging.WARNING)
        logger = UserLoggerManager.get_user_logger("user_new", "company1")
        assert logger.level == logging.WARNING
        assert all(h.level == logging.WARNING for h in logger.handlers)

    def test_chatbot_app_log_level_param(self):
        mock_consumer = MagicMock()
        from chatgraph.bot.chatbot_model import ChatbotApp
        ChatbotApp(message_consumer=mock_consumer, log_level="ERROR")
        assert UserLoggerManager._level == logging.ERROR
