from dataclasses import dataclass
from fastcore.all import Path, AttrDict

@dataclass(frozen=True)
class Routes:
    base = '/blog'
    index = '/blog'
    new = '/blog/new'
    post = '/blog/{slug}'
    skip = ['/blog', r'/blog/.*']

cfg = AttrDict(posts_seed_force=True, posts_dir=Path(__file__).parent / 'posts', pinned_slug='vedicreader-what-it-does')