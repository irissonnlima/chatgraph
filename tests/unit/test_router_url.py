# ruff: noqa: PLR6301 - testes em classe e literais nos asserts, como no
# resto da suíte.
import pytest

from chatgraph.services.router_http_client import (
    RouterHTTPClient,
    router_v1_base,
)

SAME_HOST_FORMS = [
    'http://h',
    'http://h/',
    'http://h/v1',
    'http://h/v1/',
    'http://h/v1/actions',
    'http://h/v1/actions/',
]


@pytest.mark.unit
class TestRouterV1Base:
    @pytest.mark.parametrize('url', SAME_HOST_FORMS)
    def test_same_host_forms_resolve_to_v1(self, url):
        assert router_v1_base(url) == 'http://h/v1'

    @pytest.mark.parametrize(
        ('url', 'expected'),
        [
            ('https://h/api/v1/actions', 'https://h/api/v1'),
            ('https://h/api', 'https://h/api/v1'),
            ('  http://h/v1/actions/  ', 'http://h/v1'),
        ],
    )
    def test_prefixed_and_padded_urls(self, url, expected):
        assert router_v1_base(url) == expected


@pytest.mark.unit
class TestRouterHTTPClientUrl:
    @pytest.mark.parametrize('url', SAME_HOST_FORMS)
    def test_same_host_forms_build_same_clients(self, url):
        client = RouterHTTPClient(url, username='u', password='p')

        assert str(client._actions_client.base_url) == 'http://h/v1/actions/'
        assert (
            str(client._id_positiva_client.base_url)
            == 'http://h/v1/id-positiva/'
        )

    @pytest.mark.parametrize('url', SAME_HOST_FORMS)
    def test_base_url_keeps_input_without_trailing_slash(self, url):
        client = RouterHTTPClient(url, username='u', password='p')

        assert client.base_url == url.rstrip('/')
