import logging
import secrets
from starlette.responses import PlainTextResponse
from fastcore.all import Config
from fasthtml.common import RedirectResponse, Path, Database, threaded, FT, to_xml

__all__ = ['cfg', 'database', 'AppErr', 'boss_redirect', 'home', 'send_email']

d = dict(app_nm="Lego", app_id="lego", app_sh="LG",
         site_description="Build modern performant webapps one block at a time",
         site_keywords="lego, fastHTML, MonsterUI, webapp, python", site_author="Karthik Rajgopal",
         jwt_scrt=secrets.token_urlsafe(32), tkn_exp=691200, mode="production",
         typwrtr_dyn_txt="Build, Expand, Innovate", typwrtr_stat_txt="like lego",
         domain="http://localhost:5001", db="db/app.db", resend_api_key="",
         static="/static", svg="/static/svg", config_file=".env.override")

cfg = Config(Path(__file__).parent, d['config_file'], create=d, types=dict(tkn_exp=int), defaults=d)


# TODO: support Postgres using fastsql
def database(path=cfg.db, wal=True) -> Database:
    path = Path(path)
    path.parent.mkdir(exist_ok=True)
    tracer = lambda sql, params: print("SQL: {} - params: {}".format(sql, params))
    db = Database(path, tracer=tracer if cfg.mode == "dev" else None)
    if wal: db.enable_wal()
    return db


class AppErr(Exception):
    def __init__(self, msg=None, fields=None):
        super().__init__(msg)
        self.msg, self.fields = msg, fields or []


def boss_redirect(request=None, route="/", status_code=303):
    response = RedirectResponse(route, status_code)
    if request and request.headers.get("hx-request") == "true":
        new_response = PlainTextResponse("", status_code=200)
        new_response.headers["HX-Redirect"] = response.headers["location"]
        return new_response
    return response

@threaded
def send_email(to, subject, html: FT, from_email=None):
    # you will need to set this domain in resend.com
    if not from_email: from_email = f"accounts@{cfg.app_nm.lower()}.com"
    if isinstance(html, FT): html = to_xml(html)
    import resend
    if not cfg.resend_api_key: return
    resend.api_key = cfg.resend_api_key
    try: r = resend.Emails.send({"from": from_email, "to": to, "subject": subject, "html": html})
    except Exception as e: logging.log(logging.WARN, e)

def home(req=None): return boss_redirect(req)
