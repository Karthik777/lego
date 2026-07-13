from datetime import datetime
from time import time
from lego.core import database, quick_lgr, slug
from .cfg import *

__all__ = ['get_db', 'hist', 'shared', 'get_projects', 'new_chat', 'get_chat', 'latest_chat', 'get_msgs', 'add_msg', 'msgs_as_bubbles']

info,err,warn=quick_lgr()

def all_dcs(db):
    for t in db.t:
        if '_fts' not in t.name: t.dataclass()   # skip FTS shadow tables

def get_db():
    _db = database(cfg.db)
    chats, msgs, docs, ckpts, proj = _db.t.chats, _db.t.chat_messages, _db.t.documents, _db.t.chat_checkpoints, _db.t.projects
    proj.create(id=int, name=str, description=str, created_at=float, pk='id', if_not_exists=True,
        transform=True, user_id=int, not_null={'name'},defaults=dict(created_at=time()))
    proj.create_index(['name'], if_not_exists=True)

    chats.create(id=str, user_id=int, name=str, shared_with=str, created_at=float, updated_at=float, project_id=int,
         pk='id', foreign_keys=[('project_id', 'projects', 'id')], if_not_exists=True, transform=True,
         not_null={'user_id', 'name'}, defaults=dict(created_at=time(), updated_at=time(), name='New Chat', shared_with='[]'))

    chats.create_index(['user_id'], if_not_exists=True)
    chats.create_index(['updated_at'], if_not_exists=True)
    chats.create_index(['project_id'], if_not_exists=True)

    # TODO: enable sqlite extension spellfix for FTS
    if not chats.detect_fts(): chats.enable_fts(['name'], create_triggers=True)

    msgs.create(id=int, sender=str, message=str, document_ids=str, created_at=float, chat_id=str,
        foreign_keys=[('chat_id', 'chats', 'id')], pk='id', if_not_exists=True, transform=True,
        not_null={'chat_id', 'sender', 'message'}, defaults=dict(created_at=time()))
    msgs.create_index(['chat_id'], if_not_exists=True)

    docs.create(id=str, user_id=int, name=str, mime_type=str, storage_url=str, created_at=float, pk='id', chat_id=str,
        project_id=int, if_not_exists=True, defaults=dict(created_at=time()),transform=True, not_null={'id', 'user_id', 'name', 'storage_url'},
        foreign_keys=[('chat_id', 'chats', 'id'),('project_id', 'projects', 'id')])
    docs.create_index(['user_id'], if_not_exists=True)
    docs.create_index(['project_id'], if_not_exists=True)
    docs.create_index(['chat_id'], if_not_exists=True)

    ckpts.create(id=int, user_id=int, name=str, last_msg_id=int, created_at=float, chat_id=str, pk='id',
        if_not_exists=True, foreign_keys=[('chat_id', 'chats', 'id')], transform=True,
        not_null={'chat_id', 'user_id', 'name', 'last_msg_id'}, defaults=dict(created_at=time()))
    ckpts.create_index(['user_id'], if_not_exists=True)
    ckpts.create_index(['chat_id'], if_not_exists=True)

    all_dcs(_db)
    return _db

db = get_db()


def _limit(pg=1, sz=5): return f'{(pg - 1) * sz},{sz}'
def hist(uid=None, pg=1, sz=10):
    '''Get chats for a user'''
    sz_ = (db.t.chats.name, uid, _limit(pg, sz))
    ch_sql = 'select updated_at, name, id from %s where user_id = %s order by updated_at desc limit %s' % sz_
    sql = f'''
    select case 
        when date(c.updated_at, 'unixepoch') = date('now', 'localtime') then 'Today'
        else strftime('%m-%Y', datetime(c.updated_at, 'unixepoch'))
    end as bin,
    group_concat(c.name, '||') as titles_concat,
    group_concat(c.id, '||') as chat_ids
    from ({ch_sql}) c
    group by bin
    order by max(c.updated_at) desc
    '''
    fmt_bin = lambda x: 'Today' if x == 'Today' else datetime.strptime(x, '%m-%Y').strftime('%b %Y')
    return L(db.q(sql)).map(lambda r: (fmt_bin(r['bin']), list(zip(r['titles_concat'].split('||'), r['chat_ids'].split('||')))))

def shared(uid=None, pg=1, sz=5): return L(db.t.chats(where=f"instr(shared_with, '{uid}') > 0", limit=_limit(pg, sz), order_by='updated_at desc'))
def get_projects(uid=None, pg=1, sz=5): return L(db.t.projects(where=f"user_id={uid}", limit=_limit(pg, sz), order_by='created_at desc'))

def new_chat(uid, name='New Chat'):
    cid = slug(f'{uid}{name}{time()}')
    db.t.chats.insert(dict(id=cid, user_id=uid, name=name, created_at=time(), updated_at=time()))
    return cid

def get_chat(cid, uid):
    r = L(db.t.chats(where='id=? and user_id=?', where_args=[cid, uid]))
    return r[0] if r else None

def latest_chat(uid):
    r = L(db.t.chats(where='user_id=?', where_args=[uid], order_by='updated_at desc', limit=1))
    return r[0] if r else None

def get_msgs(cid):
    return L(db.t.chat_messages(where='chat_id=?', where_args=[cid], order_by='created_at'))

def add_msg(cid, sender, message):
    row = db.t.chat_messages.insert(dict(chat_id=cid, sender=sender, message=message, created_at=time()))
    db.t.chats.update(dict(id=cid, updated_at=time()))
    return row

def _ts(t): return datetime.fromtimestamp(t).strftime('%I:%M %p')
def msgs_as_bubbles(cid):
    return [(r.message, r.sender == 'user', _ts(r.created_at)) for r in get_msgs(cid)]
