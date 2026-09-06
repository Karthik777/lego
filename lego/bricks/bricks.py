"The brick registry: every UI component a lego block offers a document, with its ports and its wiring snippet."

from dataclasses import dataclass, field, asdict
from fastcore.all import L, first

__all__ = ['Port', 'Brick', 'brick', 'BRICKS', 'manifest', 'find', 'GROUPS']

@dataclass
class Port:
    "One named input a brick draws from, or one named value it hands back."
    name: str
    kind: str = 'any'
    doc: str = ''
    sample: object = None
    required: bool = True
    def dict(self): return asdict(self)

@dataclass
class Brick:
    "An embeddable component. `wire` is the code that fills its ports from the package that owns it."
    name: str
    title: str
    group: str
    doc: str = ''
    ports: list = field(default_factory=list)
    emits: list = field(default_factory=list)
    wire: str = ''
    height: int = 260
    def dict(self): return {**asdict(self), 'src': self.src, 'ports': [p.dict() for p in self.ports], 'emits': [p.dict() for p in self.emits]}
    @property
    def src(self): return f'lego.bricks:{self.name}'
    def sample(self): return {p.name: p.sample for p in self.ports}

BRICKS = {}

def brick(name, title, group, ports=(), emits=(), wire='', height=260, doc=''):
    "Register one brick. Declaration only: the drawing is `bricks.js`, keyed by the same name."
    BRICKS[name] = Brick(name=name, title=title, group=group, doc=doc, ports=list(ports),
                         emits=list(emits), wire=wire.strip('\n'), height=height)
    return BRICKS[name]

def find(name): return BRICKS.get(name)
def manifest(): return {'bricks': [b.dict() for b in BRICKS.values()], 'groups': GROUPS}

GROUPS = {'panchanga': 'The traditional day, from lego.muhurtha',
          'thrifty':   'Model and agent cost, from lego.thrifty',
          'viz':       'Plain figures: tiles, series, funnels',
          'learn':     'Explaining a concept rather than reporting on one'}

# === panchanga ===

brick('panchanga.day', 'Panchangam day', 'panchanga',
      doc='The five limbs at sunrise, with the day around them.',
      ports=[Port('day', 'dict', 'One day_panchanga() result',
                  sample={'date': '2026-09-06', 'place_name': 'Bengaluru', 'vara': 'Ravivara',
                          'tithi': {'name': 'Krishna Dashami', 'end': '2026-09-06T14:10:00'},
                          'nakshatra': {'name': 'Ardra', 'end': '2026-09-06T09:20:00'},
                          'yoga': {'name': 'Vyaghata'}, 'karana': {'name': 'Vishti'},
                          'masa': 'Shravana', 'paksha': 'Krishna', 'moon_phase': 'Waning crescent',
                          'sunrise': '2026-09-06T06:08:00', 'sunset': '2026-09-06T18:24:00'})],
      emits=[Port('limb', 'str', 'Which limb was clicked')],
      height=250,
      wire='''
from datetime import date
from lego.muhurtha.panchanga import Place, day_panchanga
place = Place(12.97, 77.59, 'Asia/Kolkata', 'Bengaluru')
day = day_panchanga(place, date.today(), planets=True, spans=False)
''')

brick('panchanga.horas', 'Hora ribbon', 'panchanga',
      doc='The twenty-four planetary hours as a ribbon. Click one to select it.',
      ports=[Port('horas', 'list', 'day["horas"]', sample=[{'name': p, 'planet': p, 'start': f'2026-09-06T{h:02d}:00:00', 'end': f'2026-09-06T{h+1:02d}:00:00'}
                                                           for h, p in enumerate(['Sun', 'Venus', 'Mercury', 'Moon', 'Saturn', 'Jupiter', 'Mars'] * 4)][:24])],
      emits=[Port('hora', 'dict', 'The hora clicked')],
      height=150,
      wire='''\nfrom datetime import date
from lego.muhurtha.panchanga import Place, day_panchanga
place = Place(12.97, 77.59, 'Asia/Kolkata', 'Bengaluru')
day = day_panchanga(place, date.today(), planets=True, spans=False)
horas = day['horas']\n''')

