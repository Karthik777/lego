"""Docker + Hetzner + Cloudflare tunnel deployment for VedicReader."""
import os, sys, secrets
from datetime import datetime
from fastcore.all import Path, joins, parse_env
from dockeasy import fasthtml_app, env_set
from cfeasy import CF
from vpseasy import hetzner_deploy, caddy_stack, Hetzner, pull_remote, push_remote, run_remote_backup, run_ssh
from setup import mk_env, env2push

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

def deploy2prod(force=None):
    '''Idempotent: provisions Hetzner VPS if needed, then deploys.
    force= \'\' | \'checksum\' | \'ignore-times\' (falls back to $RSYNC_FORCE).'''
    mk_env(env2push(), path=root/'.env')
    mk_compose()
    tid, tok = CF().setup_tunnel(domain, sd, tunnel_name=f'{sd}_{domain}')
    print('created Cloudflare tunnel:', tid)
    env_set('CF_TUNNEL_TOKEN',tok, path=root/'.env')
    force = force or os.getenv('RSYNC_FORCE', '')
    extra = RSYNC_FORCE.get(force)
    if extra: print(f'rsync force: {force} ({extra})')
    r = hetzner_deploy(sd, root, include=inc, exclude=exc, path=srv, extra=extra)
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
    elif cmd == 'deploy': deploy2prod(force=args[1] if len(args) > 1 else None)
    elif cmd == 'nuke': nuke_prod()
    elif cmd == 'env': mk_env(env2push(), path=root/'.env')
    else: print('usage: lego-deploy compose | deploy | nuke | env')

# --- Backup / restore / migration ---

def _load_prod_env():
    'Read HETZNER_IP and HETZNER_KEY from local .env file.'
    env_file = root / '.env'
    return parse_env(fn=str(env_file)) if env_file.exists() else {}

def pull_state(local_dest=None, host=None, key=None, path=srv):
    'Pull /app/data and /app/backups from production server to a local timestamped directory.'
    env = _load_prod_env()
    host = host or env.get('HETZNER_IP')
    key = key or env.get('HETZNER_KEY')
    if not host: raise ValueError('HETZNER_IP not set. Run lego-deploy first.')
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    dest = Path(local_dest or f'local_state/{ts}')
    dest.mkdir(parents=True, exist_ok=True)
    pull_remote(host, f'{path}/data', dest / 'data', key=key, verbose=True)
    pull_remote(host, f'{path}/backups', dest / 'backups', key=key, verbose=True)
    print(f'State pulled to {dest}')
    return dest

def push_state(local_src, host=None, key=None, path=srv):
    'Push local state dir (data/ backups/) to server. Stops app to release SQLite locks.'
    env = _load_prod_env()
    host = host or env.get('HETZNER_IP')
    key = key or env.get('HETZNER_KEY')
    if not host: raise ValueError('HETZNER_IP not set.')
    local_src = Path(local_src)
    run_ssh(host, f'cd {path} && docker compose stop app', key=key, verbose=True)
    for sub in ('data', 'backups'):
        src = local_src / sub
        if src.exists(): push_remote(host, src, f'{path}/{sub}', key=key, verbose=True)
    run_ssh(host, f'cd {path} && docker compose start app', key=key, verbose=True)
    print(f'State pushed from {local_src} to {host}:{path}')

def migrate(new_name, new_server_type='cx23', via='r2', local_tmp=None):
    'Migrate app to a new Hetzner server. via="r2" (recommended) or via="local".'
    env = _load_prod_env()
    old_host, old_key = env.get('HETZNER_IP'), env.get('HETZNER_KEY')
    chk_name = f'migration_{new_name}_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
    if old_host:
        print(f'Step 1: Creating checkpoint on {old_host}...')
        run_ssh(old_host,
                f'cd {srv} && docker compose exec -T app python -c '
                f'"from lego.core.backups import checkpoint; checkpoint(\'{chk_name}\')"',
                key=old_key, verbose=True)
    if via == 'r2': _migrate_via_r2(chk_name, new_name, new_server_type)
    elif via == 'local': _migrate_via_local(local_tmp, new_name, new_server_type)
    else: raise ValueError(f"via must be 'r2' or 'local', got {via!r}")

