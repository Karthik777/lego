import ujson as json
from fasthtml.common import Path, Script, AttrDict, Link, Surreal, Style
from monsterui.core import ThemeRadii, ThemeShadows, ThemeFont
from .utils import loadX
from .cache import cache

__all__ = ['themes']

css, js = Path(__file__).parent / 'css/theme.css', Path(__file__).parent / 'js/theme.js'
@cache(p='theme',ttl=3600*24*7)
def themes(color='slate', radii=ThemeRadii.md, shadows=ThemeShadows.sm, font=ThemeFont.sm):
    d=AttrDict(mode='auto', theme='uk-theme-%s' % color, radii=radii.value, shadows=shadows, font=font)
    j = loadX(js, dict(state=json.dumps(d), theme=d.theme), r'\{\{__(\w+)__\}\}')
    return [
        Link(rel='stylesheet', href='https://cdn.jsdelivr.net/npm/franken-ui@2.0.0/dist/css/core.min.css'),
        Link(rel='stylesheet', href='https://cdn.jsdelivr.net/npm/franken-ui@2.0.0/dist/css/utilities.min.css'),
        Script(src='https://cdn.jsdelivr.net/npm/underscore@1.13.7/underscore-umd-min.js', defer=True),
        Style(loadX(css)),Script(j),Surreal("me('body').remove_class('hidden');"),
        Script(type='module', src='https://cdn.jsdelivr.net/npm/franken-ui@2.0.0/dist/js/core.iife.js'),
        Script(type='module', src='https://cdn.jsdelivr.net/npm/franken-ui@2.0.0/dist/js/icon.iife.js'),
        Script(src='/static/js/NoSleep.min.js', defer=True)
    ]
