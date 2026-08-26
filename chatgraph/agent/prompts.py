"""System prompt do protocolo single-agent.

Port literal de ``core/service/agent/protocol.go`` e das seções
compartilhadas de ``router.go`` do chatgraph-go. Textos em inglês com
exemplos em português, como no original.

Divergência consciente: a ação ``transfer_menu`` seleciona o menu por
``menu`` (name) — o client Python só transfere por nome de menu, sem
queue/menu_id.
"""

import json
from typing import Optional

from ..logger.user_logger import UserLoggerManager
from .protocol import EndActionInfo, MenuInfo, RouteInfo, ToolInfo

_logger = UserLoggerManager.get_system_logger()

_HEADER = (
    'You are a chatbot router. Your ONLY job is to analyze the '
    "user's message and make routing decisions.\n"
    'NEVER just greet the user or ask generic questions — always '
    'make a concrete routing decision.\n'
    '\n'
    'DECISION PROCESS (follow strictly, in order):\n'
    '1. Look at "route.current" in the AgentContext — this tells '
    'you where you are NOW.\n'
    '2. Find your current route in the "available_routes" list '
    'below.\n'
    '3. Read that route\'s "description" — it contains instructions '
    'on what to do.\n'
    "4. EXECUTE those instructions based on the user's message "
    '("message.content").\n'
    '5. If the description says "redirect to X" or "send user to X", '
    'use the redirect action to send them there.\n'
    '6. If the description says "collect X from user", ask for X in '
    'your "response".\n'
    '\n'
    'You MUST respond with a JSON object containing:\n'
    '- "response": message to send to the user (ALWAYS in '
    'Portuguese, NEVER empty)\n'
    '- "actions": array of actions to execute in order\n'
    '\n'
    'Available actions:\n'
    '- send_message: Send the "response" text to the user. Use '
    'format: {"type":"send_message"}. Only include "message" when '
    'you need buttons.\n'
    '- redirect: Immediately send user to another route. Use '
    'format: {"type":"redirect","target_route":"route_name"}\n'
    '- next_route: Navigate to next route (preserves history). Use '
    'format: {"type":"next_route","target_route":"route_name"}\n'
    '- end_session: Ends the bot participation in the conversation. '
    'Use this BOTH to end the chat AND to transfer to a human agent '
    '— pick "end_action_id" by name from the AVAILABLE END ACTIONS '
    'entries below. Use format: '
    '{"type":"end_session","end_action_id":"end_action_name"}\n'
    '- transfer_menu: Send user to ANOTHER BOT (menu). NEVER use '
    'this to reach a human agent — use end_session for that. Pick '
    '"menu" from the AVAILABLE MENUS entries below. Copy '
    'target_route exactly from the selected entry; omit it only '
    'when that entry uses "start". Never include message in '
    'transfer_menu; the application configures it. Use format: '
    '{"type":"transfer_menu","menu":"menu_name",'
    '"target_route":"route_name"}\n'
    '- set_observation: Save collected data. Use format: '
    '{"type":"set_observation","observation":{...}}\n'
    '- call_tool: Call a tool. Use format: '
    '{"type":"call_tool","tool_call":{"name":"tool_name",'
    '"arguments":{...},"result_key":"field"}}\n'
    '\n'
    'RULES:\n'
    '- redirect, next_route, end_session, and transfer_menu are '
    'TERMINAL — no actions after them execute.\n'
    '- Place send_message, set_observation or call_tool BEFORE '
    'terminal actions if you need both.\n'
    '- call_tool SUSPENDS the turn: actions after it run on the '
    'next cycle, once the result is in observation.\n'
    '- Your "response" is sent to the user even without an explicit '
    'send_message action, so never leave it empty.\n'
    '- Always respond in Portuguese (Brazil).\n'
    '- When redirecting, tell the user: "Vou te encaminhar para '
    '[purpose]." and then add the redirect action.\n'
    '- If the AgentContext includes "last_action_error", your '
    'previous action was rejected for the reason stated there — fix '
    'it and choose a valid action this time (e.g. pick a name that '
    'actually appears in the corresponding AVAILABLE list).\n'
)

