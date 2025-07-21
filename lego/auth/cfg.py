from fasthtml.oauth import GoogleAppClient, GitHubAppClient
from fasthtml.common import StrEnum, dataclass, AttrDictDefault, str2bool
import os
from lego.core import cfg as core_cfg, AppErr, get_db_pth, RouteOverrides

cfg = core_cfg
cfg.update(AttrDictDefault(db=get_db_pth('auth'),
                           want_google=str2bool(os.getenv('WANT_GOOGLE', 'true')),
                           want_github=str2bool(os.getenv('WANT_GIT', 'false')),
                           g_cli_id=os.getenv('GOOGLE_CLI',''),
                           g_cli_scrt=os.getenv('GOOGLE_SCRT',''),
                           git_cli_id=os.getenv('GIT_CLI',''),
                           git_cli_scrt=os.getenv('GIT_SCRT','')))
cfg.want_google = cfg.want_google and bool(cfg.g_cli_id) and bool(cfg.g_cli_scrt)
cfg.want_github = bool(cfg.want_github) and bool(cfg.git_cli_id) and bool(cfg.git_cli_scrt)
cfg.g_cli = GoogleAppClient(cfg.g_cli_id, cfg.g_cli_scrt) if cfg.want_google else None
cfg.git_cli = GitHubAppClient(cfg.git_cli_id, cfg.git_cli_scrt) if cfg.want_github else None

EmailNotVerified = AppErr('Email is registered but not verified yet', fields=['email'])
EmailAlreadyRegistered = AppErr('Email already registered', fields=['email'])
UserNotFound = AppErr('User not found', fields=None)
VerifyErr = AppErr('Cannot create verification link. Sign in and click Resend Verification link.',fields=None)
EmailNotFound = AppErr('Email not found', fields=['email'])
EmailAlreadyVerified = AppErr('Email already verified', fields=['email'])
InvalidEmail = AppErr('Invalid email or not reachable', fields=['email'])
InvalidCreds = AppErr('Invalid Credentials', fields=['email', 'password'])
InvalidToken = AppErr('Invalid or Expired token', fields=['token'])
PasswordMismatch = AppErr('Passwords do not match', fields=['password', 'confirm_password'])
OathError = AppErr('Auth provider does not work. Sign in with email maybe.', fields=['email'])
DefaultError = AppErr('We messed up. Please refresh.', fields=None)
def AllFieldsRequired(fields=None): return AppErr('All fields are required.', fields=fields)

class Step(StrEnum):
    '''Authentication form steps.'''
    login, reg, ph, otp = 'login', 'register', 'phone', 'otp'
    forgot_pw, reset_pw = 'forgot-password', 'reset-password'
    pw_reset_sent, pw_reset_ok = 'password-reset-sent', 'password-reset-success'
    em_ver, em_ok, ver_err, resend_ver = 'email-verify', 'email-verified', 'verify-error', 'resend-verify'

@dataclass(frozen=True)
class Routes:
    '''User-management-specific routes extending core user '''
    base = '/a/'
    auth_ok = f'{base}ok'
    login = f'{base}lgn'
    logout = f'{base}lgt'
    register = f'{base}reg'
    verify_email = f'{base}ver-em'
    ver_ph = f'{base}ver-ph'
    ver_otp = f'{base}ver-otp'
    verified = f'{base}verfd'
    err = f'{base}err'
    verification_error = f'{base}ver-err'
    resend_verification = f'{base}rsnd-ver'
    forgot_pw = f'{base}fgt-pw'
    reset_pw = f'{base}rst-pw'
    auth_modal = f'{base}m'
    process_reset_pw = f'{base}pr-rst-pw'
    google_clbk = f'{base}google/callback'
    git_clbk = f'{base}github/callback'
    skip = [login, logout, register, verify_email, ver_ph, ver_otp, auth_modal, err, forgot_pw,
            process_reset_pw, resend_verification, verified, reset_pw, verification_error, google_clbk, git_clbk,
            r'/favicon\.ico', r'/static/.*', '/'] + RouteOverrides.skip
