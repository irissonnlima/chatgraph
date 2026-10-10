"""Testes para os modelos e a decodificação tolerante do protocolo."""

import json

import pytest
from pydantic import BaseModel

from chatgraph.agent.protocol import (
    ACTION_CALL_TOOL,
    ACTION_END_SESSION,
    ACTION_NEXT_ROUTE,
    ACTION_REDIRECT,
    ACTION_SEND_MESSAGE,
    ACTION_SET_OBSERVATION,
    ACTION_TRANSFER_MENU,
    ACTION_TYPES,
    AgentAction,
    AgentContext,
    AgentResult,
    MenuInfo,
    RouteState,
    ToolCallRequest,
    UserSummary,
    build_agent_result_schema,
    decode_json_string_maybe,
    tolerant_validate,
)
from chatgraph.agent.types import AgentMessage


@pytest.mark.unit
class TestDecodeJsonStringScenario:
    def test_decodifica_objeto_serializado(self):
        assert decode_json_string_maybe('{"a": 1}') == {'a': 1}

    def test_decodifica_array_serializado(self):
        assert decode_json_string_maybe('[1, 2]') == [1, 2]

    def test_string_comum_fica_inalterada(self):
        assert decode_json_string_maybe('ola mundo') == 'ola mundo'

    def test_json_invalido_fica_inalterado(self):
        assert decode_json_string_maybe('{quebrado') == '{quebrado'

    def test_nao_string_fica_inalterado(self):
        assert decode_json_string_maybe(5) == 5
        assert decode_json_string_maybe(None) is None


@pytest.mark.unit
class TestAgentActionScenario:
    def test_is_terminal(self):
        terminais = (
            ACTION_NEXT_ROUTE,
            ACTION_REDIRECT,
            ACTION_END_SESSION,
            ACTION_TRANSFER_MENU,
        )
        for action_type in terminais:
            assert AgentAction(type=action_type).is_terminal()
        nao_terminais = (
            ACTION_SEND_MESSAGE,
            ACTION_SET_OBSERVATION,
            ACTION_CALL_TOOL,
            '',
        )
        for action_type in nao_terminais:
            assert not AgentAction(type=action_type).is_terminal()

    def test_observation_string_json_e_decodificada(self):
        action = AgentAction(
            type=ACTION_SET_OBSERVATION,
            observation='{"cpf": "123"}',
        )
        assert action.observation == {'cpf': '123'}

    def test_observation_string_comum_permanece(self):
        action = AgentAction(
            type=ACTION_SET_OBSERVATION, observation='texto'
        )
        assert action.observation == 'texto'

    def test_tool_call_arguments_string_json_decodificada(self):
        request = ToolCallRequest(
            name='consultar', arguments='{"cpf": "123"}'
        )
        assert request.arguments == {'cpf': '123'}

    def test_chaves_extras_sao_ignoradas(self):
        action = AgentAction.model_validate({
            'type': ACTION_REDIRECT,
            'target_route': 'faq',
            'campo_alucinado': 'x',
        })
        assert action.target_route == 'faq'


@pytest.mark.unit
class TestAgentResultScenario:
    def test_sanitiza_actions_sem_type(self):
        result = AgentResult.model_validate({
            'response': 'ola',
            'actions': [
                {'type': ACTION_SEND_MESSAGE},
                {'target_route': 'faq'},
                {'type': ''},
            ],
        })
        assert len(result.actions) == 1
        assert result.actions[0].type == ACTION_SEND_MESSAGE

    def test_actions_null_vira_lista_vazia(self):
        result = AgentResult.model_validate({
            'response': 'ola',
            'actions': None,
        })
        assert result.actions == []


@pytest.mark.unit
class TestAgentContextScenario:
    def test_exclude_none_reproduz_omitempty(self):
        ctx = AgentContext(
            message=AgentMessage(role='user', content='oi'),
            user=UserSummary(name='Ana', auth_level='read'),
            route=RouteState(current='start'),
        )
        payload = json.loads(ctx.model_dump_json(exclude_none=True))
        for omitido in (
            'observation',
            'observation_schema',
            'available_tools',
            'available_menus',
            'history',
        ):
            assert omitido not in payload
        assert payload['message'] == {'role': 'user', 'content': 'oi'}

    def test_menu_info_message_nao_vai_para_a_ia(self):
        menu = MenuInfo(name='humano', message='transferindo...')
        payload = menu.model_dump(exclude_none=True)
        assert 'message' not in payload
        assert menu.message == 'transferindo...'