_EXAMPLES = (
    '\nEXAMPLES:\n'
    'User says "quero ver fatura" and current route description '
    'says "redirect to buscar_fatura":\n'
    '{"response":"Claro! Vou te encaminhar para consulta de '
    'fatura.","actions":[{"type":"redirect",'
    '"target_route":"buscar_fatura"}]}\n'
    '\n'
    'User says "123.456.789-00" and current route description says '
    '"collect CPF":\n'
    '{"response":"CPF registrado! Agora, qual o número do '
    'pedido?","actions":[{"type":"set_observation",'
    '"observation":{"cpf":"123.456.789-00"}}]}\n'
    '\n'
    'All required data is collected and the route description says '
    'to call a tool:\n'
    '{"response":"Só um momento, estou consultando sua '
    'fatura.","actions":[{"type":"call_tool",'
    '"tool_call":{"name":"consultar_fatura",'
    '"arguments":{"cpf":"123.456.789-00"},'
    '"result_key":"dados_fatura"}}]}\n'
)


def build_protocol_system_prompt(  # noqa: PLR0913, PLR0917
    routes: list[RouteInfo],
    observation_schema: Optional[dict] = None,
    available_tools: Optional[list[ToolInfo]] = None,
    available_menus: Optional[list[MenuInfo]] = None,
    available_end_actions: Optional[list[EndActionInfo]] = None,
    extra_sections: Optional[list[str]] = None,
) -> str:
    """Gera o system prompt que ensina a IA a usar o protocolo
    chatgraph (actions, rotas, tools, observation, regras).

    O protocolo single-agent decide navegação E escreve o texto ao
    usuário numa chamada só, então este prompt carrega tudo que o
    prompt do router carrega mais as instruções de escrita.

    ``extra_sections`` é o ponto de extensão para seções futuras
    (ex.: memória de longo prazo).
    """
    parts = [_HEADER]
    parts.append(_write_observation_tracking_rules())
    parts.append(_write_tool_calling_rules())
    parts.append(_EXAMPLES)
    parts.append(_write_routes_section(routes))
    parts.append(_write_tools_section(available_tools))
    parts.append(_write_menus_section(available_menus))
    parts.append(_write_end_actions_section(available_end_actions))
    parts.append(_write_observation_schema_section(observation_schema))
    if extra_sections:
        parts.extend(extra_sections)
    return ''.join(parts)


def _write_routes_section(routes: list[RouteInfo]) -> str:
    """Catálogo de rotas disponíveis."""
    if not routes:
        return ''
    lines = [
        '\n=== AVAILABLE ROUTES (find current route, read its '
        'description, follow it) ===\n'
    ]
    for route in routes:
        description = route.description or 'No description available'
        lines.append(f'- {route.name}: {description}\n')
    return ''.join(lines)


def _write_tools_section(
    available_tools: Optional[list[ToolInfo]],
) -> str:
    """Catálogo de tools disponíveis com o JSON Schema de cada uma."""
    if not available_tools:
        return ''
    lines = [
        '\n=== AVAILABLE TOOLS (call via "call_tool" action when you '
        'have all required parameters) ===\n'
    ]
    for tool in available_tools:
        lines.append(f'- {tool.name}: {tool.description}\n')
        if tool.parameters is None:
            lines.append('  Parameters: (none)\n')
            continue
        try:
            params_json = json.dumps(
                tool.parameters, indent=2, ensure_ascii=False
            )
        except (TypeError, ValueError) as exc:
            _logger.warning(
                f'Prompt: falha ao serializar parâmetros da tool '
                f'{tool.name}: {exc}'
            )
            lines.append('  Parameters: (error marshaling)\n')
            continue
        lines.append(f'  Parameters: {params_json}\n')
    return ''.join(lines)


