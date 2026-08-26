"""Testes para o normalizador de JSON Schema do módulo de agentes."""

import pytest

from chatgraph.agent.schema import (
    JSON_STRING_DESCRIPTION,
    normalize,
    normalize_subschema,
    nullable,
)


@pytest.mark.unit
class TestNormalizeObjectScenario:
    def test_fecha_objeto_com_additional_properties_false(self):
        schema = {
            'type': 'object',
            'properties': {'nome': {'type': 'string'}},
        }
        result = normalize(schema)
        assert result['additionalProperties'] is False

    def test_required_contem_todas_as_propriedades_ordenadas(self):
        schema = {
            'type': 'object',
            'properties': {
                'zeta': {'type': 'string'},
                'alfa': {'type': 'integer'},
                'meio': {'type': 'number'},
            },
        }
        result = normalize(schema)
        assert result['required'] == ['alfa', 'meio', 'zeta']

    def test_nao_muta_o_input(self):
        schema = {
            'type': 'object',
            'properties': {'nome': {'type': 'string', 'title': 'Nome'}},
        }
        normalize(schema)
        assert 'additionalProperties' not in schema
        assert schema['properties']['nome'] == {
            'type': 'string',
            'title': 'Nome',
        }

    def test_objeto_aninhado_tambem_e_fechado(self):
        schema = {
            'type': 'object',
            'properties': {
                'endereco': {
                    'type': 'object',
                    'properties': {'rua': {'type': 'string'}},
                },
            },
        }
        result = normalize(schema)
        inner = result['properties']['endereco']
        assert inner['additionalProperties'] is False
        assert inner['required'] == ['rua']

    def test_raiz_invalida_degrada_para_objeto_fechado_vazio(self):
        for raw in (None, {}, {'type': 'string'}):
            result = normalize(raw)
            assert result == {
                'type': 'object',
                'properties': {},
                'required': [],
                'additionalProperties': False,
            }

    def test_properties_declarado_vazio_permanece_objeto(self):
        schema = {'type': 'object', 'properties': {}}
        result = normalize(schema)
        assert result['properties'] == {}
        assert result['required'] == []


@pytest.mark.unit
class TestUnsupportedKeywordsScenario:
    def test_remove_keywords_nao_suportados(self):
        schema = {
            'type': 'object',
            'properties': {'nome': {'type': 'string', 'maxLength': 10}},
            'allOf': [{'type': 'object'}],
            'not': {'type': 'string'},
            'patternProperties': {},
            'uniqueItems': True,
        }
        result = normalize(schema)
        for keyword in ('allOf', 'not', 'patternProperties', 'uniqueItems'):
            assert keyword not in result
        assert 'maxLength' not in result['properties']['nome']

    def test_remove_title_e_default_emitidos_pelo_pydantic(self):
        schema = {
            'type': 'object',
            'title': 'Modelo',
            'properties': {
                'nome': {'type': 'string', 'title': 'Nome', 'default': ''},
            },
        }
        result = normalize(schema)
        assert 'title' not in result
        assert 'title' not in result['properties']['nome']
        assert 'default' not in result['properties']['nome']

    def test_fold_min_length_para_description(self):
        schema = {
            'type': 'object',
            'properties': {
                'cpf': {
                    'type': 'string',
                    'minLength': 11,
                    'description': 'CPF do cliente.',
                },
                'nome': {'type': 'string', 'minLength': 3},
                'zerado': {'type': 'string', 'minLength': 0},
            },
        }
        result = normalize(schema)
        props = result['properties']
        assert props['cpf']['description'] == (
            'CPF do cliente. Minimum length: 11 characters.'
        )
        assert 'minLength' not in props['cpf']
        assert props['nome']['description'] == (
            'Minimum length: 3 characters.'
        )
        assert 'description' not in props['zerado']


@pytest.mark.unit
class TestJsonStringFallbackScenario:
    def test_objeto_sem_properties_vira_string_json(self):
        result = normalize_subschema({'type': 'object'})
        assert result == {
            'type': ['string', 'null'],
            'description': JSON_STRING_DESCRIPTION,
        }

    def test_no_vazio_vira_string_json(self):
        result = normalize_subschema({})
        assert result['type'] == ['string', 'null']

    def test_campo_dict_dentro_de_objeto_vira_string_json(self):
        schema = {
            'type': 'object',
            'properties': {'observation': {'type': 'object'}},
        }
        result = normalize(schema)
        obs = result['properties']['observation']
        assert obs['type'] == ['string', 'null']
        assert obs['description'] == JSON_STRING_DESCRIPTION

    def test_array_sem_items_carrega_strings_json(self):
        schema = {
            'type': 'object',
            'properties': {'valores': {'type': 'array'}},
        }
        result = normalize(schema)
        items = result['properties']['valores']['items']
        assert items['type'] == ['string', 'null']


