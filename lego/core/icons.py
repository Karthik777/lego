from fasthtml.svg import *

def icon_auto(cls='', stroke_width=1, stroke_color='currentColor', w=24, h=24):
    return Svg(Path(stroke='none', d='M0 0h24v24H0z', fill='none'), Circle(cx='12', cy='12', r='9'),
               Path(d='M13 12h5'), Path(d='M13 15h4'), Path(d='M13 18h1'), Path(d='M13 9h4'), Path(d='M13 6h1'),
               viewbox='0 0 24 24', fill='none', stroke=stroke_color, stroke_width=f'{stroke_width}',
               stroke_linecap='round', stroke_linejoin='round', cls=f'icon-tabler-shadow {cls}', w=w, h=h)

def icon_toc(cls='', stroke_width=0, stroke_color='currentColor', w=24, h=24):
    return Svg(Path(d='M408 442h480c4.4 0 8-3.6 8-8v-56c0-4.4-3.6-8-8-8H408c-4.4 0-8 3.6-8 8v56c0 4.4 3.6 8 8 8zm-8 204c0 4.4 3.6 8 8 8h480c4.4 0 8-3.6 8-8v-56c0-4.4-3.6-8-8-8H408c-4.4 0-8 3.6-8 8v56zm504-486H120c-4.4 0-8 3.6-8 8v56c0 4.4 3.6 8 8 8h784c4.4 0 8-3.6 8-8v-56c0-4.4-3.6-8-8-8zm0 632H120c-4.4 0-8 3.6-8 8v56c0 4.4 3.6 8 8 8h784c4.4 0 8-3.6 8-8v-56c0-4.4-3.6-8-8-8zM115.4 518.9L271.7 642c5.8 4.6 14.4.5 14.4-6.9V388.9c0-7.4-8.5-11.5-14.4-6.9L115.4 505.1a8.74 8.74 0 0 0 0 13.8z'),
            stroke=stroke_color,fill=stroke_color,stroke_width=f'{stroke_width}',
               viewbox='0 0 1024 1024', cls=f'icon-tabler-moon {cls}', w=w, h=h)