def _migrate_via_r2(chk_name, new_name, server_type):
    env = _load_prod_env()
    old_host, old_key = env.get('HETZNER_IP'), env.get('HETZNER_KEY')
    print('Step 2: Cloning checkpoint to R2...')
    run_ssh(old_host,
            f'cd {srv} && docker compose exec -T app python -c '
            f'"from lego.core.backups import clone; clone(src=\'backups/checkpoints/{chk_name}.tar.gz\', sync=False, zip=False)"',
            key=old_key, verbose=True)
    print(f'Step 3: Provisioning new server {new_name}...')
    mk_compose()
    r = hetzner_deploy(new_name, root, include=inc, exclude=exc, path=srv)
    print('Step 4: Restoring checkpoint from R2 on new server...')
    run_ssh(r.ip,
            f'cd {srv} && docker compose exec -T app python -c '
            f'"from lego.core.backups import pull_clone, restore_checkpoint; '
            f'pull_clone(\'{chk_name}.tar.gz\'); restore_checkpoint(\'{chk_name}\')"',
            key=r.key, verbose=True)
    env_set('HETZNER_IP', r.ip, path=root / '.env')
    env_set('HETZNER_KEY', str(r.key), path=root / '.env')
    print(f'Migration complete. New server: {r.ip}')

def _migrate_via_local(local_tmp, new_name, server_type):
    tmp = pull_state(local_dest=local_tmp)
    print(f'Step 3: Provisioning new server {new_name}...')
    mk_compose()
    r = hetzner_deploy(new_name, root, include=inc, exclude=exc, path=srv)
    push_state(tmp, host=r.ip, key=r.key)
    env_set('HETZNER_IP', r.ip, path=root / '.env')
    env_set('HETZNER_KEY', str(r.key), path=root / '.env')
    print(f'Migration complete. New server: {r.ip}')

# --- CLI entry points ---

def backup_cli():
    'lego-backup [clone] — run backup, optionally clone to R2.'
    from lego.core.backups import run_backup, clone
    args = sys.argv[1:]
    run_backup()
    if 'clone' in args: clone(src='backups'); print('Cloned backups to R2.')

def restore_cli():
    'lego-restore [<timestamp>] — restore from most recent or named snapshot.'
    from lego.core.backups import restore
    args = sys.argv[1:]
    restore(backup_ts=args[0] if args else None)
    print(f'Restored from {"latest" if not args else args[0]}')

def checkpoint_cli():
    'lego-checkpoint <name> [restore] [--overwrite] — create or restore a named checkpoint.'
    from lego.core.backups import checkpoint, restore_checkpoint
    args = sys.argv[1:]
    if not args: print('Usage: lego-checkpoint <name> [restore] [--overwrite]'); return
    name = args[0]
    if 'restore' in args: restore_checkpoint(name); print(f'Restored checkpoint: {name}')
    else: out = checkpoint(name, overwrite='--overwrite' in args); print(f'Checkpoint: {out}')

def migrate_cli():
    'lego-migrate <new-server-name> [--via r2|local] [--type cx23]'
    args = sys.argv[1:]
    if not args: print('Usage: lego-migrate <new-server-name> [--via r2|local] [--type cx23]'); return
    new_name, via, server_type = args[0], 'r2', 'cx23'
    for i, a in enumerate(args):
        if a == '--via' and i + 1 < len(args): via = args[i + 1]
        if a == '--type' and i + 1 < len(args): server_type = args[i + 1]
    migrate(new_name, new_server_type=server_type, via=via)

if __name__ == '__main__': deploy_cli()