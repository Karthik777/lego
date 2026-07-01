from fastcore.all import L
from lego.core.cfg import database, get_db_pth
from lego.church.cfg import cfg

__all__ = ['teachings_db', 'teachings', 'seed_teachings']


def teachings_db(path=None):
    from fastcore.all import ifnone
    path = ifnone(path, get_db_pth('teachings'))
    db = database(path)
    db.t.teachings.create(slug=str, title=str, summary=str, body=str, created_at=float, updated_at=float,
        pk='slug', if_not_exists=True, transform=True, not_null={'title', 'body'})
    db.t.teachings.create_index(['slug'], unique=True, if_not_exists=True)
    return db

_db = teachings_db()
teachings = _db.t.teachings

def _parse_md(path):
    from datetime import datetime
    text = path.read_text()
    try: _, fm, body = text.split('---', 2)
    except ValueError: raise ValueError(f"{path}: expected frontmatter between '---' delimiters")
    meta = {k.strip(): v.strip() for k, v in (line.split(':', 1) for line in fm.strip().splitlines() if ':' in line)}
    if 'date' in meta:
        try: ts = datetime.strptime(meta['date'], '%Y-%m-%d').timestamp()
        except ValueError: ts = path.stat().st_ctime
    else: ts = path.stat().st_ctime
    return dict(slug=meta.get('slug', path.stem),
         title=meta.get('title', path.stem),
         summary=meta.get('summary', ''),
         body=body.strip(),
         created_at=ts,
         updated_at=ts,
         )

_seeds = L(cfg.teachings_dir.glob('*.md')).sorted().map(_parse_md)

def seed_teachings(force=False):
    ex = L(teachings(select='slug')).map(lambda r: r['slug'])
    [teachings.insert(t, replace=True) for t in _seeds if force or t['slug'] not in ex]
