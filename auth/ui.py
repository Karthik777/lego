from fasthtml.common import A, Div, P, Span, Br
from fasthtml.components import Uk_input_pin
from monsterui.franken import H3, Button, Form, LabelInput, H4, UkIcon, TextT, ButtonT
from .cfg import *

FORM_CLS = "uk-form-stacked space-y-6 uk-form-sm"
LINK_CLS = "uk-btn-text"
ERR_CLS = f"text-danger mt-2 {TextT.italic}"


def err_cls(err, *fields): return [f" text-danger" if err and f in err.fields else "" for f in fields]
def _form(post, kids): return Form(*kids, cls=FORM_CLS, hx_post=post, hx_target="#auth-container", hx_trigger="submit")


def _err_div(err):
    if err: return Div(cls=TextT.break_)(
        *[P(e, cls=f"text-danger {TextT.italic}") for e in err.msg.split(", ")])


def _back_to_login(txt="Back to Login"):
    return P(
        A(txt, cls=LINK_CLS, hx_get=f"{Routes.auth_modal}?step={Step.login}", hx_target="#auth-container", hx_swap="outerHTML", hx_trigger="click"),
        cls=f"{TextT.center} uk-margin-remove")


def EmailPasswordField(email="", err: AppErr=None, email_ph="shiva.subramaniyam@example.com", pwd_ph="Password"):
    e_lbl_cls, pw_lbl_cls = err_cls(err, "email", "password")

    return Div(cls="space-y-4")(
        LabelInput("Email", id="email", type="email", placeholder=email_ph, value=email, cls=TextT.left, lbl_cls=e_lbl_cls),
        LabelInput("Password", id="password", type="password", placeholder=pwd_ph, cls=TextT.left, lbl_cls=pw_lbl_cls))


def PhoneField(ph="Enter your phone number"): return LabelInput("Phone Number", id="phone", type="tel", placeholder=ph, cls=TextT.left)
def OTPField(): return Div(Uk_input_pin(name="PIN", separated=True, uk_cloak=True), cls="space-y-2 flex items-center justify-center")


def SocialLoginButtons(g_redirect=None, git_redirect=None):
    def btn(href, txt, primary=False):
        cls = ['uk-btn', ButtonT.sm, ButtonT.primary if primary else ButtonT.default, 'w-full']
        return A(Div(txt, cls="flex items-center justify-center"), href=href, cls=cls)

    if git_redirect or g_redirect:
        return Div(
            Div(Span("Sign in instantly"), Span("•", cls="mx-1"), Span("No password needed"),
                cls="text-xs text-center mb-3"),
            (btn(g_redirect, "Continue with Google", primary=True), Div(cls="my-2") if g_redirect else None),
            (btn(git_redirect, "Continue with Github") if git_redirect else None),
            (Span("or login with email", cls=TextT.xs) if git_redirect or g_redirect else None),
            cls="mb-4")


def register_form(name, email, err, *args):
    name_lbl_cls, con_pw_lbl_cls = err_cls(err, "name", "confirm_password")
    return _form(Routes.register, (
        LabelInput("Name", id="name", type="text", placeholder="Shiva Subramaniam", value=name, lbl_cls=name_lbl_cls, cls=TextT.left),
        EmailPasswordField(email, err),
        LabelInput("Confirm Password", id="confirm_password", type="password", placeholder="Confirm Password", lbl_cls=con_pw_lbl_cls, cls=TextT.left),
        _err_div(err),
        P(
            A("Resend verification email", hx_get=f"{Routes.resend_verification}?email={email}", cls=f"{LINK_CLS} uk-margin-small-top"))
        if err and err.msg == EmailNotVerified.msg else None,
        Button("Sign up", cls=[ButtonT.primary, ButtonT.sm]),
        _back_to_login("Already have an account?"),
    ))


def phone_form():
    return _form(Routes.ver_ph, (
        H3("Verify Phone Number", cls="uk-text-center text-xl font-semibold"),
        P("Please enter your phone number to receive a verification code", cls="uk-text-muted text-center"),
        PhoneField(),
        P(id="error", cls=ERR_CLS), Button("Send OTP", cls=[ButtonT.primary, ButtonT.sm])))


def otp_form():
    return _form(Routes.ver_otp, (
        H3("Enter OTP", cls="uk-text-center text-xl font-semibold"),
        P("We've sent a verification code to your phone number", cls="uk-text-center uk-text-muted"),
        OTPField(),
        Button("Verify OTP", cls=ButtonT.sm),
        P(A("Resend OTP", cls=LINK_CLS, hx_post=Routes.resend_verification, hx_target="#auth-container"), cls=f"{TextT.center} uk-margin-small-top")))


def login_form(email, g_redirect, git_redirect, err, *args):
    is_social_on = g_redirect or git_redirect
    return _form(Routes.login, (
        SocialLoginButtons(g_redirect, git_redirect),
        EmailPasswordField(email, err),
        _err_div(err),
        P(A("Resend verification email", hx_get=f"{Routes.resend_verification}?email={email}", cls=f"{LINK_CLS} uk-margin-small-top"))
        if err and err.msg == EmailNotVerified.msg else None,
        Button("Login", cls=[ButtonT.secondary if is_social_on else ButtonT.primary,ButtonT.sm]),
        P(A("Forgot password", cls=LINK_CLS, hx_get=f"{Routes.auth_modal}?step=forgot-password", hx_target="#auth-container", hx_swap="outerHTML"), cls="uk-text-right uk-margin-remove"),
        P("Don't have an account? ", A("Sign up", cls=LINK_CLS, hx_get=f"{Routes.auth_modal}?step=register", hx_target="#auth-container", hx_swap="outerHTML"), cls="uk-margin-small-top")))


