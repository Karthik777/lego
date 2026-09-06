# Bricks

A block's UI is components. `bricks` is where a document outside the app gets at them.

A brick is one component with three declarations: the ports it draws from, the values it hands back
when somebody uses it, and the code that fills those ports from the block that owns it.

```python
brick('panchanga.horas', 'Hora ribbon', 'panchanga',
      doc='The twenty-four planetary hours as a ribbon. Click one to select it.',
      ports=[Port('horas', 'list', 'day["horas"]', sample=[...])],
      emits=[Port('hora', 'dict', 'The hora clicked')],
      height=150,
      wire='...')
```

`lego/bricks/bricks.py` holds the declarations. `lego/bricks/bricks.js` holds the drawing, keyed by
the same name. `tests/test_bricks.py` asserts the two sets are equal, so a brick declared without a
renderer fails at test time rather than as a blank frame.

## Routes

| route | serves |
|---|---|
| `/bricks` | the gallery, every brick drawn with its sample data |
| `/bricks/manifest.json` | every brick, its ports, its emits, its height |
| `/bricks/f/<name>` | one brick as a whole HTML document, for an iframe |
| `/bricks/data/<name>` | that brick's ports, filled by running its wiring here |
| `/bricks/wire/<name>` | the wiring, twice: as an import and as a call to this host |
| `/bricks/js`, `/bricks/css` | the frame's client |

The asset routes carry no file extension because fasthtml's static route claims any path that has
one.

## The frame protocol

A frame is an iframe and four messages. It knows nothing about the document it is in.

| message | direction | meaning |
|---|---|---|
| `brick:ready` | frame to host | loaded, with its manifest |
| `brick:props` | host to frame | resolved port values |
| `brick:height` | frame to host | how tall it wants to be |
| `brick:emit` | frame to host | a value the person produced by using it |

`brick:emit` is the half that makes a component an input. Clicking a rasi, a cost row or a funnel
bar posts a value out. What the host does with it is the host's business.

A frame ignores `brick:props` while `root.dataset.busy` is set, so a value coming back mid-drag does
not restart the drag.

## Wiring, twice

`wire` imports the block:

```python
from datetime import date
from lego.muhurtha.panchanga import Place, day_panchanga
place = Place(12.97, 77.59, 'Asia/Kolkata', 'Bengaluru')
day = day_panchanga(place, date.today(), planets=True, spans=False)
```

`remote` calls this host instead:

```python
import json, urllib.request
_ports = json.load(urllib.request.urlopen('http://127.0.0.1:5001/bricks/data/panchanga.day'))
day = _ports['day']
```

The second is generated from the first. `/bricks/data/<name>` runs `wire` here and returns the port
values as JSON. A document runs the import form and falls back to the call form when the import
fails, which is what happens when lego is not installed beside it.

A wiring snippet that raises does not fail the route. The ports come back filled with the samples
each port declares, and `_error` says what went wrong.

## The ten

| brick | group | draws from | hands back |
|---|---|---|---|
| `panchanga.day` | panchanga | `day` | `limb` |
| `panchanga.horas` | panchanga | `horas` | `hora` |
| `panchanga.wheel` | panchanga | `planets`, `highlight` | `rasi` |
| `thrifty.costs` | thrifty | `rows` | `row` |
| `viz.tiles` | viz | `tiles` | `tile` |
| `viz.series` | viz | `labels`, `series` | `point` |
| `viz.funnel` | viz | `stages` | `stages`, `stage` |
| `learn.cell` | learn | `label` | `organelle` |
| `learn.wavepacket` | learn | `barrier`, `width`, `k0` | `transmission` |
| `learn.orbit` | learn | `mass_ratio`, `eccentricity` | `period` |

`learn.wavepacket` integrates the one-dimensional Schrödinger equation with a staggered leapfrog,
forty steps a screen refresh, with absorbing edges so a wall reflection is not mistaken for physics.
At the default barrier of 1.02 times the packet energy over six cells it transmits about 15%.
`learn.orbit` is velocity Verlet on two bodies.

## Who consumes this

Leela's canvas, on `claude/dynamic-document-canvas-ohgfud`. A canvas embeds a brick, picks its
wiring off `/bricks/wire/<name>`, keeps that code in the document as an ordinary cell, and binds the
ports it filled. Set `BRICK_HOST` to point a canvas at a lego app.
