from .data import *
from fasthtml.common import Response
from lego.core import home, RouteOverrides

async def ok(req): return Response(status_code=200) if auth_ok(req) else Response(status_code=401)
async def login(req): return home() if auth_ok(req) else login_form(req, wrap=True)
async def process_login(req, session, lgn: Login): return lgn.__ft__(req, session)
def modal(req, step:Step = Step.login): return login_form(req) if step == Step.login else form(step)
async def forgot_pwd(fgt_pw: ForgotPwdLink): return fgt_pw
async def reset_pwd_link(rst_pw: ResetPwdReq): return rst_pw
async def change_pwd(chng_pwd: ChangePwd): return chng_pwd
async def register(reg: Register): return reg
async def verify_em(ver: VerEmailReq): return ver
async def resend_ver_link(res: ResendVerLink): return res
async def error(req): return home(req) if auth_ok(req) else form(err=OathError)

def connect(app, prefix='/a/'):
    if prefix: Routes.base = prefix
    setup_oath(app)
    Routes.base = prefix
    app.get(Routes.auth_ok)(ok)
    app.get(Routes.login)(login)
    app.post(Routes.login)(process_login)
    app.post(Routes.forgot_pw)(forgot_pwd)
    app.get(Routes.reset_pw)(reset_pwd_link)
    app.post(Routes.reset_pw)(change_pwd)
    app.post(Routes.register)(register)
    app.get(Routes.verify_email)(verify_em)
    app.get(Routes.resend_verification)(resend_ver_link)
    app.get(Routes.auth_modal)(modal)
    app.get(Routes.err)(error)
    RouteOverrides.lgn = Routes.login
    RouteOverrides.lgt = Routes.logout
