from dataclasses import dataclass
from email_validator import validate_email, EmailNotValidError, EmailSyntaxError, EmailUndeliverableError
from fasthtml.oauth import OAuth
from fastlite import Table, threaded, NotFoundError, ifnone, database
import hashlib, hmac, time, jwt, re
from core import landing, placeholder, send_email, email_template, home
from .ui import *
g_oath = git_oath = None

# Single global database instance with lazy initialization
_db = None
def get_db():
    global _db
    _db = ifnone(_db, init_schema(_db))
    return _db

def setup_oath(app):
    if not cfg.git_cli and not cfg.g_cli: return
    global g_oath, git_oath
    sk, err, lgt, lgn = Routes.skip, Routes.err, Routes.logout, Routes.login
    g_clbk, git_clbk = Routes.google_clbk, Routes.git_clbk
    g_oath = GoogleAuth(app, cfg.g_cli, sk, g_clbk, err, lgt, lgn) if cfg.g_cli and cfg.want_google else None
    git_oath = GithubAuth(app, cfg.git_cli, sk, git_clbk, err, lgt, lgn) if cfg.git_cli and cfg.want_github else None


class Status(StrEnum): pending, active, suspended, deleted = "pending", "active", "suspended", "deleted"
class TokenT(StrEnum): em_verify, pwd_reset, access_tkn = "email_verification", "password_reset", "access_token"

def init_schema(db):
    db = ifnone(db, database(cfg.db))
    users = db.t.users
    confirmation_tokens = db.t.confirmation_tokens

    users.create(id=int, email=str, password_hash=bytes, phone_number=str, status=str, display_name=str,
                 avatar_url=str, auth_provider=str, provider_user_id=str, last_active_at=float, preferences=str,
                 created_at=float, updated_at=float, pk="id", if_not_exists=True, transform=True,
                 not_null={"email", "status", "display_name", "auth_provider"},
                 defaults=dict(status=Status.pending, created_at=time.time(), updated_at=time.time(),
                               last_active_at=time.time(), preferences="{}", auth_provider="local"))

    confirmation_tokens.create(user_id=int, token=str, type=str, validated=bool, created_at=float, transform=True,
                               pk=["user_id", "type"], if_not_exists=True, not_null={"user_id", "token", "type"},
                               defaults={"type": TokenT.em_verify, "created_at": time.time()})

    users.create_index(["email"], unique=True, if_not_exists=True)
    users.create_index(["provider_user_id", "auth_provider"], unique=True, if_not_exists=True)
    return db

db = get_db()
users, confirmation_tokens = db.t.users, db.t.confirmation_tokens
users.dataclass(); confirmation_tokens.dataclass()
hsh_key = hashlib.sha256(cfg.jwt_scrt.encode()).digest()

def hash_pw(pw): return hmac.new(hsh_key, pw.encode(), hashlib.sha256).digest()
def chk_pw(pw, hashed): return hmac.compare_digest(hash_pw(pw), hashed)
@threaded
def log_usr(uid): users.update(dict(id=uid, last_active_at=time.time()))
def usr_by_em(em): usr = users(where="email=:em", where_args=dict(em=em), fetchone=True); log_usr(usr.id); return usr
def usr_by_oa(pr, pr_uid): usr = users(where="auth_provider=:pr and provider_user_id=:uid", where_args=dict(pr=pr, uid=pr_uid), fetchone=True); log_usr(usr.id); return usr
def usr_by_em_or_oa(val): usr = users(where="email=:val or provider_user_id=:val", where_args=dict(val=val), fetchone=True); log_usr(usr.id); return usr

def set_auth(em, req):
    try: u = usr_by_em_or_oa(em)
    except (NotFoundError, StopIteration): return
    d = dict(usr_id=u.id, usr_email=u.email, usr_name=u.display_name, usr_avatar=u.avatar_url)
    req.scope["auth"] = req.scope["session"]["auth"] = d

def auth_ok(req):
    auth = req.scope["auth"]
    if not auth: return False
    if isinstance(auth, str): set_auth(auth, req)
    if not isinstance(auth, dict) or not auth.get("usr_id"): return False
    return True

def get_token(uid, typ=TokenT.em_verify):
    tok = jwt.encode(dict(uid=uid, typ=typ), cfg.jwt_scrt, "HS256")
    return confirmation_tokens.insert(dict(user_id=uid, type=typ, token=tok), replace=True) and tok