brick('panchanga.wheel', 'Rasi wheel', 'panchanga',
      doc='The twelve rasis with the grahas placed. Click a rasi to select it.',
      ports=[Port('planets', 'list', 'day["planets"]',
                  sample=[{'name': n, 'lon': l, 'glyph': g} for n, l, g in
                          [('Sun', 139.9, '☉'), ('Moon', 66.3, '☾'), ('Mars', 176.2, '♂'), ('Mercury', 152.0, '☿'),
                           ('Jupiter', 96.4, '♃'), ('Venus', 118.7, '♀'), ('Saturn', 349.1, '♄'), ('Rahu', 322.8, '☊'), ('Ketu', 142.8, '☋')]]),
              Port('highlight', 'str', 'A rasi name to ring', required=False, sample=None)],
      emits=[Port('rasi', 'dict', 'The rasi clicked, with what sits in it')],
      height=380,
      wire='''\nfrom datetime import date
from lego.muhurtha.panchanga import Place, day_panchanga
place = Place(12.97, 77.59, 'Asia/Kolkata', 'Bengaluru')
day = day_panchanga(place, date.today(), planets=True, spans=False)
planets = day['planets']\nhighlight = day['moon_rasi']\n''')

# === thrifty ===

brick('thrifty.costs', 'Cost table', 'thrifty',
      doc='Monthly and per-request cost per option, sorted, with the cheapest marked.',
      ports=[Port('rows', 'list', '[{label, monthly, per_request}]',
                  sample=[{'label': 'Opus 5', 'monthly': 4210.0, 'per_request': 0.042},
                          {'label': 'Sonnet 5', 'monthly': 890.0, 'per_request': 0.0089},
                          {'label': 'Haiku 4.5', 'monthly': 148.0, 'per_request': 0.00148}])],
      emits=[Port('row', 'dict', 'The row clicked')],
      height=220,
      wire='''
from lego.thrifty.data import get_all_platforms
options = get_all_platforms()['observability'].values()
rows = [{'label': p.name, 'monthly': p.estimated_monthly_base, 'per_request': p.estimated_per_request}
        for p in options if p.estimated_monthly_base]
''')

# === viz ===

brick('viz.tiles', 'Stat tiles', 'viz',
      doc='A row of numbers that matter, each with its movement.',
      ports=[Port('tiles', 'list', '[{label, value, delta}]',
                  sample=[{'label': 'Pipeline', 'value': '$4.2M', 'delta': 12},
                          {'label': 'Win rate', 'value': '31%', 'delta': -4},
                          {'label': 'Cycle', 'value': '48d', 'delta': -9}])],
      emits=[Port('tile', 'dict', 'The tile clicked')],
      height=130)

brick('viz.series', 'Series', 'viz',
      doc='One or more lines over shared labels.',
      ports=[Port('labels', 'list', 'x axis labels', sample=['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']),
             Port('series', 'list', '[{name, values}]',
                  sample=[{'name': 'won', 'values': [4, 6, 5, 9, 12, 11]}, {'name': 'lost', 'values': [9, 7, 8, 6, 5, 7]}])],
      emits=[Port('point', 'dict', 'The point clicked')],
      height=260)

brick('viz.funnel', 'Funnel', 'viz',
      doc='Stages with a conversion between each. Drag a stage to change it: the document recomputes.',
      ports=[Port('stages', 'list', '[{name, value}]',
                  sample=[{'name': 'Leads', 'value': 1000}, {'name': 'Qualified', 'value': 420},
                          {'name': 'Demo', 'value': 180}, {'name': 'Proposal', 'value': 74}, {'name': 'Won', 'value': 23}])],
      emits=[Port('stages', 'list', 'The stages after a drag'), Port('stage', 'dict', 'The stage clicked')],
      height=330)

# === learn ===

brick('learn.cell', 'Animal cell', 'learn',
      doc='An animal cell. Click an organelle: it emits what was clicked, and the document answers.',
      ports=[Port('label', 'str', 'An organelle to ring', required=False, sample=None)],
      emits=[Port('organelle', 'dict', 'name and function of what was clicked')],
      height=420)

brick('learn.wavepacket', 'Wavepacket', 'learn',
      doc='A gaussian wavepacket meeting a barrier, integrated in the frame. Tunnelling is visible when the barrier is thin.',
      ports=[Port('barrier', 'num', 'Barrier height, in units of the packet energy', sample=1.02),
             Port('width', 'num', 'Barrier width in grid points', sample=6),
             Port('k0', 'num', 'Mean wavenumber', sample=0.7)],
      emits=[Port('transmission', 'num', 'Fraction of probability past the barrier')],
      height=340)

brick('learn.orbit', 'Two-body orbit', 'learn',
      doc='Two masses under gravity, integrated with velocity Verlet.',
      ports=[Port('mass_ratio', 'num', 'm2/m1', sample=0.3), Port('eccentricity', 'num', '0 is a circle', sample=0.5)],
      emits=[Port('period', 'num', 'Orbits completed')],
      height=340)
