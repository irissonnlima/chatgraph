"""Testes para a construção do system prompt do protocolo."""

import pytest

from chatgraph.agent.prompts import build_protocol_system_prompt
from chatgraph.agent.protocol import (
    EndActionInfo,
    MenuInfo,
    RouteInfo,
    ToolInfo,
)


def _routes() -> list[RouteInfo]:
    return [
        RouteInfo(name='start', description='Triage the user intent.'),
        RouteInfo(name='faq', description=None),
    ]


@pytest.mark.unit
class TestProtocolPromptScenario:
    def test_cabecalho_e_regras_presentes(self):
        prompt = build_protocol_system_prompt(_routes())
        assert 'You are a chatbot router.' in prompt
        assert 'DECISION PROCESS (follow strictly, in order):' in prompt
        assert 'RULES:' in prompt
        assert 'OBSERVATION TRACKING:' in prompt
        assert 'TOOL CALLING:' in prompt
        assert 'EXAMPLES:' in prompt
        assert 'Always respond in Portuguese (Brazil).' in prompt

    def test_formatos_das_actions(self):
        prompt = build_protocol_system_prompt(_routes())
        assert '{"type":"send_message"}' in prompt
        assert (
            '{"type":"redirect","target_route":"route_name"}' in prompt
        )
        assert (
            '{"type":"next_route","target_route":"route_name"}'
            in prompt
        )
        assert (
            '{"type":"end_session","end_action_id":"end_action_name"}'
            in prompt
        )
        assert (
            '{"type":"transfer_menu","menu":"menu_name",'
            '"target_route":"route_name"}' in prompt
        )
        assert (
            '{"type":"set_observation","observation":{...}}' in prompt
        )
        assert '"result_key":"field"' in prompt

    def test_transfer_menu_nao_menciona_queue_nem_menu_id(self):
        prompt = build_protocol_system_prompt(_routes())
        assert 'queue' not in prompt
        assert 'menu_id' not in prompt

    def test_end_session_cobre_encerrar_e_humano(self):
        prompt = build_protocol_system_prompt(_routes())
        assert 'end_session' in prompt
        assert 'transfer to a human agent' in prompt

    def test_transfer_menu_nunca_para_humano(self):
        prompt = build_protocol_system_prompt(_routes())
        assert 'ANOTHER BOT' in prompt
        assert 'NEVER use this to reach a human agent' in prompt

    def test_regra_de_correcao_de_last_action_error(self):
        prompt = build_protocol_system_prompt(_routes())
        assert 'last_action_error' in prompt

    def test_secao_de_rotas_com_fallback_de_descricao(self):
        prompt = build_protocol_system_prompt(_routes())
        assert '=== AVAILABLE ROUTES' in prompt
        assert '- start: Triage the user intent.\n' in prompt
        assert '- faq: No description available\n' in prompt

    def test_exemplos_portados_do_go(self):
        prompt = build_protocol_system_prompt(_routes())
        assert 'quero ver fatura' in prompt
        assert '"target_route":"buscar_fatura"' in prompt
        assert '"observation":{"cpf":"123.456.789-00"}' in prompt
        assert '"result_key":"dados_fatura"' in prompt


@pytest.mark.unit
class TestPromptSectionsScenario:
    def test_secoes_vazias_sao_omitidas(self):
        prompt = build_protocol_system_prompt([])
        assert '=== AVAILABLE ROUTES' not in prompt
        assert '=== AVAILABLE TOOLS' not in prompt
        assert '=== AVAILABLE MENUS' not in prompt
        assert '=== AVAILABLE END ACTIONS' not in prompt
        assert '=== OBSERVATION SCHEMA' not in prompt

    def test_secao_de_tools_com_schema_json(self):
        tools = [
            ToolInfo(
                name='consultar_pedido',
                description='Consulta um pedido.',
                parameters={
                    'type': 'object',
                    'properties': {'cpf': {'type': 'string'}},
                },
            ),
            ToolInfo(name='ping', description='Sem parâmetros.'),
        ]
        prompt = build_protocol_system_prompt(
            _routes(), available_tools=tools
        )
        assert '=== AVAILABLE TOOLS' in prompt
        assert '- consultar_pedido: Consulta um pedido.' in prompt
        assert '"cpf"' in prompt
        assert '  Parameters: (none)\n' in prompt

    def test_secao_de_menus_por_name(self):
        menus = [
            MenuInfo(
                name='cartoes',
                route='bloqueio',
                description='Bloqueio e cartões.',
            ),
            MenuInfo(name='humano'),
            MenuInfo(name='  '),
        ]
        prompt = build_protocol_system_prompt(
            _routes(), available_menus=menus
        )
        assert '=== AVAILABLE MENUS' in prompt
        assert (
            '- menu "cartoes" | target_route "bloqueio": '
            'Bloqueio e cartões.\n' in prompt
        )
        assert (
            '- menu "humano" | target_route "start": '
            'No description available\n' in prompt
        )
        assert '- menu ""' not in prompt

    def test_menus_sem_name_omitem_secao(self):
        prompt = build_protocol_system_prompt(
            _routes(), available_menus=[MenuInfo(name='  ')]
        )
        assert '=== AVAILABLE MENUS' not in prompt

    def test_secao_de_end_actions_por_name(self):
        end_actions = [
            EndActionInfo(
                name='humano',
                description='Transferir para atendente humano.',
            ),
            EndActionInfo(name='resolvido'),
            EndActionInfo(name='  '),
        ]
        prompt = build_protocol_system_prompt(
            _routes(), available_end_actions=end_actions
        )
        assert '=== AVAILABLE END ACTIONS' in prompt
        assert (
            '- end action "humano": Transferir para atendente '
            'humano.\n' in prompt
        )
        assert '- end action "resolvido": No description available\n' in prompt
        assert '- end action ""' not in prompt

    def test_end_actions_sem_name_omitem_secao(self):
        prompt = build_protocol_system_prompt(
            _routes(), available_end_actions=[EndActionInfo(name='  ')]
        )
        assert '=== AVAILABLE END ACTIONS' not in prompt

    def test_secao_de_observation_schema(self):
        schema = {
            'type': 'object',
            'properties': {'cpf': {'type': 'string'}},
        }
        prompt = build_protocol_system_prompt(
            _routes(), observation_schema=schema
        )
        assert '=== OBSERVATION SCHEMA' in prompt
        assert '"cpf"' in prompt

    def test_extra_sections_apendadas_no_final(self):
        prompt = build_protocol_system_prompt(
            _routes(), extra_sections=['\n=== MEMORY ===\nfatos\n']
        )
        assert prompt.endswith('\n=== MEMORY ===\nfatos\n')
