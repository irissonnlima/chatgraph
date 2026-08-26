"""Reescreve JSON Schemas para o subset aceito pelo Structured Outputs.

O contrato oficial tem duas regras que geradores automáticos (pydantic,
reflection) não seguem: todo objeto precisa ser fechado com
``additionalProperties: false`` e toda propriedade precisa constar em
``required``. Opcionalidade é expressa unindo o tipo com ``"null"`` em vez
de deixar o campo fora de ``required``.

Este módulo é uma folha: não depende de nada dentro do projeto.

Port de ``core/domain/jsonschema/normalize.go`` do chatgraph-go.
"""

import copy
from typing import Any, Optional

# Documenta o fallback aplicado a nós de schema que não podem ser
# expressos como objeto fechado. Structured Outputs não tem escape para
# objeto aberto: additionalProperties deve ser false, então um objeto sem
# properties declaradas só casaria com {}. Campos `Any`/dict viram string
# JSON e são decodificados de volta na leitura (decode_json_string_maybe).
JSON_STRING_DESCRIPTION = 'JSON-encoded value, serialized as a string.'

# Keywords removidos de todo nó. Os de composição são documentados como
# não suportados; os demais estão fora do conjunto suportado documentado.
# Remover uma restrição só afrouxa a validação; mantê-la rejeita a
# requisição inteira. `title` e `default` entram na lista porque o
# pydantic os emite em todo nó e não fazem parte do subset.
UNSUPPORTED_KEYWORDS = (
    # Documentados como não suportados.
    'allOf',
    'not',
    'if',
    'then',
    'else',
    'dependentRequired',
    'dependentSchemas',
    # Fora do conjunto suportado documentado.
    'maxLength',
    'patternProperties',
    'unevaluatedProperties',
    'propertyNames',
    'minProperties',
    'maxProperties',
    'unevaluatedItems',
    'contains',
    'minContains',
    'maxContains',
    'uniqueItems',
    # Emitidos pelo pydantic, fora do subset.
    'title',
    'default',
)


def normalize(schema: Optional[dict]) -> dict:
    """Retorna cópia estrita de ``schema``, que deve descrever um objeto
    raiz. O input nunca é mutado.

    Um schema que não pode ser representado como objeto (None, vazio ou
    mapa aberto) degrada para um objeto fechado vazio em vez de produzir
    uma requisição inválida.
    """
    node = _normalize_node(schema or {})
    if _is_object_node(node):
        return node
    return {
        'type': 'object',
        'properties': {},
        'required': [],
        'additionalProperties': False,
    }


def normalize_subschema(schema: Optional[dict]) -> dict:
    """``normalize`` sem a garantia de raiz, para nós mesclados em um
    schema maior. Input sem nada a declarar degrada para string JSON
    anulável em vez de objeto vazio (que só casaria com {})."""
    return _normalize_node(schema or {})


def nullable(node: dict) -> dict:
    """Retorna cópia de ``node`` cuja união de tipos inclui ``"null"``.

    Nós sem keyword ``type`` voltam inalterados: não há tipo a alargar, e
    ``normalize`` já os transforma em string JSON anulável.
    """
    out = copy.deepcopy(node)
    node_type = out.get('type')
    if isinstance(node_type, str):
        if node_type != 'null':
            out['type'] = [node_type, 'null']
    elif isinstance(node_type, list):
        if 'null' not in node_type:
            out['type'] = [*node_type, 'null']
    return out


def _is_object_node(node: dict) -> bool:
    """Informa se o nó foi normalizado em um objeto fechado."""
    if not isinstance(node.get('properties'), dict):
        return False
    return _has_type(node, 'object')