@pytest.mark.unit
class TestArraysAndCompositionScenario:
    def test_items_forma_unica_normalizado(self):
        schema = {
            'type': 'object',
            'properties': {
                'itens': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {'sku': {'type': 'string'}},
                    },
                },
            },
        }
        result = normalize(schema)
        items = result['properties']['itens']['items']
        assert items['additionalProperties'] is False
        assert items['required'] == ['sku']

    def test_items_forma_tupla_normalizada(self):
        schema = {
            'type': 'object',
            'properties': {
                'par': {
                    'type': 'array',
                    'items': [{'type': 'object'}, {'type': 'string'}],
                },
            },
        }
        result = normalize(schema)
        first, second = result['properties']['par']['items']
        assert first['type'] == ['string', 'null']
        assert second == {'type': 'string'}

    def test_branches_de_anyof_sao_normalizados(self):
        schema = {
            'type': 'object',
            'properties': {
                'campo': {
                    'anyOf': [
                        {
                            'type': 'object',
                            'properties': {'x': {'type': 'string'}},
                        },
                        {'type': 'null'},
                    ],
                },
            },
        }
        result = normalize(schema)
        branches = result['properties']['campo']['anyOf']
        assert branches[0]['additionalProperties'] is False
        assert branches[1] == {'type': 'null'}

    def test_defs_sao_normalizados_e_ref_preservado(self):
        schema = {
            'type': 'object',
            'properties': {'item': {'$ref': '#/$defs/Item'}},
            '$defs': {
                'Item': {
                    'type': 'object',
                    'properties': {'sku': {'type': 'string'}},
                },
            },
        }
        result = normalize(schema)
        assert result['properties']['item'] == {'$ref': '#/$defs/Item'}
        item = result['$defs']['Item']
        assert item['additionalProperties'] is False
        assert item['required'] == ['sku']

    def test_additional_properties_removido_de_escalares(self):
        schema = {
            'type': 'object',
            'properties': {
                'nome': {'type': 'string', 'additionalProperties': False},
            },
        }
        result = normalize(schema)
        assert 'additionalProperties' not in result['properties']['nome']


@pytest.mark.unit
class TestEnumAndNullableScenario:
    def test_enum_alinhado_com_null(self):
        schema = {
            'type': 'object',
            'properties': {
                'status': {
                    'type': ['string', 'null'],
                    'enum': ['ativo', 'inativo'],
                },
            },
        }
        result = normalize(schema)
        assert result['properties']['status']['enum'] == [
            'ativo',
            'inativo',
            None,
        ]

    def test_enum_ja_com_null_nao_duplica(self):
        schema = {
            'type': 'object',
            'properties': {
                'status': {
                    'type': ['string', 'null'],
                    'enum': ['ativo', None],
                },
            },
        }
        result = normalize(schema)
        assert result['properties']['status']['enum'] == ['ativo', None]

    def test_enum_sem_null_no_tipo_permanece(self):
        schema = {
            'type': 'object',
            'properties': {
                'status': {'type': 'string', 'enum': ['ativo']},
            },
        }
        result = normalize(schema)
        assert result['properties']['status']['enum'] == ['ativo']

    def test_nullable_escalar(self):
        assert nullable({'type': 'string'})['type'] == ['string', 'null']

    def test_nullable_uniao_existente(self):
        node = {'type': ['string', 'integer']}
        assert nullable(node)['type'] == ['string', 'integer', 'null']

    def test_nullable_idempotente(self):
        node = {'type': ['string', 'null']}
        assert nullable(node)['type'] == ['string', 'null']

    def test_nullable_sem_type_volta_inalterado(self):
        assert nullable({'description': 'x'}) == {'description': 'x'}


@pytest.mark.unit
class TestIdempotencyScenario:
    def test_normalize_e_idempotente(self):
        schema = {
            'type': 'object',
            'properties': {
                'nome': {'type': 'string', 'minLength': 3},
                'meta': {'type': 'object'},
                'itens': {'type': 'array', 'items': {'type': 'string'}},
                'status': {
                    'type': ['string', 'null'],
                    'enum': ['a', 'b'],
                },
            },
        }
        once = normalize(schema)
        twice = normalize(once)
        assert once == twice
