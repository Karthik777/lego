# fhoat

> Oat UI for FastHTML: a drop-in for Pico. `fast_app(oat=True)`.

[Oat](https://oat.ink) is a small semantic UI library: plain tags look finished, a few classes and attributes pick variants, and a handful of
web components (tabs, dropdowns, upload, tag input) need no framework. fhoat puts Oat 1.1.0 in a FastHTML app the way `pico=True` puts
Pico there, and adds themes, light and dark modes, the reader's own settings and FastHTML functions for each component.

## Install

```sh
pip install fhoat
```

## Start

```python
from fhoat import *        # everything in fasthtml.common, plus fhoat

app, rt = fast_app(oat=True)

@rt
def index():
    return (Navbar('My app', ('Docs', '/docs'), end=(ThemePicker(), ModeToggle())),
            Container(Grid(Card(P('Plain tags are styled.'), header=H3('One')),
                           Card(P('Classes pick variants.'), header=H3('Two'), footer=Btn('Go')))))

serve()
```

`oat` takes `True`, a preset name (`'blue'`), a dict (`dict(primary='#8a1f11', radius='lg')`) or a `Theme`. `oat=False` gives plain
FastHTML with Pico. The files come from your own app at `/fhoat/`, hashed and cached for a year; nothing loads from a CDN unless you pass
`oat_kw=dict(cdn=True)`.

## What styles itself

`Button`, `A`, `Input`, `Select`, `Textarea`, `Label`, `Fieldset`, `Table`, `Dialog`, `Details`, `Progress`, `Meter` and the headings
need nothing. `A(..., cls='button')` is a link drawn as a button. A `Div` has no look of its own: give it `cls='card'`, `'row'`,
`'hstack'`, `'vstack'` or `'container'`, or use the functions below. With the restyle on (the default), fhoat also sets the type,
links, code, tables and focus rings.

## Examples

A form that posts with htmx, shows a server error on the field and a toast on success:

```python
@rt
def signup(): return Form(Field('Email', Input(name='email', type='email'), hint='We never share it.'), Btn('Join'), hx_post=join, hx_swap='outerHTML')

@rt
def join(email: str):
    if '@' not in email: return Form(Field('Email', Input(name='email', value=email), error='That is not an email.', invalid=True), Btn('Join'), hx_post=join, hx_swap='outerHTML')
    return P('Thanks.'), toast_hdr('You are in.', 'Welcome', 'success')
```

A dialog that opens from a button and closes itself:

```python
DialogOpen('Delete', id='del'), DialogX(P('This cannot be undone.'), header=H3('Delete project?'),
                                        footer=(DialogClose('Cancel'), Btn('Delete', variant='danger', hx_delete='/p/1')), id='del')
```

Tabs, a menu, a spinner while htmx works:

```python
Tabs(('Account', P('…')), ('Billing', P('…')), anchor='tab')
Dropdown('Options', A('Profile', href='/me'), Hr(), Btn('Sign out', hx_post='/out'))
OatBusy()   # in the page: every htmx request marks its element aria-busy, which Oat draws as a spinner
```

An app shell with a sidebar:

```python
Sidebar(Ul(Li(A('Home', href='/', aria_current='page')), Li(A('Users', href='/u'))), Container(H1('Home')), topnav=(SidebarToggle(), Strong('My app')))
```

## Themes and the reader's settings

Presets: `default zinc slate stone red rose orange amber yellow green teal blue indigo violet paper ink`; `paper` and `ink` also change
the surfaces. Each works in light and in dark.

```python
fast_app(oat=Theme(name='paper', primary=('#8a1f11', '#dcae6d'), radius='md', shadow='sm', size='lg', font='serif', tokens=dict(container_max='64rem')))
```

`radius`, `shadow` and `size` are the app's defaults: the reader changes them with `ThemePicker` and `FontToggle`, and `ModeToggle` moves
between auto, light and dark. The browser keeps the choice in `localStorage` and applies it before first paint. From your own script:
`fhoat.set('radius', 'lg')`, `fhoat.mode('dark')`, `fhoat.theme('teal')`, `fhoat.cycle('size', ['', 'lg', 'xl'])`. A change fires a
`fhoat` event on `<html>`, which carries `data-mode data-theme data-radius data-shadow data-size` and the class `dark` or `light`.

Your own CSS wins without `!important`: fhoat's rules sit in Oat's layers, and the theme's tokens in one unlayered `:root` rule.

## Layers

`oat_kw` (or `oat_hdrs` directly) picks the layers:

| flag | default | adds |
|---|---|---|
| `presets` | on | mode, presets, the reader's settings (`themes.css`) |
| `components` | on | what fhoat's components need: card parts, grid, navbar, hero, footer, controls (`components.css`) |
| `restyle` | on | type, links, code, tables, focus (`fhoat.css`) |
| `script` | on | mode, settings, controls and toasts (`fhoat.js`, inline) |
| `compat` | off | Oat 1.0's tokens, metrics and title sweep, for an app drawn on 1.0 |
| `cdn` | off | Oat from jsDelivr, with SRI |
| `prefix` | `/fhoat` | where the files are served |

`fast_app` also takes `mode`, `tips=False` (hide Oat's tooltips for an app that draws its own) and `store` (the `localStorage` key).

## An existing app

`setup_oat` does what `fast_app(oat=...)` does, on an app you already have, including one built with `FastHTML(...)`:

```python
app = FastHTML()
setup_oat(app, 'teal', restyle=False)
setup_oat_toasts(app)   # FastHTML's add_toast(sess, msg, typ) now shows Oat toasts
```

An app that serves its own files mounts `OAT_DIR` and passes its path as `prefix`; an app that builds its own head calls `oat_hdrs` and
`oat_htmlkw`:

```python
app.router.routes.insert(0, Mount('/css/fhoat', StaticImmutable(directory=OAT_DIR)))
hdrs = oat_hdrs(restyle=False, presets=False, script=False, compat=True, prefix='/css/fhoat')
```

```python
app, rt = fast_app(oat='blue')
assert app.htmlkw['data_theme'] == 'blue'
```

## Components

| | |
|---|---|
| Pico's names | `Card Group Search Grid DialogX Container OatBusy` |
| Layout | `Row Column Sidebar SidebarToggle` |
| Buttons | `Btn ABtn ButtonGroup DialogOpen DialogClose tip` |
| Content | `Badge Alert Avatar AvatarGroup Skeleton Spinner` |
| Forms | `Field Switch Upload TagInput` |
| Interactive | `Tabs Dropdown` |
| Page | `Navbar Hero PageFooter` |
| Reader controls | `ModeToggle ThemePicker FontToggle` |
| Toasts | `OatToast toast_hdr setup_oat_toasts` |

`Search` hides FastHTML's `<search>` tag, as in `fasthtml.pico`. FastHTML's `Col` (the `<col>` tag) and `Toast` stay as they are; fhoat's
are `Column` and `OatToast`.

The demo shows each one: `python -m fhoat.demo`, then open http://localhost:5002.

## Develop

fhoat is an [nbdev](https://nbdev.fast.ai) project: the code and its tests are in `nbs/`.

```sh
pip install -e '.[dev]'
nbdev-export      # nbs/ to fhoat/
nbdev-test        # run the notebooks
nbdev-prepare     # both, plus clean
```

Oat 1.1.0 is © Kailash Nadh, MIT (`fhoat/static/LICENSE-oat`). The icons are from Lucide (ISC).
