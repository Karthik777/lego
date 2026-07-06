"""Docker + Hetzner + Cloudflare tunnel deployment for VedicReader."""
import os, sys, secrets
from fastcore.all import Path, joins
from dockeasy import fasthtml_app, env_set, env_get
from cfeasy import CF
from vpseasy import hetzner_deploy, caddy_stack, Hetzner
from setup import ROOT, mk_env, env2push, push_gh_vars

root = Path(__file__).resolve().parent
pkgs = ['rclone','libsqlite3-dev','curl']
vols = ['/app/data', '/app/backups', '/app/static']
inc = ['lego/','static/','pyproject.toml','docker-compose.yml','main.py','Dockerfile','Caddyfile','.env','uv.lock']
exc = ['data/','backups/', 'mrsladjoe/']
sd, domain, srv = 'lego', 'sankalpa.sh', '/srv/app'
RSYNC_FORCE = {'checksum': '--checksum', 'ignore-times': '--ignore-times'}

def mk_compose():
    df = fasthtml_app(pkgs=pkgs, vols=vols, healthcheck='/health', cmd=['python', 'main.py'])
    return caddy_stack(joins('.', [sd, domain]), df, vols=vols)

def deploy2prod(force=None, password=False):
    '''Idempotent: provisions Hetzner VPS if needed, then deploys.
    force= \'\' | \'checksum\' | \'ignore-times\' (falls back to $RSYNC_FORCE).'''
    mk_env(env2push(), path=root/'.env')
    mk_compose()
    tid, tok = CF().setup_tunnel(domain, sd, tunnel_name=f'{sd}_{domain}')
    print('created Cloudflare tunnel:', tid)
    env_set('CF_TUNNEL_TOKEN',tok, path=root/'.env')
    force = force or os.getenv('RSYNC_FORCE', '')
    extra = RSYNC_FORCE.get(force)
    hz_nm = env_get('SERVER_NAME', path=root/'.env', default=sd)
    u, k = env_get('SERVER_USER', path=root/'.env', default='deploy'), env_get('HETZNER_KEY', path=root/'.env')
    p = env_get('SERVER_PASSWORD', path=root/'.env', default=password)
    if extra: print(f'rsync force: {force} ({extra})')
    r = hetzner_deploy(hz_nm, root, include=inc, exclude=exc, path=srv, extra=extra, password=p, user=u, key=k)
    env_set('HETZNER_IP', r.ip, path=root/'.env')
    env_set('HETZNER_KEY', r.key, path=root/'.env')
    if (ROOT / '.gheasy/config.json').exists() :push_gh_vars()
    print(f'deployed: {r.ip}')

def nuke_prod():
    'Nuke prod server and Cloudflare tunnel. Use with caution!'
    typ = secrets.token_urlsafe(8)
    ans = input(f'WARNING: This will irreversibly delete the production server and tunnel. Type {typ} to proceed: ')
    if ans != typ: return print('Aborting nuke.')
    hz_nm = env_get('server_name', sd)
    Hetzner().delete(hz_nm)
    print(f'prod server {hz_nm} deleted')
    try:
        cf = CF()
        tid = cf.tunnel_id(sd)
        cf.delete_tunnel(tid)
        print(f'prod tunnel {tid} deleted')
    except ValueError: print('No prod tunnel found, skipping tunnel nuke.')
    except Exception as e: print(f'Error during tunnel nuke: {e}')

def deploy_cli():
    args = sys.argv[1:]
    cmd = args[0] if args else ''
    if cmd == 'compose': mk_compose()
    elif cmd == 'deploy': deploy2prod(force=args[1] if len(args) > 1 else None)
    elif cmd == 'nuke': nuke_prod()
    elif cmd == 'env': mk_env(env2push(), path=root/'.env')
    else: print('usage: lego-deploy compose | deploy')

if __name__ == '__main__': deploy2prod(password=True)