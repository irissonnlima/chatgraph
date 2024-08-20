import pytest

from chatgraph.auth.credentials import Credential


def test_credential_initialization():
    cred = Credential(username='user', password='pass')
    assert cred.username == 'user'
    assert cred.password == 'pass'


def test_credential_empty_username_raises_error():
    with pytest.raises(ValueError, match='Usuário vazio!'):
        Credential(username=None, password='pass').username


def test_credential_empty_password_raises_error():
    with pytest.raises(ValueError, match='Senha vazia!'):
        Credential(username='user', password=None).password


def test_dot_env_credentials(monkeypatch):
    monkeypatch.setenv('CHATBOT_USER', 'env_user')
    monkeypatch.setenv('CHATBOT_PASS', 'env_pass')

    cred = Credential().dot_env_credentials()

    assert cred.username == 'env_user'
    assert cred.password == 'env_pass'
