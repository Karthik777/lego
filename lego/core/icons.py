from fasthtml.svg import *
from fastlucide.core import SvgSprites

__all__ = ['icon_auto', 'icon_toc', 'lc_icon', 'lc_sprites', 'lc_sprite_nms']

# every lucide icon the app renders (incl. via htmx fragments) must be seeded here
# so the sprite sheet emitted on full page loads contains all symbols
_NMS = ('lock', 'log-out', 'moon', 'sun', 'sun-moon', 'palette', 'notebook', 'case-lower', 'triangle-alert',
        'search', 'circle-help', 'table-2')
_ALIASES = {'warning': 'triangle-alert'}

class _Nms(set):
    '''The seeded names, iterating in a fixed order.

    SvgSprites keeps them in a plain set and emits the sheet in iteration order, so the
    same page came out with its symbols shuffled between one process and the next — which
    makes every full page response a different set of bytes for no reason, and defeats
    anything downstream that would rather serve the one it already has.'''
    def __iter__(self): return iter(sorted(super().__iter__()))

_sprites = SvgSprites('lc-', nms=_NMS)
_sprites.nms = _Nms(_sprites.nms)

def lc_icon(nm, w=16, h=None, cls='', **kw):
    'Lucide icon by name (drop-in for the old UkIcon). Renders a <use> ref into the sprite sheet.'
    nm = _ALIASES.get(nm, nm)
    if nm not in _sprites.icons: nm = 'circle-help'
    _sprites.nms.add(nm)
    return _sprites(nm, sz=(w, h or w), cls=cls, **kw)

def lc_sprites():
    'Hidden <defs> sheet with all seeded symbols. Include once per full page render.'
    return _sprites.__ft__()

def lc_sprite_nms():
    'The seeded names, in the order the sheet emits them.'
    return tuple(_sprites.nms)

def icon_auto(cls='', stroke_width=1, stroke_color='currentColor', w=24, h=24):
    return Svg(Path(stroke='none', d='M0 0h24v24H0z', fill='none'), Circle(cx='12', cy='12', r='9'),
               Path(d='M13 12h5'), Path(d='M13 15h4'), Path(d='M13 18h1'), Path(d='M13 9h4'), Path(d='M13 6h1'),
               viewbox='0 0 24 24', fill='none', stroke=stroke_color, stroke_width=f'{stroke_width}',
               stroke_linecap='round', stroke_linejoin='round', cls=f'icon-tabler-shadow {cls}', w=w, h=h)

def icon_toc(cls='', stroke_width=0, stroke_color='currentColor', w=24, h=24):
    return Svg(Path(d='M408 442h480c4.4 0 8-3.6 8-8v-56c0-4.4-3.6-8-8-8H408c-4.4 0-8 3.6-8 8v56c0 4.4 3.6 8 8 8zm-8 204c0 4.4 3.6 8 8 8h480c4.4 0 8-3.6 8-8v-56c0-4.4-3.6-8-8-8H408c-4.4 0-8 3.6-8 8v56zm504-486H120c-4.4 0-8 3.6-8 8v56c0 4.4 3.6 8 8 8h784c4.4 0 8-3.6 8-8v-56c0-4.4-3.6-8-8-8zm0 632H120c-4.4 0-8 3.6-8 8v56c0 4.4 3.6 8 8 8h784c4.4 0 8-3.6 8-8v-56c0-4.4-3.6-8-8-8zM115.4 518.9L271.7 642c5.8 4.6 14.4.5 14.4-6.9V388.9c0-7.4-8.5-11.5-14.4-6.9L115.4 505.1a8.74 8.74 0 0 0 0 13.8z'),
            stroke=stroke_color,fill=stroke_color,stroke_width=f'{stroke_width}',
               viewbox='0 0 1024 1024', cls=f'icon-tabler-moon {cls}', w=w, h=h)