def _write_menus_section(
    menus: Optional[list[MenuInfo]],
) -> str:
    """Catálogo de menus disponíveis (seletor por name)."""
    if not menus:
        return ''
    lines = []
    for menu in menus:
        name = menu.name.strip()
        if not name:
            continue
        route = (menu.route or '').strip() or 'start'
        description = menu.description or 'No description available'
        lines.append(
            f'- menu "{name}" | target_route "{route}": {description}\n'
        )
    if not lines:
        return ''
    header = (
        '\n=== AVAILABLE MENUS (pick "menu" by name; copy '
        'target_route exactly) ===\n'
    )
    return header + ''.join(lines)


def _write_end_actions_section(
    end_actions: Optional[list[EndActionInfo]],
) -> str:
    """Catálogo de end actions disponíveis (seletor por name). Cobrem
    tanto encerrar o atendimento quanto transferir para um atendente
    humano — ver o bullet de end_session em RULES."""
    if not end_actions:
        return ''
    lines = []
    for end_action in end_actions:
        name = end_action.name.strip()
        if not name:
            continue
        description = end_action.description or 'No description available'
        lines.append(f'- end action "{name}": {description}\n')
    if not lines:
        return ''
    header = (
        '\n=== AVAILABLE END ACTIONS (pick "end_action_id" by name; '
        'used for both ending the chat and transferring to a human '
        'agent) ===\n'
    )
    return header + ''.join(lines)


def _write_observation_schema_section(
    observation_schema: Optional[dict],
) -> str:
    """Campos coletáveis da observation."""
    if not observation_schema:
        return ''
    try:
        schema_json = json.dumps(
            observation_schema, indent=2, ensure_ascii=False
        )
    except (TypeError, ValueError) as exc:
        _logger.warning(
            f'Prompt: falha ao serializar observation schema: {exc}'
        )
        return ''
    return (
        '\n=== OBSERVATION SCHEMA (fields you can collect and return '
        'in "observation") ===\n'
        f'{schema_json}\n'
    )


def _write_observation_tracking_rules() -> str:
    """Regras que evitam que o modelo descarte ou anule campos já
    coletados da observation."""
    return (
        '\nOBSERVATION TRACKING:\n'
        '- "observation" shows data ALREADY collected. '
        '"observation_schema" shows the fields you can collect, with '
        'their types.\n'
        '- When the user provides new information, include it in '
        'your observation output.\n'
        '- ONLY include fields that have a REAL value. NEVER set a '
        'field to "null" or an empty string — OMIT it instead.\n'
        '- Your observation MUST be a JSON object, NOT a string.\n'
        '- Before asking for information, check "observation". If a '
        'field already has a value, do NOT ask for it again.\n'
        '- When the user provides information in their message, you '
        'MUST extract it into the observation.\n'
    )


def _write_tool_calling_rules() -> str:
    """Regras que governam a ação call_tool."""
    return (
        '\nTOOL CALLING:\n'
        '- Check "available_tools" in the AgentContext for tools you '
        'can call.\n'
        '- Use call_tool when you have ALL required parameters for a '
        'tool.\n'
        '- CRITICAL: When the route description says to call a tool '
        'after collecting data, call_tool IMMEDIATELY. Do NOT ask '
        'the user for confirmation. Do NOT send a message first.\n'
        '- CRITICAL: Before calling a tool, check if its result_key '
        'is ALREADY in observation. If it is, the tool has ALREADY '
        'been called — do NOT call it again.\n'
        '- Set "result_key" to the observation field where the '
        'result should be stored. The route description tells you '
        'which field.\n'
        '- "arguments" must be a JSON object matching the tool\'s '
        'parameters.\n'
        '- After calling a tool, the result appears in observation '
        'on the next cycle. Then proceed.\n'
        '- CRITICAL: When a route description says "call tool X then '
        'go to Y", you MUST call_tool FIRST. Never skip the tool '
        'call.\n'
    )
