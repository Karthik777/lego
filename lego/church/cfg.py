from dataclasses import dataclass
from fastcore.all import Path, AttrDict

@dataclass(frozen=True)
class Routes:
    home = '/'
    about = '/about'
    teachings = '/teachings'
    teaching = '/teachings/{slug}'
    assembly = '/assembly'
    beliefs = '/beliefs'
    contact = '/contact'
    skip = ['/', '/about', '/teachings', r'/teachings/.*', '/assembly', '/beliefs', '/contact']

_here = Path(__file__).parent
cfg = AttrDict(
    teachings_dir=_here / 'teachings',
    teachings_seed_force=True,
    beliefs_md=(_here / 'content' / 'beliefs.md').read_text(),
)
