"""One-shot project setup: git-lfs, DB backup/restore, secrets push to GitHub."""
import os, sys, shutil
from fastcore.all import Path, run, L, parse_env, filter_keys,in_
from dockeasy import env_set
from gheasy import GheasyConfig, gh_lfs, gh_push_env

__all__ = ['setup', 'push_gh_vars', 'mk_env','env2push']

ROOT = Path(__file__).resolve().parent
LFS_PATTERNS = ['*.mp3', '*.ogg', '*.wav', '*.flac', '*.ico', '*.png', '*.jpg', '*.jpeg', '*.webp', '*.xml']
ENV_KEYS = dict(MODE='dev', PORT='5001', DOMAIN='http://localhost:5001', TOKEN_EXP='691200', PURGE='false',
    JWT_SCRT=None, RESEND_API_KEY=None, WANT_GOOGLE='true', WANT_GIT='false', GOOGLE_CLI=None, GOOGLE_SCRT=None,
    GIT_CLI=None, GIT_SCRT=None, NEED_BACKUP='true', RC_TYPE='s3', RC_PROVIDER='Cloudflare', CF_ACCESS_KEY_ID=None,
    CF_SCRT_ACCESS_KEY=None, CF_ENDPOINT=None, CF_TUNNEL_TOKEN=None, HCLOUD_TOKEN=None)

def _load_env(): return dict(os.environ) | (parse_env(fn=str(envf)) if (envf := ROOT / '.env').exists() else {})
def env2push(): return ENV_KEYS | filter_keys(_load_env(),in_(ENV_KEYS))

def _init_gheasy():
	if app:=GheasyConfig.load(ROOT).app: print(f'gheasy: config already initialized for {app}')
	gh=GheasyConfig(app='vedicreader', env_schema=ENV_KEYS).save(ROOT)
	print(f'gheasy: initialized config fpr {gh.app} with env schema keys: {len(gh.env_schema)}')

def lfs():
	gh_lfs(LFS_PATTERNS, path=str(ROOT))
	print(f'lfs: tracking {len(LFS_PATTERNS)} patterns')

def mk_env(env:dict=None, path=Path(ROOT/'.env.example')):
	'Create .env.example file with keys from ENV_KEYS and empty values.'
	env = env or ENV_KEYS
	for k,v in env.items(): env_set(k,v,path)
	print(f'env: wrote/updated {path}')

def push_gh_vars(dry_run=False):
	"Push local .env values to GitHub. None-default keys → secrets; string-default → variables."
	to_push = env2push()
	if not to_push: return print('push: nothing to push (no matching keys with values in .env)')
	gh_push_env(to_push, dry_run=dry_run, path=ROOT)

def push_cli(): push_gh_vars('--dry-run' in sys.argv)

def setup():
	_init_gheasy()
	gh_lfs(LFS_PATTERNS, path=str(ROOT))
	print(f'lfs: tracking {len(LFS_PATTERNS)} patterns')
	mk_env()

if __name__ == '__main__':
	if 'push' in sys.argv: push_gh_vars('--dry-run' in sys.argv)
	elif 'mkenv' in sys.argv: mk_env(env2push(), path=ROOT/'.env')
	else: setup()
