from fastcore.xml import A, Div, P, Span, Br, Input
from fasthtml.components import Form, Button, H3, H4
from fasthtml.xtend import Script
from .cfg import Routes, AppErr, Step, EmailNotVerified
from lego.core import typewriter, modal, LabelInput, lc_icon, TextT, ButtonT
from lego.core.cfg import cfg as s, RouteOverrides

FORM_CLS = 'vstack align-left'
LINK_CLS = 'link-btn'
ERR_CLS = f'text-danger mt-2 {TextT.italic}'

def err_cls(err, *fields): return [f' text-danger' if err and f in err.fields else '' for f in fields]
def _form(post, kids): return Form(*kids, cls=FORM_CLS, hx_post=post, hx_target='#auth-container', hx_trigger='submit')
def _err_div(err): return Div(*[P(e, cls=ERR_CLS) for e in err.msg.split(', ')], cls=TextT.break_) if err else None

def _back_to_login(txt='Back to Login', home=False):
    kw = dict(href=RouteOverrides.home) if home else dict(hx_target='#auth-container', hx_swap='outerHTML',
        hx_get=f'{Routes.auth_modal}?step={Step.login}', hx_trigger='click')
    return P(A(txt, cls=LINK_CLS, **kw), cls=f'{TextT.center} m-0')

def _go_home(msg):
    o = Script('setTimeout(()=>location.href="%s",1500)' % RouteOverrides.home)
    return Div(P(msg, cls=TextT.center), o, cls='space-y-6')

def EmailPasswordField(email='', err: AppErr=None, email_ph='shiva.subramaniyam@example.com', pwd_ph='Password', new_pwd=False):
    e_lbl_cls, pw_lbl_cls = err_cls(err, 'email', 'password')
    pw_ac = 'new-password' if new_pwd else 'current-password'
    return Div(cls='space-y-4')(
        LabelInput('Email', id='email', type='email', placeholder=email_ph, value=email, cls=TextT.left, lbl_cls=e_lbl_cls, autocomplete='username'),
        LabelInput('Password', id='password', type='password', placeholder=pwd_ph, cls=TextT.left, lbl_cls=pw_lbl_cls, autocomplete=pw_ac))

def PhoneField(ph='Enter your phone number'): return LabelInput('Phone Number', id='phone', type='tel', placeholder=ph, cls=TextT.left)

def OTPField():
    otp = Input(name='PIN', id='pin', type='text', inputmode='numeric', maxlength='6', pattern='[0-9]*',
                autocomplete='one-time-code', placeholder='······', cls='otp-input')
    return Div(otp, cls='space-y-2 flex items-center justify-center')

def SocialLoginButtons(g_redirect=None, git_redirect=None):
    def btn(href, txt, primary=False):
        cls = [ButtonT.sm, ButtonT.primary if primary else ButtonT.default, 'w-full']
        return A(Div(txt, cls='flex items-center justify-center'), href=href, cls=cls)

    if git_redirect or g_redirect:
        return Div(
            Div(Span('Sign in instantly'), Span('•', cls='mx-1'), Span('No password needed'),
                cls='text-xs align-center mb-3'),
            (btn(g_redirect, 'Continue with Google', primary=True), Div(cls='my-2') if g_redirect else None),
            (btn(git_redirect, 'Continue with Github') if git_redirect else None),
            (Span('or login with email', cls=TextT.xs) if git_redirect or g_redirect else None),
            cls='mb-4')

def register_form(name, email, err, *args):
    name_lbl_cls, con_pw_lbl_cls = err_cls(err, 'name', 'confirm_password')
    return _form(Routes.register, (
        LabelInput('Name', id='name', type='text', placeholder='Shiva Subramaniam', value=name,
                   lbl_cls=name_lbl_cls, cls=TextT.left),
        EmailPasswordField(email, err, new_pwd=True),
        LabelInput('Confirm Password', id='confirm_password', type='password', placeholder='Confirm Password',
                   lbl_cls=con_pw_lbl_cls, cls=TextT.left, autocomplete='new-password'),
        _err_div(err),
        P(A('Resend verification email', hx_get=f'{Routes.resend_verification}?email={email}',
            cls=f'{LINK_CLS} mt-1'))
        if err and err.msg == EmailNotVerified.msg else None,
        Button('Sign up', cls=[ButtonT.primary, ButtonT.sm]),
        _back_to_login('Already have an account?'),
        ))

def phone_form():
    return _form(Routes.ver_ph, (
        H3('Verify Phone Number', cls='align-center text-xl font-medium'),
        P('Please enter your phone number to receive a verification code', cls='text-light align-center'),
        PhoneField(),
        P(id='error', cls=ERR_CLS), Button('Send OTP', cls=[ButtonT.primary, ButtonT.sm])))

def otp_form():
    return _form(Routes.ver_otp, (
        H3('Enter OTP', cls='align-center text-xl font-medium'),
        P("We've sent a verification code to your phone number", cls='align-center text-light'),
        OTPField(),
        Button('Verify OTP', cls=ButtonT.sm),
        P(A('Resend OTP', cls=LINK_CLS, hx_post=Routes.resend_verification, hx_target='#auth-container'),
          cls=f'{TextT.center} mt-1')))

