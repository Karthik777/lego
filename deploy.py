"""Docker + Hetzner + Cloudflare tunnel deployment for VedicReader."""
import sys, secrets
from fastcore.all import Path, joins
from dockeasy import fasthtml_app, env_set
from cfeasy import CF
from vpseasy import hetzner_deploy, caddy_stack, Hetzner, run_ssh
from setup import mk_env, env2push

root = Path(__file__).resolve().parent
pkgs = ['rclone','libsqlite3-dev','curl']
vols = ['/app/data', '/app/backups']
inc = ['lego/','static/','pyproject.toml','docker-compose.yml','main.py','Dockerfile','Caddyfile','.env','uv.lock']
exc = ['data/','backups/']
sd, domain, srv = 'lego', 'sankalpa.sh', '/srv/app'

def mk_compose():
    df = fasthtml_app(pkgs=pkgs, vols=vols, healthcheck='/health', cmd=['python', 'main.py'])
    return caddy_stack(joins('.', [sd, domain]), df, vols=vols)

def deploy2prod():
    'Idempotent: provisions Hetzner VPS if needed, then deploys.'
    mk_env(env2push(), path=root/'.env')
    mk_compose()
    tid, tok = CF().setup_tunnel(domain, sd, tunnel_name=f'{sd}_{domain}')
    print('created Cloudflare tunnel:', tid)
    env_set('CF_TUNNEL_TOKEN',tok, path=root/'.env')
    r = hetzner_deploy(sd, root, include=inc, exclude=exc, path=srv)
    env_set('HETZNER_IP', r.ip, path=root/'.env')
    env_set('HETZNER_KEY', r.key, path=root/'.env')
    print(f'deployed: {r.ip}')

def nuke_prod():
    'Nuke prod server and Cloudflare tunnel. Use with caution!'
    typ = secrets.token_urlsafe(8)
    input(f'WARNING: This will irreversibly delete the production server and tunnel. Type {typ} to proceed: ')
    if input() != typ: return print('Aborting nuke.')
    Hetzner().delete(sd)
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
    elif cmd == 'deploy': deploy2prod()
    elif cmd == 'nuke': nuke_prod()
    else: print('usage: vr-deploy compose | deploy')

if __name__ == '__main__': deploy_cli()