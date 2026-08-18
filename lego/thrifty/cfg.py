import os
from dataclasses import dataclass
from fastcore.all import AttrDict

@dataclass(frozen=True)
class Routes:
    index = '/thrifty'
    skip = ['/thrifty']

# thrifty is the whole of thrifty.sankalpa.sh and one page of lego.sankalpa.sh. `domain` is
# only used for the canonical and og: URLs, so it names the host the page belongs to.
#
# `or`, not a getenv default: the key reaches the container from a GitHub variable that is
# the empty string when unset, which a default would happily accept.
cfg = AttrDict(
    domain      = os.getenv('THRIFTY_DOMAIN') or 'thrifty.sankalpa.sh',
    title       = os.getenv('THRIFTY_TITLE') or 'Thrifty',
    subtitle    = 'AI Platform TCO Calculator',
    tagline     = 'Total cost of ownership for LLM and agent platforms, priced from live model rates.',
    theme_color = '#2563eb',
    repo        = 'Karthik777/thrifty',
)
