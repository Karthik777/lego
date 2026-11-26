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
- `cdn=True` loads Oat from jsDelivr (pinned to `OAT_VER`) and inlines the fhoat layer. No route is added.

## Themes

Presets: `default slate stone rose orange amber green teal blue indigo violet paper ink`.
`paper` and `ink` also change the surfaces. Every preset works in light and in dark.

```python
Theme(name='paper', primary=('#8a1f11', '#dcae6d'), radius='md', shadow='sm', font='serif', scale=1.05, tokens=dict(container_max='64rem'))
```

- `primary`: one `#hex`, or a `(light, dark)` pair. The text colour on it is derived from it.
- `radius`: `none sm md lg full`. `shadow`: `none sm md lg`. `font`/`display`: `sans serif mono`, or a font stack.
- `tokens`: any Oat CSS variable (`container_max` → `--container-max`).

Custom values are unlayered `:root` rules. They override presets and Oat. Your own unlayered CSS overrides them.

In the browser: `fhoat.mode('dark')`, `fhoat.cycle()`, `fhoat.theme('teal')`, `fhoat.theme()` (back to the app default).
The browser keeps these in `localStorage` and applies them before first paint.

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
| `ModeToggle ThemePicker` | reader controls |
| `Toast toast_hdr` | a toast in a page or swap; a toast after an htmx request (`HX-Trigger`) |

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

## Demo

`uv run python -m fhoat.demo` starts the demo on port 5002. Pages:
- `/`: every component.
- `/lego`: a blog front, a sign-in dialog and a dashboard.
- `/vr`: a verse reader, a pañcāṅga card and a shelf of works.

Oat 1.1.0 is © Kailash Nadh, MIT (`static/LICENSE-oat`). The icons are from Lucide (ISC).
