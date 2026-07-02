import pytest

from chatgraph.models.platform_state import PlatformState, VollStateData


@pytest.mark.unit
class TestPlatformState:
    def test_from_dict_with_valid_data(self):
        ps = PlatformState.from_dict({'a': 1})
        assert ps.data == {'a': 1}

    def test_from_dict_with_none(self):
        ps = PlatformState.from_dict(None)
        assert ps.data == {}

    def test_bool_true_when_data_present(self):
        ps = PlatformState(data={'x': 1})
        assert bool(ps) is True

    def test_bool_false_when_data_empty(self):
        ps = PlatformState(data={})
        assert bool(ps) is False

    def test_to_dict_roundtrip(self):
        data = {'a': 1, 'b': 'teste'}
        ps = PlatformState.from_dict(data)
        assert ps.to_dict() == data

    def test_as_voll_with_valid_data(self):
        voll_data = {
            'session_id': 123,
            'customer_id': 'CUST001',
            'platform': 'whatsapp_enterprise',
            'protocol': 'PROTO001',
            'campaign': 'CAMPANHA.TESTE',
        }
        ps = PlatformState(data=voll_data)
        voll = ps.as_voll
        assert isinstance(voll, VollStateData)
        assert voll.session_id == 123
        assert voll.customer_id == 'CUST001'
        assert voll.platform == 'whatsapp_enterprise'
        assert voll.protocol == 'PROTO001'
        assert voll.campaign == 'CAMPANHA.TESTE'

    def test_as_voll_with_invalid_data(self):
        ps = PlatformState(data={'session_id': 1})
        assert ps.as_voll is None

    def test_as_voll_with_empty_data(self):
        ps = PlatformState(data={})
        assert ps.as_voll is None
