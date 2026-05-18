"""One-shot project setup: git-lfs, DB backup/restore, secrets push to GitHub."""
import os, sys, shutil
from fastcore.all import Path, parse_env, filter_keys,in_, first
from dockeasy import env_set
from gheasy import GheasyConfig, gh_lfs, gh_push_env
from gheasy.workflow import Workflow

__all__ = ['setup', 'push_gh_vars', 'mk_env','env2push']

def repo_root() -> Path:
	'Find the root of the current git repository, or None if not in a repo.'
	return first((Path.cwd(), *Path.cwd().parents), lambda p: (p/'.git').exists())

def mv_skill_md(dry_run=True, dir=None) -> None:
	'Copy bundled SKILL.md into `.agents/skills/lego/` and `.claude/skills/lego/` at project root or specified dir.'
	base = Path(__file__).parent if '__file__' in globals() else Path.cwd()
	if not (src := base.joinpath('SKILL.md')).exists(): return
	root = Path(dir or repo_root() or '.')
	ts = [root/'.agents/skills/lego/SKILL.md', root/'.claude/skills/lego/SKILL.md']
	if dry_run: print(f'Would copy {src} to: {list(map(str,ts))}')
	else:
		for p in ts: p.mk_write(src.read_text(encoding='utf-8'))
		print(f'Installed -> {list(map(str,ts))}')

ROOT = repo_root()
LFS_PATTERNS = ['*.mp3', '*.ogg', '*.wav', '*.flac', '*.ico', '*.png', '*.jpg', '*.jpeg', '*.webp', '*.xml']
ENV_KEYS = dict(MODE='dev', PORT='5001', DOMAIN='lego.sankalpa.sh', TOKEN_EXP='691200', PURGE='false',
    JWT_SCRT=None, RESEND_API_KEY=None, WANT_GOOGLE='true', WANT_GIT='false', GOOGLE_CLI=None, GOOGLE_SCRT=None,
    GIT_CLI=None, GIT_SCRT=None, NEED_BACKUP='true', RC_TYPE='s3', RC_PROVIDER='Cloudflare', CF_ACCESS_KEY_ID=None,
    CF_SCRT_ACCESS_KEY=None, CF_ENDPOINT=None, CF_TUNNEL_TOKEN=None, CLOUDFLARE_API_TOKEN=None, HCLOUD_TOKEN=None)

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
	print(f'push: {"would push" if dry_run else "pushed"} {len(to_push)} keys to GitHub as '
	      f'{"secrets" if any(v is None for v in ENV_KEYS.values()) else "variables"}')

def push_cli(): push_gh_vars('--dry-run' in sys.argv)

def push_ssh_key():
	"Upload ~/.ssh/lego private key as the DEPLOY_KEY GitHub secret (matches vpseasy _res_key(name='lego'))."
	from gheasy import gh_deploy_key_setup
	gh_deploy_key_setup(Path.home()/'.ssh'/'lego')

def gen_deploy_workflow():
	wf = Workflow('deploy')
	wf.on.push(branches=['main'])
	env = {k: (f'${{{{ secrets.{k} }}}}' if v is None else f'${{{{ vars.{k} }}}}') for k, v in ENV_KEYS.items()}
	ssh_cmd = 'mkdir -p ~/.ssh && echo "${{ secrets.DEPLOY_KEY }}" > ~/.ssh/lego && chmod 600 ~/.ssh/lego'
	(wf.job('deploy').runs_on('ubuntu-latest')
	 .env(**env).checkout().end_step()
	 .setup_uv().with_(python_version='3.13').end_step()
	 .uv_install('uv sync --group dev').end_step()
	 .step('Install SSH key').if_("secrets.DEPLOY_KEY != ''").run(ssh_cmd).end_step()
	 .step('Deploy').run('python deploy.py deploy').end_job())
	p = ROOT / '.github' / 'workflows' / 'deploy.yml'
	wf.build().save(p)
	print(f'workflow: wrote {p}')

def setup():
	_init_gheasy()
	gh_lfs(LFS_PATTERNS, path=str(ROOT))
	print(f'lfs: tracking {len(LFS_PATTERNS)} patterns')
	mk_env()
	gen_deploy_workflow()
	install_skills()
	print('Setup complete. Please review the generated .env.example, .github/workflows/deploy.yml, and SKILL.md files.'
	      'Update .env with your secrets and push to GitHub to trigger the deploy workflow.')

def install_skills():
	import importlib
	mv_skill_md(dry_run=False)
	for nm in ('dockeasy', 'gheasy', 'vpseasy', 'cfeasy', 'kosha', 'litesearch'):
		try: mod = importlib.import_module(nm)
		except ImportError: print(f'skip {nm}: not installed'); continue
		if mv := getattr(mod, 'mv_skill_md', None): mv(dry_run=False)
		else: print(f'skip {nm}: no mv_skill_md')

if __name__ == '__main__':
	if 'push' in sys.argv: push_cli()
	elif 'mkenv' in sys.argv: mk_env(env2push(), path=ROOT/'.env')
	elif 'workflow' in sys.argv: gen_deploy_workflow()
	elif 'skills' in sys.argv: install_skills()
	elif 'ssh-key' in sys.argv: push_ssh_key()
	else: setup()