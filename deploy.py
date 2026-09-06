"""Docker + Hetzner + Cloudflare tunnel deployment for VedicReader."""
import os, sys, secrets
from fastcore.all import Path, joins
from dockeasy import Dockerfile, env_set, env_get
from cfeasy import CF
from vpseasy import hetzner_deploy, caddy_stack, Hetzner
from setup import ROOT, mk_env, env2push, push_gh_vars

root = Path(__file__).resolve().parent
pkgs = ['rclone','libsqlite3-dev','curl']
vols = ['/app/data', '/app/backups', '/app/static']
inc = ['lego/','static/','pyproject.toml','docker-compose.yml','main.py','Dockerfile','Caddyfile','.dockerignore','.env','uv.lock']
exc = ['data/','backups/', 'mrsladjoe/']
sd, domain, srv = 'lego', 'sankalpa.sh', '/srv/app'
tunnel_nm = f'{sd}_{domain}'
# The extra hostnames: one block each, served at the root of its own host. Same server, same
# container, same tunnel and the same zone as lego.sankalpa.sh — muhurtha answers at
# /muhurtha and thrifty at /thrifty, and on their own hosts that is what the root should serve.
#
# `or` rather than a getenv default, because the workflow passes every key through as
# `${{ vars.KEY }}` — an unset repository variable arrives as the empty string, not as
# absent, and getenv's default would not fire. That would put `http:// {` in the Caddyfile
# and take every site down until someone read the generated config.
SITES = {os.getenv('MUHURTHA_DOMAIN') or domain: os.getenv('APEX_ROUTE') or '/muhurtha',
         os.getenv('THRIFTY_DOMAIN') or f'thrifty.{domain}': '/thrifty'}
app_svc, app_port = 'app', 5001
# caddy_stack writes Dockerfile, docker-compose.yml and Caddyfile relative to the cwd, and
# the compose mounts ./Caddyfile — so this has to stay a relative path or the mount would
# point at a directory that only exists on the machine that ran the deploy.
CADDYFILE = Path('Caddyfile')
RSYNC_FORCE = {'checksum': '--checksum', 'ignore-times': '--ignore-times'}

def caddy_site(host, *directives):
    return f'http://{host} {{\n' + ''.join(f'\t{d}\n' for d in directives) + f'\treverse_proxy {app_svc}:{app_port}\n}}\n'

def mk_caddyfile(path=CADDYFILE):
    main = joins('.', [sd, domain])
    Path(path).write_text(caddy_site(main) + ''.join(caddy_site(h, f'rewrite / {r}') for h, r in SITES.items()))
    print(f'caddy: {", ".join([main, *SITES])} -> {app_svc}:{app_port}')

def mk_compose():
    df = (Dockerfile().from_('python:3.13-slim').workdir('/app').apt_install(*pkgs)
          .run('pip install uv').copy('pyproject.toml', '.').copy('uv.lock', '.')
          .run('uv sync --frozen --no-dev --no-cache')
          .env('PATH', '/app/.venv/bin:$PATH').copy('.', '.')
          .run('uv pip check && python -c "import lego"')
          .run('mkdir -p ' + ' '.join(vols))
          .healthcheck('curl -f http://localhost:5001/health', i='30s', t='5s', r='3')
          .expose(5001).cmd(['python', 'main.py']))
    c = caddy_stack(joins('.', [sd, domain]), df, vols=vols)
    mk_caddyfile()
    return c

def zone_of(host): return '.'.join(host.split('.')[-2:])

def add_site_dns(cf, tid):
    for host in SITES:
        try:
            cf.tunnel_cname(zone_of(host), host, tid)
            print(f'dns: {host} -> tunnel {tid}')
        except Exception as e:
            print(f'WARNING: could not point {host} at the tunnel: {e}\n'
                  f'         {joins(".", [sd, domain])} is unaffected. Add a proxied CNAME '
                  f'{host} -> {tid}.cfargotunnel.com by hand.')

def deploy2prod(force=None, password=False):
    '''Idempotent: provisions Hetzner VPS if needed, then deploys.
    force= \'\' | \'checksum\' | \'ignore-times\' (falls back to $RSYNC_FORCE).'''
    mk_env(env2push(), path=root/'.env')
    mk_compose()
    cf = CF()
    tid, tok = cf.setup_tunnel(domain, sd, tunnel_name=tunnel_nm)
    print('created Cloudflare tunnel:', tid)
    add_site_dns(cf, tid)
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

def rm_site_dns(cf):
    for host in SITES:
        zid = cf.zone_id(zone_of(host))
        for r in cf.dns_records(zid):
            if r.get('name') == host and r.get('type') == 'CNAME':
                cf.delete_record(zid, r['id'])
                print(f'prod dns {host} deleted')

def nuke_prod():
    'Nuke prod server, Cloudflare tunnel, and the extra host records. Use with caution!'
    typ = secrets.token_urlsafe(8)
    ans = input(f'WARNING: This will irreversibly delete the production server and tunnel. Type {typ} to proceed: ')
    if ans != typ: return print('Aborting nuke.')
    # SERVER_NAME, and as a keyword: env_get's second positional is the .env path, so the
    # old call was reading the key out of a file called "lego" and always getting the default.
    hz_nm = env_get('SERVER_NAME', path=root/'.env', default=sd)
    Hetzner().delete(hz_nm)
    print(f'prod server {hz_nm} deleted')
    try:
        cf = CF()
        # deploy2prod names the tunnel `{sd}_{domain}`; looking it up as `sd` never found it
        tid = cf.tunnel_id(tunnel_nm)
        try: rm_site_dns(cf)
        except Exception as e: print(f'Error removing the extra host records: {e}')
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
    else: print('usage: lego-deploy compose | deploy | nuke | env')

if __name__ == '__main__': deploy_cli()