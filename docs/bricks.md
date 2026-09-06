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

## On its way out of lego

`bricks` is going to be its own package, depended on by Leela and by anything else that wants these
components. The split is already made: `app.py` is the only file that names lego, and everything
else lifts unchanged.

| file | what it is |
|---|---|
| `bricks.py` | the declarations: ports, emits, wiring, height |
| `bricks.js` | the drawings, keyed by the same names |
| `frame.js`, `bricks.css` | the frame protocol and the frame's own styles |
| `data.py` | running a wiring snippet here, and generating the remote form of it |
| `ui.py` | the gallery, and one brick as a whole document |
| `serve.py` | every route, taking a `page` for the host's shell |
| `cfg.py` | the paths |
| `app.py` | **the seam.** lego's nav, its skip list, and `base` as the shell |

`tests/test_bricks.py` holds both halves of that: no file outside the seam imports lego, and
`serve.connect` mounts into a fasthtml app that is not this one.

A brick's `wire` names whatever package owns its data, which is a different question. `panchanga.day`
will still name `lego.muhurtha` after the move, because that is where a panchangam comes from.

## Who consumes this

Leela's canvas, on `claude/dynamic-document-canvas-ohgfud`. A canvas embeds a brick, picks its
wiring off `/bricks/wire/<name>`, keeps that code in the document as an ordinary cell, and binds the
ports it filled. Set `BRICK_HOST` to point a canvas at a lego app.
