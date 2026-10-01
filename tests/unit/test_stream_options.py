# ruff: noqa: PLR2004, PLR6301 - testes em classe e literais nos asserts, como no
# resto da suíte.
import pytest

from chatgraph.stream.errors import StreamConfigError
from chatgraph.stream.options import (
    StreamOptions,
    connect_url,
    normalize_menus,
    normalize_options,
)

SAME_HOST_FORMS = [
    'http://router-a:8085',
    'http://router-a:8085/',
    'http://router-a:8085/v1',
    'http://router-a:8085/v1/',
    'http://router-a:8085/v1/actions',
    'http://router-a:8085/v1/actions/',
]


def make_options(**kwargs) -> StreamOptions:
    defaults = dict(
        router_url='http://router-a:8085', token='tok', menus=('rh',)
    )
    defaults.update(kwargs)
    return StreamOptions(**defaults)


@pytest.mark.unit
class TestConnectUrl:
    @pytest.mark.parametrize('url', SAME_HOST_FORMS)
    def test_same_host_forms_resolve_to_same_url(self, url):
        assert connect_url(url) == 'ws://router-a:8085/v1/menus/connect'

    @pytest.mark.parametrize(
        ('url', 'expected'),
        [
            (
                'https://voll-hml.verdecard.cloud/v1/actions',
                'wss://voll-hml.verdecard.cloud/v1/menus/connect',
            ),
            ('https://h/api/v1/actions/', 'wss://h/api/v1/menus/connect'),
            ('https://h/v1?x=1#frag', 'wss://h/v1/menus/connect'),
        ],
    )
    def test_https_and_prefix(self, url, expected):
        assert connect_url(url) == expected

    @pytest.mark.parametrize('url', ['ftp://x', 'router:8085', 'http://'])
    def test_invalid_url_raises_config_error(self, url):
        with pytest.raises(StreamConfigError, match='ROUTER_URL inválida'):
            connect_url(url)


@pytest.mark.unit
class TestNormalizeMenus:
    def test_strips_blanks_and_duplicates_keeping_order(self):
        assert normalize_menus([' rh', 'geral', 'rh', '']) == ('rh', 'geral')


@pytest.mark.unit
class TestNormalizeOptions:
    def test_defaults(self):
        opts = normalize_options(make_options())

        assert opts.queue_size == 100
        assert opts.drain_timeout == 15.0
        assert opts.username == 'chatgraph'

    @pytest.mark.parametrize(
        ('field', 'value', 'expected'),
        [
            ('queue_size', 0, 100),
            ('queue_size', -3, 100),
            ('queue_size', 7, 7),
            ('drain_timeout', 0, 15.0),
            ('drain_timeout', -1.0, 15.0),
            ('drain_timeout', 2.5, 2.5),
            ('username', '   ', 'chatgraph'),
            ('username', 'bot', 'bot'),
        ],
    )
    def test_values_are_defaulted_or_kept(self, field, value, expected):
        opts = normalize_options(make_options(**{field: value}))

        assert getattr(opts, field) == expected

    def test_menus_are_normalized(self):
        opts = normalize_options(make_options(menus=(' rh ', 'rh', 'geral')))

        assert opts.menus == ('rh', 'geral')

    @pytest.mark.parametrize(
        ('kwargs', 'message'),
        [
            ({'token': '  '}, 'ROUTER_TOKEN vazio'),
            ({'menus': (' ', '')}, r'nenhum menu declarado \(ROUTER_MENUS\)'),
            ({'router_url': 'router:8085'}, 'ROUTER_URL inválida'),
        ],
    )
    def test_invalid_options_raise_config_error(self, kwargs, message):
        with pytest.raises(StreamConfigError, match=message) as exc_info:
            normalize_options(make_options(**kwargs))

        assert isinstance(exc_info.value, ValueError)
