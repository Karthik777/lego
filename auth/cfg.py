from fasthtml.oauth import GoogleAppClient, GitHubAppClient
from fasthtml.common import StrEnum, Path, AttrDictDefault
from fastcore.foundation import Config
from core import cfg as core_cfg, AppErr, boss_redirect


d = dict(db="db/users.db", want_google='true', want_github='true',
         g_cli_id='', g_cli_scrt='', git_cli_id='', git_cli_scrt='')
try:
    cfg = Config(Path(__file__).parent, ".env.override", create=d,
                 types=dict(want_google=bool, want_github=bool),
                 extra_files=core_cfg.config_file, defaults=d)
except Exception: cfg = AttrDictDefault(d)

cfg.want_google = cfg.want_google and bool(cfg.g_cli_id) and bool(cfg.g_cli_scrt)
cfg.want_github = bool(cfg.want_github) and bool(cfg.git_cli_id) and bool(cfg.git_cli_scrt)
cfg.g_cli = GoogleAppClient(cfg.g_cli_id, cfg.g_cli_scrt) if cfg.want_google else None
cfg.git_cli = GitHubAppClient(cfg.git_cli_id, cfg.git_cli_scrt) if cfg.want_github else None

EmailNotVerified = AppErr("Email is registered but not verified yet", fields=["email"])
EmailAlreadyRegistered = AppErr("Email already registered", fields=["email"])
UserNotFound = AppErr("User not found", fields=None)
VerifyErr = AppErr("Can't create verification link. Sign in and click Resend Verification link.",fields=None)
EmailNotFound = AppErr("Email not found", fields=["email"])
EmailAlreadyVerified = AppErr("Email already verified", fields=["email"])
InvalidEmail = AppErr("Invalid email or not reachable", fields=["email"])
InvalidCreds = AppErr("Invalid Credentials", fields=["email", "password"])
InvalidToken = AppErr("Invalid or Expired token", fields=["token"])
PasswordMismatch = AppErr("Passwords don't match", fields=["password", "confirm_password"])
OathError = AppErr("Auth provider does not work. Sign in with email maybe.", fields=["email"])
DefaultError = AppErr("We messed up. Please refresh.", fields=None)
def AllFieldsRequired(fields=None): return AppErr("All fields are required.", fields=fields)


class Step(StrEnum):
    """Authentication form steps."""
    login = "login"
    reg = "register"
    ph = "phone"
    otp = "otp"
    forgot_pw = "forgot-password"
    reset_pw = "reset-password"
    pw_reset_sent = "password-reset-sent"
    pw_reset_ok = "password-reset-success"
    em_ver = "email-verify"
    em_ok = "email-verified"
    ver_err = "verify-error"
    resend_ver = "resend-verify"


class Routes:
    """User management specific routes extending core user """
    base = '/a'
    login = f'{base}/lgn'
    logout = f'{base}/lgt'
    register = f'{base}/reg'
    verify_email = f'{base}/ver-em'
    ver_ph = f'{base}/ver-ph'
    ver_otp = f'{base}/ver-otp'
    verified = f'{base}/verfd'
    err = f'{base}/err'
    verification_error = f'{base}/ver-err'
    resend_verification = f'{base}/rsnd-ver'
    forgot_pw = f'{base}/fgt-pw'
    reset_pw = f'{base}/rst-pw'
    auth_modal = f'{base}/m'
    process_reset_pw = f'{base}/pr-rst-pw'
    google_clbk = f"{base}/google/callback"
    git_clbk = f"{base}/github/callback"
    skip = [login, logout, register, verify_email, ver_ph, ver_otp, auth_modal, err, forgot_pw,
            process_reset_pw, resend_verification, verified, reset_pw, verification_error, google_clbk, git_clbk,
            r'/favicon\.ico', r'/static/.*', r'.*\.css']


async def err_page(req): boss_redirect(req, Routes.err)