def _normalize_node(node: dict) -> dict:
    """Reescreve um nó de schema e tudo abaixo dele."""
    if not node:
        return _json_string_fallback()

    # Nós $ref não carregam restrições inline a reescrever, e o alvo é
    # normalizado onde é definido.
    if '$ref' in node:
        return copy.deepcopy(node)

    out = copy.deepcopy(node)

    for keyword in UNSUPPORTED_KEYWORDS:
        out.pop(keyword, None)
    _fold_min_length(out)

    # Nó sem nenhum keyword de shape (caso típico: campo `Any` do
    # pydantic, que só emite title/default) tem shape desconhecido —
    # mesmo destino do `any` na reflection do Go: string JSON.
    if not _has_shape(out):
        return _json_string_fallback()

    defs = out.get('$defs')
    if isinstance(defs, dict):
        out['$defs'] = _normalize_children(defs)

    # Cada branch de anyOf precisa satisfazer o mesmo subset.
    branches = out.get('anyOf')
    if isinstance(branches, list):
        out['anyOf'] = [
            _normalize_node(branch) if isinstance(branch, dict) else branch
            for branch in branches
        ]

    if _has_type(out, 'object'):
        props = out.get('properties')
        if not isinstance(props, dict):
            # Sem cláusula properties o shape nunca foi conhecido (dict,
            # Any ou schema aberto). Fechar deixaria um nó que só casa
            # com {}, então o valor viaja como string. Um properties
            # declarado porém vazio é diferente — é um "struct" sem
            # campos, e {} é de fato seu único valor válido.
            return _json_string_fallback()
        out['properties'] = _normalize_children(props)
        out['required'] = _sorted_keys(props)
        out['additionalProperties'] = False
    else:
        # additionalProperties só tem significado em objetos; solto em
        # um escalar é erro de schema.
        out.pop('additionalProperties', None)

    if _has_type(out, 'array'):
        out['items'] = _normalize_items(out.get('items'))

    _align_enum_with_null(out)

    return out


def _normalize_children(children: dict) -> dict:
    """Normaliza cada valor de um mapa properties/$defs."""
    return {
        name: _normalize_node(child) if isinstance(child, dict) else child
        for name, child in children.items()
    }


def _normalize_items(raw: Any) -> Any:
    """Normaliza a cláusula items de um array (forma única ou tupla)."""
    if isinstance(raw, dict):
        return _normalize_node(raw)
    if isinstance(raw, list):
        return [
            _normalize_node(entry) if isinstance(entry, dict) else entry
            for entry in raw
        ]
    # items ausente ou inutilizável: array de valores sem restrição não é
    # representável, então os elementos viajam como strings JSON.
    return _json_string_fallback()


def _json_string_fallback() -> dict:
    """Representação de valores sem equivalente em objeto fechado.
    Anulável para o modelo poder declinar de preencher."""
    return {
        'type': ['string', 'null'],
        'description': JSON_STRING_DESCRIPTION,
    }


def _fold_min_length(node: dict) -> None:
    """Remove minLength preservando a intenção na description, já que
    restrições de tamanho não fazem parte dos keywords suportados."""
    if 'minLength' not in node:
        return
    raw = node.pop('minLength')

    if not isinstance(raw, (int, float)) or isinstance(raw, bool):
        return
    if raw <= 0:
        return
    hint = f'Minimum length: {int(raw)} characters.'
    description = node.get('description')
    if isinstance(description, str) and description:
        node['description'] = f'{description} {hint}'
        return
    node['description'] = hint


def _align_enum_with_null(node: dict) -> None:
    """Mantém um enum consistente com união de tipos anulável, para um
    campo que o modelo pode deixar vazio ter null como valor legal."""
    if not _has_type(node, 'null'):
        return
    values = node.get('enum')
    if not isinstance(values, list):
        return
    if any(value is None for value in values):
        return
    node['enum'] = [*values, None]


_SHAPE_KEYWORDS = (
    'type',
    'properties',
    'anyOf',
    'oneOf',
    'enum',
    'const',
    'items',
    '$ref',
)


def _has_shape(node: dict) -> bool:
    """Informa se o nó declara algum keyword que define seu shape."""
    return any(keyword in node for keyword in _SHAPE_KEYWORDS)


def _has_type(node: dict, want: str) -> bool:
    """Informa se o nó declara ``want`` na forma escalar ou de união do
    keyword type."""
    node_type = node.get('type')
    if isinstance(node_type, str):
        return node_type == want
    if isinstance(node_type, list):
        return want in node_type
    return False


def _sorted_keys(props: dict) -> list[str]:
    """Chaves de props em ordem estável, para schemas gerados compararem
    iguais entre execuções."""
    return sorted(props)
