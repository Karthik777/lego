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
tunnel_nm = f'{sd}_{domain}'
# The second hostname: the apex of the zone lego is already in. Same server, same container,
# same tunnel and now the same zone — the hora block answers at /hora, and on the apex that
# is what the root should serve.
#
# `or` rather than a getenv default, because the workflow passes every key through as
# `${{ vars.KEY }}` — an unset repository variable arrives as the empty string, not as
# absent, and getenv's default would not fire. That would put `http:// {` in the Caddyfile
# and take both sites down until someone read the generated config.
hora_domain, hora_route = os.getenv('HORA_DOMAIN') or domain, '/hora'
app_svc, app_port = 'app', 5001
# caddy_stack writes Dockerfile, docker-compose.yml and Caddyfile relative to the cwd, and
# the compose mounts ./Caddyfile — so this has to stay a relative path or the mount would
# point at a directory that only exists on the machine that ran the deploy.
CADDYFILE = Path('Caddyfile')
RSYNC_FORCE = {'checksum': '--checksum', 'ignore-times': '--ignore-times'}

def caddy_site(host, *directives):
    '''One site block for the shared Caddy.

    http:// because the tunnel terminates TLS in front of it — the same prefix dockeasy
    writes for `cloudflared=True`, for the same reason: there is no public port 80 to run
    an ACME challenge against.'''
    return f'http://{host} {{\n' + ''.join(f'\t{d}\n' for d in directives) + f'\treverse_proxy {app_svc}:{app_port}\n}}\n'

def mk_caddyfile(path=CADDYFILE):
    '''Both hostnames, one Caddy, one app container.

    dockeasy's `caddy_svc` writes a Caddyfile for a single site, so caddy_stack's copy is
    replaced with this one after the fact. Nothing else about the stack changes: the apex
    reaches the same container through the same tunnel, and Caddy tells the two apart by the
    Host header it was going to read anyway.

    The rewrite matches the bare root only, which is all hora needs — it is one page, and
    /static and every other path still resolve untouched on both domains.'''
    Path(path).write_text(caddy_site(joins('.', [sd, domain])) + caddy_site(hora_domain, f'rewrite / {hora_route}'))
    print(f'caddy: {joins(".", [sd, domain])} + {hora_domain} -> {app_svc}:{app_port}')

def mk_compose():
    df = fasthtml_app(pkgs=pkgs, vols=vols, healthcheck='/health', cmd=['python', 'main.py'])
    c = caddy_stack(joins('.', [sd, domain]), df, vols=vols)
    mk_caddyfile()
    return c

def add_hora_dns(cf, tid):
    '''Point the apex at the tunnel that already exists.

    One tunnel, not two: cloudflared runs with `--url http://caddy`, so every hostname routed
    through it arrives at the same Caddy. An apex cannot hold a CNAME in plain DNS; Cloudflare
    serves one anyway by flattening it, which is why this needs to stay proxied.

    `upsert_record` clears any same-name record first, so an A record or a parked CNAME
    already sitting on the apex is replaced rather than fought with.

    A failure here costs the apex and nothing else: the tunnel and the lego record are both
    in place by the time this runs. So it warns with the record to add by hand rather than
    aborting a deploy that is otherwise fine.'''
    try:
        cf.tunnel_cname(hora_domain, hora_domain, tid)
        print(f'hora dns: {hora_domain} -> tunnel {tid}')
    except Exception as e:
        print(f'WARNING: could not point {hora_domain} at the tunnel: {e}\n'
              f'         {joins(".", [sd, domain])} is unaffected. Add a proxied CNAME '
              f'{hora_domain} -> {tid}.cfargotunnel.com by hand.')

def deploy2prod(force=None, password=False):
    '''Idempotent: provisions Hetzner VPS if needed, then deploys.
    force= \'\' | \'checksum\' | \'ignore-times\' (falls back to $RSYNC_FORCE).'''
    mk_env(env2push(), path=root/'.env')
    mk_compose()
    cf = CF()
    tid, tok = cf.setup_tunnel(domain, sd, tunnel_name=tunnel_nm)
    print('created Cloudflare tunnel:', tid)
    add_hora_dns(cf, tid)
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

def rm_hora_dns(cf):
    '''Drop the apex CNAME, which would otherwise outlive the tunnel it names.

    The name match is exact on purpose: lego's own record lives in this same zone now, and a
    prefix or suffix test would take `lego.sankalpa.sh` out with the apex.'''
    zid = cf.zone_id(hora_domain)
    for r in cf.dns_records(zid):
        if r.get('name') == hora_domain and r.get('type') == 'CNAME':
            cf.delete_record(zid, r['id'])
            print(f'prod dns {hora_domain} deleted')

def nuke_prod():
    'Nuke prod server, Cloudflare tunnel, and the apex record. Use with caution!'
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
        try: rm_hora_dns(cf)
        except Exception as e: print(f'Error removing {hora_domain} record: {e}')
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

if __name__ == '__main__': deploy2prod(password=True)