def reqd_chk(attrs: dict) -> AppErr | None:
    fields = [nm for nm, v in attrs.items() if not v]
    return AllFieldsRequired(fields) if fields else None

def em_chk(em, full=False) -> AppErr | str:
    try: valid = validate_email(em, check_deliverability=full, globally_deliverable=full); return valid.normalized.lower()
    except (EmailNotValidError, EmailSyntaxError, EmailUndeliverableError): return InvalidEmail

def pw_chk(pwd, conf_pwd) -> AppErr | None:
    if pwd != conf_pwd: return PasswordMismatch
    errs = []
    if len(pwd) < 8: errs.append("Password must be at least 8 characters")
    if not re.search("[a-z]", pwd): errs.append("Password must contain a lowercase letter")
    if not re.search("[A-Z]", pwd): errs.append("Password must contain an uppercase letter")
    if not re.search("[0-9]", pwd): errs.append("Password must contain a number")
    if not re.search("[!@#$%^&*(),.?\":{}|<>]", pwd): errs.append("Password must contain a special character")
    return AppErr(", ".join(errs), ["password", "confirm_password"]) if errs else None

def tok_chk(tok) -> AppErr | Table:
    if not tok: return InvalidToken
    try:
        ct = confirmation_tokens(where="token=?", where_args=[tok], fetchone=True)
        data: dict = jwt.decode(tok, cfg.jwt_scrt, algorithms=["HS256"])
        if not data: return InvalidToken
        uid, typ = data.get("uid"), data.get("typ")
        if not (uid and typ and users[uid]): return InvalidToken
        if not (ct.user_id == uid and ct.type == typ and ct.created_at + int(cfg.tkn_exp) > time.time() and ct.validated != True): return InvalidToken
        confirmation_tokens.update(dict(user_id=uid, type=typ, validated=True))
        return users[uid]
    except (NotFoundError, StopIteration): return InvalidToken
    except Exception: return DefaultError

def login_form(req, email="", err=None, wrap=False):
    global g_oath, git_oath
    g_redirect = git_redirect = None
    if g_oath: g_redirect = g_oath.login_link(req)
    if git_oath: git_redirect = git_oath.login_link(req)
    c = form(git_redirect=git_redirect, g_redirect=g_redirect, email=email, err=err)
    return landing(c) if wrap else c

def send_ver_em(u, ver_link):
    link = A("Verify Your Account", href=ver_link, cls="text-blue-600 underline p-1")
    content = Div(P(f"Hi {u.display_name},", cls="p-1"), P(f"Welcome to {cfg.app_nm}.", cls="p-1"), link)

    sub = f"{cfg.app_nm} - Email Verification"
    send_email(u.email, sub, email_template(content))

def send_pw_ch_em(u, pw_chng_lnk):
    content = Div(P(f"Hi {u.display_name},", cls="p-1"),
               P(A("Click here", href=f"{pw_chng_lnk}") + " to reset your pwd."))
    sub = f"{cfg.app_nm} - Password Change Request"
    send_email(u.email, sub, email_template(content))

@dataclass
class Login:
    email: str = None; password: str = None

    def __ft__(self, req, session):
        err = self.catch()
        if not err: set_auth(self.email, req); return home(req)
        return login_form(req, self.email, err)

    def catch(self):
        err = reqd_chk(vars(self))
        if err: return err
        em_or_err = em_chk(self.email)
        if isinstance(em_or_err, AppErr): return em_or_err
        self.email = em_or_err
        try: u = usr_by_em(self.email)
        except (NotFoundError, StopIteration): return InvalidCreds
        if not chk_pw(self.password, u.password_hash): return InvalidCreds
        if u.status != Status.active: return EmailNotVerified


@dataclass
class Register(Login):
    name: str = None; email: str = None
    password: str = None; confirm_password: str = None

    def __ft__(self):
        err = self.catch()
        return form(Step.em_ver, self.email) if not err else form(Step.reg, self.email, self.name, err=err)

    def catch(self):
        err = reqd_chk(vars(self))
        if err: return err
        em_or_err = em_chk(self.email)
        if isinstance(em_or_err, AppErr): return em_or_err
        self.email = em_or_err
        err = pw_chk(self.password, self.confirm_password)
        if err: return err
        try:
            u = usr_by_em(self.email)
            return EmailNotVerified if u.status == Status.pending else EmailAlreadyRegistered
        except (NotFoundError, StopIteration):
            u = users.insert(dict(email=self.email, password_hash=hash_pw(self.password), display_name=self.name))
            tok = get_token(u.id)
            ver_lnk = f"{cfg.domain}{Routes.verify_email}?token={tok}"
            send_ver_em(u, ver_lnk) if cfg.resend_api_key else print("Resend isn't setup, Verification link:",ver_lnk)