@pytest.mark.unit
class TestTolerantValidateScenario:
    def test_string_numerica_coage_para_numero(self):
        class Modelo(BaseModel):
            idade: int
            altura: float

        modelo = tolerant_validate(
            Modelo, {'idade': '42', 'altura': '1.75'}
        )
        assert modelo.idade == 42
        assert modelo.altura == 1.75

    def test_objeto_em_campo_string_vira_json(self):
        class Modelo(BaseModel):
            texto: str

        modelo = tolerant_validate(Modelo, {'texto': {'a': 1}})
        assert modelo.texto == '{"a": 1}'

    def test_string_json_em_campo_dict_e_decodificada(self):
        class Modelo(BaseModel):
            dados: dict

        modelo = tolerant_validate(Modelo, {'dados': '{"a": 1}'})
        assert modelo.dados == {'a': 1}

    def test_string_json_em_campo_lista_e_decodificada(self):
        class Modelo(BaseModel):
            itens: list[int]

        modelo = tolerant_validate(Modelo, {'itens': '[1, 2]'})
        assert modelo.itens == [1, 2]

    def test_raw_string_json_e_aceito(self):
        result = tolerant_validate(
            AgentResult, '{"response": "oi", "actions": []}'
        )
        assert result.response == 'oi'

    def test_agent_result_com_actions_string_json(self):
        raw = {
            'response': 'ola',
            'actions': json.dumps([
                {'type': ACTION_NEXT_ROUTE, 'target_route': 'faq'},
            ]),
        }
        result = tolerant_validate(AgentResult, raw)
        assert result.actions[0].target_route == 'faq'


@pytest.mark.unit
class TestAgentResultSchemaScenario:
    def test_enum_injetado_em_actions_type_via_ref(self):
        schema = build_agent_result_schema()
        action_def = schema['$defs']['AgentAction']
        assert action_def['properties']['type']['enum'] == ACTION_TYPES

    def test_schema_e_normalizado(self):
        schema = build_agent_result_schema()
        assert schema['additionalProperties'] is False
        assert schema['required'] == ['actions', 'response']
        action_def = schema['$defs']['AgentAction']
        assert action_def['additionalProperties'] is False

    def test_description_do_response_portada_do_go(self):
        schema = build_agent_result_schema()
        description = schema['properties']['response']['description']
        assert 'MUST NOT be empty' in description
        assert 'Portuguese' in description

    def test_observation_vira_string_json_no_schema(self):
        schema = build_agent_result_schema()
        action_def = schema['$defs']['AgentAction']
        observation = action_def['properties']['observation']
        assert observation['type'] == ['string', 'null']

    def test_sem_nomes_no_enum_de_menu_e_end_action(self):
        schema = build_agent_result_schema()
        action_def = schema['$defs']['AgentAction']
        for field_name in ('menu', 'end_action_id'):
            field = action_def['properties'][field_name]
            string_branch = next(
                b for b in field['anyOf'] if b.get('type') == 'string'
            )
            assert 'enum' not in string_branch

    def test_enum_de_menu_e_end_action_no_branch_de_string(self):
        schema = build_agent_result_schema(
            ('cartoes', 'humano'), ('encerrado',)
        )
        action_def = schema['$defs']['AgentAction']

        menu = action_def['properties']['menu']
        menu_string_branch = next(
            b for b in menu['anyOf'] if b.get('type') == 'string'
        )
        assert menu_string_branch['enum'] == ['cartoes', 'humano']
        null_branch = next(b for b in menu['anyOf'] if b.get('type') == 'null')
        assert 'enum' not in null_branch

        end_action_id = action_def['properties']['end_action_id']
        end_action_string_branch = next(
            b for b in end_action_id['anyOf'] if b.get('type') == 'string'
        )
        assert end_action_string_branch['enum'] == ['encerrado']

    def test_cache_nao_vaza_entre_combinacoes_diferentes(self):
        schema_a = build_agent_result_schema(('cartoes',))
        schema_b = build_agent_result_schema(('humano',))
        action_a = schema_a['$defs']['AgentAction']['properties']['menu']
        action_b = schema_b['$defs']['AgentAction']['properties']['menu']
        branch_a = next(
            b for b in action_a['anyOf'] if b.get('type') == 'string'
        )
        branch_b = next(
            b for b in action_b['anyOf'] if b.get('type') == 'string'
        )
        assert branch_a['enum'] == ['cartoes']
        assert branch_b['enum'] == ['humano']
