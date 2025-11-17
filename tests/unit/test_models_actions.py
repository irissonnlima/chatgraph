"""
Testes para os modelos de Actions.

Este módulo contém testes unitários para ActionType, EndAction
e TransferToHumanAction.
"""

import pytest
from chatgraph.models.actions import (
    ActionType,
    EndAction,
    TransferToHumanAction,
    EMPTY_END_ACTION,
    EMPTY_TRANSFER_TO_HUMAN_ACTION,
)


@pytest.mark.unit
class TestActionType:
    """Testes para o enum ActionType."""

    def test_actiontype_values(self):
        """Testa valores do enum ActionType."""
        assert ActionType.TRANSFER.value == 'TRANSFER'
        assert ActionType.END_CHAT.value == 'END_CHAT'
        assert ActionType.MESSAGE.value == 'MESSAGE'

    def test_actiontype_from_string(self):
        """Testa conversão de string para ActionType."""
        assert ActionType.from_string('transfer') == ActionType.TRANSFER
        assert ActionType.from_string('END_CHAT') == ActionType.END_CHAT
        assert ActionType.from_string('MeSsAgE') == ActionType.MESSAGE

    def test_actiontype_from_string_invalid(self):
        """Testa conversão de string inválida."""
        with pytest.raises(ValueError, match='invalid action type'):
            ActionType.from_string('invalid')


@pytest.mark.unit
class TestEndAction:
    """Testes para a classe EndAction."""

    def test_endaction_initialization_defaults(self):
        """Testa inicialização com valores padrão."""
        action = EndAction()

        assert action.id == ''
        assert action.name == ''
        assert action.department_id == 0
        assert action.observation == ''
        assert action.last_update == ''

    def test_endaction_initialization_with_values(self):
        """Testa inicialização com valores."""
        action = EndAction(
            id='end123',
            name='Finalizado com sucesso',
            department_id=10,
            observation='Cliente satisfeito',
            last_update='2025-11-14T10:00:00',
        )

        assert action.id == 'end123'
        assert action.name == 'Finalizado com sucesso'
        assert action.department_id == 10
        assert action.observation == 'Cliente satisfeito'
        assert action.last_update == '2025-11-14T10:00:00'

    def test_endaction_is_empty_true(self):
        """Testa is_empty retorna True para ação vazia."""
        action = EndAction()
        assert action.is_empty() is True

    def test_endaction_is_empty_false_with_id(self):
        """Testa is_empty retorna False quando tem ID."""
        action = EndAction(id='end123')
        assert action.is_empty() is False

    def test_endaction_is_empty_false_with_name(self):
        """Testa is_empty retorna False quando tem nome."""
        action = EndAction(name='Finalizado')
        assert action.is_empty() is False

    def test_endaction_to_dict(self):
        """Testa conversão para dicionário."""
        action = EndAction(
            id='end123',
            name='Finalizado',
            department_id=10,
            observation='OK',
            last_update='2025-11-14T10:00:00',
        )
        result = action.to_dict()

        assert result == {
            'id': 'end123',
            'name': 'Finalizado',
            'department_id': 10,
            'observation': 'OK',
            'last_update': '2025-11-14T10:00:00',
        }

    def test_endaction_from_dict(self):
        """Testa criação a partir de dicionário."""
        data = {
            'id': 'end123',
            'name': 'Finalizado',
            'department_id': 10,
            'observation': 'OK',
            'last_update': '2025-11-14T10:00:00',
        }
        action = EndAction.from_dict(data)

        assert action.id == 'end123'
        assert action.name == 'Finalizado'
        assert action.department_id == 10
        assert action.observation == 'OK'
        assert action.last_update == '2025-11-14T10:00:00'

    def test_empty_end_action_constant(self):
        """Testa constante EMPTY_END_ACTION."""
        assert isinstance(EMPTY_END_ACTION, EndAction)
        assert EMPTY_END_ACTION.is_empty() is True


@pytest.mark.unit
class TestTransferToHumanAction:
    """Testes para a classe TransferToHumanAction."""

    def test_transfer_initialization_defaults(self):
        """Testa inicialização com valores padrão."""
        action = TransferToHumanAction()

        assert action.id == 0
        assert action.name == ''
        assert action.department_id == 0
        assert action.observation == ''
        assert action.last_update == ''

    def test_transfer_initialization_with_values(self):
        """Testa inicialização com valores."""
        action = TransferToHumanAction(
            id=1,
            name='Suporte Técnico',
            department_id=10,
            observation='Cliente com dúvida técnica',
            last_update='2025-11-14T10:00:00',
        )

        assert action.id == 1
        assert action.name == 'Suporte Técnico'
        assert action.department_id == 10
        assert action.observation == 'Cliente com dúvida técnica'
        assert action.last_update == '2025-11-14T10:00:00'

    def test_transfer_is_empty_true(self):
        """Testa is_empty retorna True para ação vazia."""
        action = TransferToHumanAction()
        assert action.is_empty() is True

    def test_transfer_is_empty_false_with_id(self):
        """Testa is_empty retorna False quando tem ID."""
        action = TransferToHumanAction(id=1)
        assert action.is_empty() is False

    def test_transfer_is_empty_false_with_name(self):
        """Testa is_empty retorna False quando tem nome."""
        action = TransferToHumanAction(name='Suporte')
        assert action.is_empty() is False

    def test_transfer_to_dict(self):
        """Testa conversão para dicionário."""
        action = TransferToHumanAction(
            id=1,
            name='Suporte',
            department_id=10,
            observation='OK',
            last_update='2025-11-14T10:00:00',
        )
        result = action.to_dict()

        assert result == {
            'id': 1,
            'name': 'Suporte',
            'department_id': 10,
            'observation': 'OK',
            'last_update': '2025-11-14T10:00:00',
        }

    def test_transfer_from_dict(self):
        """Testa criação a partir de dicionário."""
        data = {
            'id': 1,
            'name': 'Suporte',
            'department_id': 10,
            'observation': 'OK',
            'last_update': '2025-11-14T10:00:00',
        }
        action = TransferToHumanAction.from_dict(data)

        assert action.id == 1
        assert action.name == 'Suporte'
        assert action.department_id == 10
        assert action.observation == 'OK'
        assert action.last_update == '2025-11-14T10:00:00'

    def test_empty_transfer_constant(self):
        """Testa constante EMPTY_TRANSFER_TO_HUMAN_ACTION."""
        assert isinstance(
            EMPTY_TRANSFER_TO_HUMAN_ACTION, TransferToHumanAction
        )
        assert EMPTY_TRANSFER_TO_HUMAN_ACTION.is_empty() is True
