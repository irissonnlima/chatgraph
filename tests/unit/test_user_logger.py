import logging
import os
import sys

import pytest

from chatgraph.logger.user_logger import UserLoggerManager

user_logger_module = sys.modules["chatgraph.logger.user_logger"]


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
        assert len(logger.handlers) == 1

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