def login_form(email, g_redirect, git_redirect, err, next='', *args):
    is_social_on = g_redirect or git_redirect
    return _form(Routes.login, (
        Input(type='hidden', name='next', value=next),
        SocialLoginButtons(g_redirect, git_redirect),
        EmailPasswordField(email, err),
        _err_div(err),
        P(A('Resend verification email', hx_get=f'{Routes.resend_verification}?email={email}', cls=f'{LINK_CLS} mt-1'))
        if err and err.msg == EmailNotVerified.msg else None,
        Button('Login', cls=[ButtonT.secondary if is_social_on else ButtonT.primary, ButtonT.sm]),
        P(A('Forgot password', cls=LINK_CLS, hx_get=f'{Routes.auth_modal}?step=forgot-password',
            hx_target='#auth-container', hx_swap='outerHTML'), cls='align-right m-0'),
        P("Don't have an account? ", A('Sign up', cls=LINK_CLS, hx_get=f'{Routes.auth_modal}?step=register',
                                       hx_target='#auth-container', hx_swap='outerHTML'), cls='mt-1')))

def forgot_password_form(email, err, *args):
    return _form(Routes.forgot_pw, (
        H4('Reset Password', cls='align-center text-xl font-medium mt-6'),
        P(('Enter your email address and', Br(), "we'll send you a link to reset your password"), cls=TextT.center),
        LabelInput('Email', id='email', type='email', placeholder='Enter your email', value=email, cls=TextT.left),
        _err_div(err), Button('Send Reset Link', cls=[ButtonT.primary, ButtonT.sm]),
        _back_to_login()))

def reset_password_form(token, check, *args):
    return _form(Routes.process_reset_pw, (
        H3('Set New Password', cls='align-center text-xl font-medium'),
        P('Please enter your new password', cls='text-light align-center'),
        LabelInput('New Password', id='new_password', type='password', placeholder='Enter new password', cls=TextT.left, autocomplete='new-password'),
        LabelInput('Confirm Password', id='confirm_password', type='password', placeholder='Confirm new password',
                   cls=TextT.left, autocomplete='new-password'),
        Input(id='token', name='token', type='hidden', value=token),
        _err_div(check), Button('Reset Password', cls=[ButtonT.primary, ButtonT.sm]),
        _back_to_login()))

def password_reset_sent_form(email, *args):
    return Form(
        P('If we have that email in our records, password reset instructions will be sent to ', cls=TextT.center),
        Span(email, cls=TextT.bold),
        P('Please check your inbox and follow the instructions to reset your password.'),
        _back_to_login(), cls=FORM_CLS)

def password_reset_success_form(*args): return _go_home('Password reset successfully! Redirecting...')

def email_verify_form(email, *args):
    return Div(
        P(f'Verification email sent to ', cls=TextT.center), Span(email, cls=TextT.bold),
        P('Please check your inbox and click the verification link.', cls='text-light align-center break-words'))

def email_verified_form(*args): return _go_home('Email verified successfully! Redirecting...')

def verify_error_form(email, err, *args):
    return Form(H4('Verification Failed', cls='align-center text-xl font-medium mt-6'),
                P(lc_icon('warning', cls='mr-1'),
                  err.msg if err else 'Invalid verification link', cls='align-center text-danger'),
                P(('The verification link you used is either invalid or has expired.', Br(),
                   'Please request a new verification link to continue.'), cls='align-center text-sm'),
                P(A('Resend verification email', cls=ButtonT.primary,
                    hx_get=f'{Routes.resend_verification}?email={email}' if email else f'{Routes.auth_modal}?step={Step.login}',
                    hx_target='#auth-container'), cls='align-center mt-6'),
                _back_to_login('Go Home?', home=True), cls=FORM_CLS)

def amodal(content, title=s.app_sh):
    ftr = P(s.ftr_txt, cls='text-xs mt-4')
    return modal(H3(title), typewriter(), content, ftr, id='auth-modal', dialog_cls='auth-dialog')

def resend_verify_form(email, err, *args):
    return _form(Routes.resend_verification, (
        H4('Resend Verification Email', cls='align-center text-xl font-medium mt-6'),
        P(('Enter your email address and', Br(), "we'll send you a new verification link"), cls=TextT.center),
        LabelInput('Email', id='email', type='email', placeholder='Enter your email', value=email, cls=TextT.left),
        _err_div(err), Button('Send Verification Link', cls=[ButtonT.primary, ButtonT.sm]),
        _back_to_login()))

def form(step=Step.login,email='',name='',token='',g_redirect=None,git_redirect=None,
         err=None,contained=False,next=''):
    match step:
        case Step.login: f = login_form(email, g_redirect, git_redirect, err, next),
        case Step.reg: f = register_form(name, email, err),
        case Step.ph: f = phone_form(),
        case Step.otp: f = otp_form(),
        case Step.forgot_pw: f = forgot_password_form(email, err),
        case Step.reset_pw: f = reset_password_form(token, err),
        case Step.pw_reset_sent: f = password_reset_sent_form(email),
        case Step.pw_reset_ok: f = password_reset_success_form(),
        case Step.em_ver: f = email_verify_form(email),
        case Step.em_ok: f = email_verified_form(),
        case Step.ver_err: f = verify_error_form(email, err),
        case Step.resend_ver: f = resend_verify_form(email, err)
        case _: f = login_form(email, g_redirect, git_redirect, err)
    cls = 'w-full max-w-sm mx-auto align-center'
    if contained: cls += ' p-6 border rounded-lg backdrop-blur-xl'
    return Div(f, id='auth-container', cls=cls)
