from lego.ai import get_db, hist
from lego.core import quick_lgr

info,err,warn=quick_lgr()
db=get_db()

def create_dummy_chat_data():
    from uuid import uuid4
    import ujson as json
    from random import randint, choice
    from time import time, mktime
    from datetime import datetime, timedelta

    chats, msgs, docs, ckpts, proj = db.t.chats, db.t.chat_messages, db.t.documents, db.t.chat_checkpoints, db.t.projects
    uid, shared_uid = 1001, 2002
    ps = [('Grok', 'xAI chatbot'), ('OpenAI', 'ChatGPT chatbot'), ('Gemini', 'Google AI')]
    proj.insert_all([dict(name=n,description=d,created_at=time(),user_id=uid) for n,d in ps], replace=True)
    mk_time = lambda md=0: mktime((datetime.now() - timedelta(days=(30 * md) + randint(0, 25))).timetuple())

    def _(md=0):
        ts, pid = mk_time(md), choice(proj()).id
        doc1, doc2 = str(uuid4()), str(uuid4())
        chat = chats.insert(dict(id=uuid4(), user_id=uid, name=f'Test Chat {uuid4()}', shared_with=json.dumps([shared_uid]),
            project_id=pid, created_at=ts, updated_at=ts + 10), replace=True)

        docs.insert(dict(id=doc1, user_id=uid, chat_id=chat.id, project_id=pid, name="foo.pdf", mime_type="application/pdf",
                         storage_url=f"{uid}/docs/foo.pdf", created_at=ts), replace=True)
        docs.insert(dict(id=doc2, user_id=uid, chat_id=chat.id, project_id=pid, name="bar.txt", mime_type="text/plain",
                         storage_url=f"{uid}/docs/bar.txt", created_at=ts + 1), replace=True)

        msgs.insert(dict(chat_id=chat.id, sender="user", message="Summarise foo.pdf", document_ids=json.dumps([doc1]),
                         created_at=ts + 2), replace=True)
        msgs.insert(dict(chat_id=chat.id, sender="assistant", message="Here's a summary of foo.pdf.", document_ids="",
                         created_at=ts + 3), replace=True)
        msgs.insert(dict(chat_id=chat.id, sender="user", message="Also consider bar.txt", document_ids=json.dumps([doc2]),
                         created_at=ts + 4), replace=True)

        ckpts.insert(dict(chat_id=chat.id, user_id=uid, name="Initial Summary", last_msg_id=2,
                          created_at=ts + 5), replace=True)
    [_(md) for md in range(4) for c in range(3) ]
    return chats()


def test():
    """Run some tests to verify the database and chat functionality"""
    info('Running test for chat database...')
    create_dummy_chat_data()
    print("Chats:", hist(1001))

if __name__ == "__main__": test()