def forgot_password_form(email, err, *args):
    return _form(Routes.forgot_pw, (
        H4("Reset Password", cls="uk-text-center text-xl font-semibold uk-margin-medium-top"),
        P(("Enter your email address and", Br(), "we'll send you a link to reset your password"), cls=TextT.center),
        LabelInput("Email", id="email", type="email", placeholder="Enter your email", value=email, cls=TextT.left),
        _err_div(err), Button("Send Reset Link", cls=[ButtonT.primary, ButtonT.sm]),
        _back_to_login()))


def reset_password_form(token, check, *args):
    return _form(Routes.process_reset_pw, (
        H3("Set New Password", cls="uk-text-center text-xl font-semibold"),
        P("Please enter your new password", cls="uk-text-muted text-center"),
        LabelInput("New Password", id="new_password", type="password", placeholder="Enter new password", cls=TextT.left),
        LabelInput("Confirm Password", id="confirm_password", type="password", placeholder="Confirm new password", cls=TextT.left),
        LabelInput("Token", id="token", type="hidden", value=token, cls="hidden", lbl_cls="hidden"),
        _err_div(check), Button("Reset Password", cls=[ButtonT.primary, ButtonT.sm]),
        _back_to_login()))


def password_reset_sent_form(email, *args):
    return Form(
        P("If we have that email in our records, password reset instructions will be sent to ", cls=TextT.center), Span(email, cls=TextT.bold),
        P("Please check your inbox and follow the instructions to reset your password."),
        _back_to_login(), cls=FORM_CLS)


def password_reset_success_form(*args):
    return Div(
        P("Password reset successfully! Redirecting to login...", cls=TextT.center),
        cls="space-y-6", hx_get=f"{Routes.auth_modal}?step={Step.login}", hx_trigger="load delay:2s")


def email_verify_form(email, *args):
    return Div(
        P(f"Verification email sent to ", cls=TextT.center), Span(email, cls=TextT.bold),
        P("Please check your inbox and click the verification link.", cls="uk-text-muted text-center uk-wrap"))


def email_verified_form(*args):
    return Div(P("Email verified successfully! Redirecting...", cls=TextT.center), cls="space-y-6",
               hx_get=f"{Routes.auth_modal}?step=login", hx_trigger="load delay:2s",
               hx_target="#auth-container", hx_swap="outerHTML", hx_replace_url="/")


def verify_error_form(email, err, *args):
    return Form(H4("Verification Failed", cls="uk-text-center text-xl font-semibold uk-margin-medium-top"),
                P(UkIcon("warning", cls="uk-margin-small-right"),
                  err.msg if err else "Invalid verification link", cls="uk-text-center text-danger"),
                P(("The verification link you used is either invalid or has expired.", Br(),
                   "Please request a new verification link to continue."), cls="uk-text-center uk-text-small"),
                P(A("Resend verification email", cls="uk-btn-primary",
                    hx_get=f"{Routes.resend_verification}?email={email}" if email else f"{Routes.auth_modal}?step={Step.login}",
                    hx_target="#auth-container"), cls="uk-text-center uk-margin-medium-top"),
                _back_to_login(), cls=FORM_CLS)

def resend_verify_form(email, err, *args):
    return _form(Routes.resend_verification, (
        H4("Resend Verification Email", cls="uk-text-center text-xl font-semibold uk-margin-medium-top"),
        P(("Enter your email address and", Br(), "we'll send you a new verification link"), cls=TextT.center),
        LabelInput("Email", id="email", type="email", placeholder="Enter your email", value=email, cls=TextT.left),
        _err_div(err), Button("Send Verification Link", cls=[ButtonT.primary, ButtonT.sm]),
        _back_to_login()))


def form(step=Step.login, email="", name="", token="", g_redirect=None, git_redirect=None, err=None):
    # Call the appropriate form based on the step
    f = None
    match step:
        case Step.login: f = login_form(email, g_redirect, git_redirect, err),
        case Step.reg: f = register_form(name, email, err),
        case Step.ph: f = phone_form(),
        case Step.otp: f = otp_form(),
        case Step.forgot_pw: f = forgot_password_form(email, err),
        case Step.reset_pw: f = reset_password_form(token, err),
        case Step.pw_reset_sent: f = password_reset_sent_form(email),
        case Step.pw_reset_ok: f = password_reset_success_form,
        case Step.em_ver: f = email_verify_form(email),
        case Step.em_ok: f = email_verified_form(),
        case Step.ver_err: f = verify_error_form(email, err),
        case Step.resend_ver: f = resend_verify_form(email, err)
        case _: f = login_form(email, g_redirect, git_redirect, err)
    return Div(f, id="auth-container", cls="w-full")