@dataclass
class ForgotPwdLink:
    email: str = None

    def __ft__(self):
        err = self.catch()
        if err and err.msg == AllFieldsRequired().msg: form(Step.forgot_pw, err=err)
        else: return form(Step.pw_reset_sent, self.email)

    def catch(self):
        err = reqd_chk(vars(self))
        if err: return err
        em_or_err = em_chk(self.email)
        if isinstance(em_or_err, AppErr): return em_or_err
        self.email = em_or_err
        try:
            u = usr_by_em(self.email)
            if u.status != Status.active: return EmailNotVerified
            tok = get_token(u.id, TokenT.pwd_reset)
            pw_chng_lnk = f"{cfg.domain}{Routes.reset_pw}?token={tok}"
            send_ver_em(u, pw_chng_lnk) if cfg.resend_api_key else print("Resend isn't setup, Reset Password link:", pw_chng_lnk)
        except (NotFoundError, StopIteration): return EmailNotFound


@dataclass
class ResetPwdReq:
    token: str = None

    def __ft__(self):
        if isinstance(self.catch(), AppErr):
            return landing(placeholder("This link is invalid. Please hit forgot password again."))
        return form(Step.reset_pw, token=self.token)

    def catch(self): return tok_chk(self.token)


@dataclass
class ResendVerLink:
    email: str = None

    def __ft__(self):
        self.catch()
        return form(Step.em_ver, self.email)

    @threaded
    def catch(self):
        err = reqd_chk(vars(self))
        if err: return err
        em_or_err = em_chk(self.email)
        if isinstance(em_or_err, AppErr): return em_or_err
        self.email = em_or_err
        try:
            u = usr_by_em(self.email)
            if u.status == Status.active: return EmailAlreadyVerified
            tok = get_token(u.id)
            ver_lnk = f"{cfg.domain}{Routes.verify_email}?token={tok}"
            send_ver_em(u, ver_lnk) if cfg.resend_api_key else print(f"Resend isn't setup, Verification link:", ver_lnk)
        except (NotFoundError, StopIteration): return EmailNotFound


@dataclass
class VerEmailReq:
    token: str = None

    def __ft__(self):
        err = self.catch()
        return landing(form(Step.ver_err, err=err)) if err else landing(form(Step.em_ok))

    def catch(self):
        u_or_err = tok_chk(self.token)
        if isinstance(u_or_err, AppErr): return u_or_err
        try: users.update(dict(id=u_or_err.id, status=Status.active, updated_at=time.time()))
        except: return DefaultError


@dataclass
class ChangePwd:
    token: str = None
    new_password: str = None
    confirm_password: str = None

    def __ft__(self):
        err = self.catch()
        return form(Step.reset_pw, err=err) if err else form(Step.pw_reset_ok)

    def catch(self):
        u_or_err = tok_chk(self.token)
        if isinstance(u_or_err, AppErr): return u_or_err
        err = reqd_chk(vars(self)) or pw_chk(self.new_password, self.confirm_password)
        if err: return err
        try: users.update(dict(id=u_or_err.id, password_hash=hash_pw(self.new_password), updated_at=time.time()))
        except: return DefaultError


class GoogleAuth(OAuth):
    def get_auth(self, info, ident, session, state):
        pr = "google"
        try: usr_by_oa(pr, ident)
        except (NotFoundError, StopIteration):
            users.insert(dict(email=info.email, display_name=info.name, avatar_url=info.avatar,
                              auth_provider=pr, provider_user_id=ident, status=Status.active))
        except: return err_page
        finally: return home()


class GithubAuth(OAuth):
    def get_auth(self, info, ident, session, state):
        pr = "github"
        try: usr_by_oa(pr, ident)
        except (NotFoundError, StopIteration):
            em, dn, av = info.email or info.login, info.name or info.login, info.avatar
            users.insert(dict(email=em, display_name=dn, avatar_url=av, auth_provider=pr,
                              provider_user_id=ident, status=Status.active))
        except: return err_page
        finally: return home()


