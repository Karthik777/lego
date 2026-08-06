import os
from dataclasses import dataclass
from fastcore.all import AttrDict

@dataclass(frozen=True)
class Routes:
    index = '/hora'
    skip = ['/hora']

# hora is the whole of sankalpa.sh and one page of lego.sankalpa.sh. `domain` is only used
# for the canonical and og: URLs, so it names the apex the page belongs to either way.
cfg = AttrDict(
    # `or`, not a getenv default: the key reaches the container from a GitHub variable that
    # is the empty string when unset, which a default would happily accept.
    domain      = os.getenv('HORA_DOMAIN') or 'sankalpa.sh',
    title       = os.getenv('HORA_TITLE') or 'Hora Viewer',
    tagline     = 'Vedic planetary hours computed from local sunrise and sunset.',
    theme_color = '#4f46e5',
)
