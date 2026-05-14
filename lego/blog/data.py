from fastcore.all import L
from lego.core.cfg import database, get_db_pth
from lego.blog.cfg import posts_dir

__all__ = ['blog_db', 'posts', 'seed_posts']


def blog_db(path=None):
    from fastcore.all import ifnone
    path = ifnone(path, get_db_pth('blog'))
    db = database(path)
    db.t.posts.create(id=int, slug=str, title=str, summary=str, body=str,author_id=int, author_name=str, visibility=str,
        created_at=float, updated_at=float, pk='id', if_not_exists=True, transform=True,
        not_null={'slug', 'title', 'body', 'visibility'}, defaults=dict(visibility='public'))
    db.t.posts.create_index(['slug'], unique=True, if_not_exists=True)
    return db

_db   = blog_db()
posts = _db.t.posts

def _parse_md(path):
    text = path.read_text()
    try: _, fm, body = text.split('---', 2)
    except ValueError: raise ValueError(f"{path}: expected frontmatter between '---' delimiters")
    meta = {k.strip(): v.strip() for k, v in (line.split(':', 1) for line in fm.strip().splitlines() if ':' in line)}
    meta['body'] = body.strip()
    meta['created_at'] = meta['updated_at'] = path.stat().st_ctime
    return dict(slug=meta.get('slug', path.stem),
         title=meta.get('title', path.stem),
         summary=meta.get('summary', ''),
         body=meta['body'],
         author_id=0,
         author_name=meta.get('author_name', 'Karthik'),
         visibility=meta.get('visibility', 'public'),
         created_at=path.stat().st_ctime,
         updated_at=path.stat().st_mtime,
         )

_seeds = L(posts_dir.glob('*.md')).sorted().map(_parse_md)

def seed_posts():
    ex = L(posts(select='slug')).map(lambda r: r['slug'])
    [posts.insert(p) for p in _seeds if p['slug'] not in ex]
