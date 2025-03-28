from .data import *
from core import welcome as wlcm

async def login(req): return home(req) if auth_ok(req) else login_form(req, wrap=True)
async def process_login(req, session, lgn: Login): return lgn.__ft__(req, session)
def modal(req, step:Step = Step.login): return login_form(req) if step == Step.login else form(step)
async def forgot_pwd(fgt_pw: ForgotPwdLink): return fgt_pw
async def reset_pwd_link(rst_pw: ResetPwdReq): return rst_pw
async def change_pwd(chng_pwd: ChangePwd): return chng_pwd
async def register(reg: Register): return reg
async def verify_em(ver: VerEmailReq): return ver
async def resend_ver_link(res: ResendVerLink): return res
async def error(req): return home(req) if auth_ok(req) else form(err=OathError)
def before(req, sess): req.scope["auth"] = sess.get('auth', None)
def welcome(req):
    return boss_redirect(req, Routes.login) if not auth_ok(req) else wlcm()


def connect(app, prefix="/a"):
    setup_oath(app)
    app.before.append(before)
    Routes.base = prefix
    app.get("/")(welcome)
    app.get(Routes.login)(login)
    app.post(Routes.login)(process_login)
    app.post(Routes.forgot_pw)(forgot_pwd)
    app.get(Routes.reset_pw)(reset_pwd_link)
    app.post(Routes.process_reset_pw)(change_pwd)
    app.post(Routes.register)(register)
    app.get(Routes.verify_email)(verify_em)
    app.get(Routes.resend_verification)(resend_ver_link)
    app.get(Routes.auth_modal)(modal)
    app.get(Routes.err)(error)