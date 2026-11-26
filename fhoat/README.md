# fhoat

[Oat UI](https://oat.ink) for FastHTML. A drop-in for Pico.

```python
from fhoat import *
app, rt = fast_app(oat=True)
```

`from fhoat import *` gives you everything in `fasthtml.common`, plus a `fast_app` that takes `oat` in place of `pico`.

## The `oat` switch

| value | result |
|---|---|
| `True` | Oat with the neutral fhoat look |
| `'blue'` | a preset theme |
| `dict(primary='#8a1f11', radius='lg')` | a custom theme |
| `Theme(...)` | the same thing, typed |
| `False` | plain fasthtml (Pico) |

Other flags:
- `mode='auto'|'light'|'dark'` sets the default mode. The reader's choice overrides it.
- `cdn=True` loads Oat from jsDelivr (pinned to `OAT_VER`) and inlines fhoat's CSS. No route is added.
- `tips=False` hides Oat's tooltips, for an app that draws its own.
- `store='myapp'` names the `localStorage` key for the reader's settings (default `fhoat`).

## Themes

Presets: `default zinc slate stone red rose orange amber yellow green teal blue indigo violet paper ink`.
`paper` and `ink` also change the surfaces. Every preset works in light and in dark.

```python
Theme(name='paper', primary=('#8a1f11', '#dcae6d'), radius='md', shadow='sm', font='serif', scale=1.05, tokens=dict(container_max='64rem'))
```

- `primary`: one `#hex`, or a `(light, dark)` pair. The text colour on it is derived from it.
- `radius`: `none sm md lg full`. `shadow`: `none sm md lg`. `size` (text): `sm lg xl`. These three are the app's defaults; a reader's choice replaces them.
- `font`/`display`: `sans serif mono`, or a font stack.
- `tokens`: any Oat CSS variable (`container_max` → `--container-max`).

Custom values are unlayered `:root` rules. They override presets and Oat. Your own unlayered CSS overrides them.

In the browser:
- `fhoat.set('radius', 'lg')`, `fhoat.set('radius')` (back to the app default). The keys are `mode theme radius shadow size`.
- `fhoat.mode('dark')`, `fhoat.theme('teal')`, `fhoat.cycle('size', ['', 'lg', 'xl'])`, `fhoat.get('theme')`.
- The browser keeps these in `localStorage` and applies them before first paint. A change fades in and fires a `fhoat` event on `<html>`.
- `<html>` carries `data-mode data-theme data-radius data-shadow data-size` and the classes `dark`/`light`, plus `auto` in auto mode.

## Components

These have the same names as `fasthtml.pico`: `Card Group Search Grid DialogX Container OatBusy`.

| Oat | |
|---|---|
| `Btn ABtn` | `variant=secondary\|danger`, `look=outline\|ghost`, `size=small\|large`, `icon=True` |
| `Badge Alert` | `variant=success\|warning\|danger` |
| `Field Switch` | a labelled input with a hint and an error; a toggle |
| `Tabs Dropdown` | `Tabs(('A', a), ('B', b))`, `Dropdown('Menu', A(...), 'item')` |
| `DialogOpen DialogClose` | open and close a `DialogX` by id |
| `Row Col` | Oat's 12-column grid, `Col(span=8)` |
| `Avatar Skeleton` | |
| `Navbar Hero PageFooter` | page chrome |
| `ModeToggle ThemePicker FontToggle` | reader controls; each takes your own `icon`s; `ModeToggle(order=...)`, `ThemePicker(themes, radii, shadows)` |
| `Toast toast_hdr` | a toast in a page or swap; a toast after an htmx request (`HX-Trigger`) |

## Files

| file | what | in `oat_hdrs` |
|---|---|---|
| `oat.min.css`, `oat.min.js` | Oat 1.1.0 | always |
| `oat10.css`, `oat10.js` | Oat 1.0's tokens, metrics and title sweep, for an app drawn on 1.0 | `compat=True` |
| `themes.css` | mode, presets, the reader's settings, the reader controls | `themes=True` (default) |
| `fhoat.css` | the look: type, links, nav, hero, cards, grid, tables | `look=True` (default) |
| `fhoat.js` | mode, settings and toasts (inline, before paint) | `script=True` (default) |

An app with its own look passes `look=False`. An app with its own mode and settings script passes `themes=False, script=False`.
An app that serves files itself mounts `OAT_DIR` and passes its path as `prefix`.

## Without the wrapper

```python
from fasthtml.common import fast_app
from fhoat import oat_hdrs, oat_htmlkw, serve_oat
app, rt = fast_app(pico=False, hdrs=oat_hdrs('blue'), htmlkw=oat_htmlkw('blue'))
serve_oat(app)
```

## Upstream

The module has the same shape as `fasthtml/pico.py`. To add it to FastHTML:
1. Add `fhoat/core.py` as `fasthtml/oat.py`.
2. In `fast_app`, add an `oat` parameter that sets `pico=False`, adds `oat_hdrs` and merges `oat_htmlkw`.

## In use

- lego: `oat_hdrs(look=False, compat=True)`. fhoat runs the mode, theme, corners, shadows and text size, and draws the reader controls. lego keeps its own look.
- vedicreader: `oat_hdrs(look=False, themes=False, script=False, compat=True, prefix='/css/fhoat')`, with `tips=False`. fhoat only supplies Oat; vedicreader keeps its own preferences.

## Demo

`uv run python -m fhoat.demo` starts the demo on port 5002. Pages:
- `/`: every component.
- `/lego`: a blog front, a sign-in dialog and a dashboard.
- `/vr`: a verse reader, a pañcāṅga card and a shelf of works.

Oat 1.1.0 is © Kailash Nadh, MIT (`static/LICENSE-oat`). The icons are from Lucide (ISC).
