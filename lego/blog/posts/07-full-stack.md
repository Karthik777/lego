---
slug: the-full-stack
date: 2026-05-15
title: "The stack: how this blog deploys"
summary: "One deploy.py. dockeasy builds the containers, vpseasy provisions the VPS, cfeasy wires the Cloudflare tunnel, gheasy handles CI, kosha keeps agents honest. Clone lego and you get all of it."
visibility: public
author_name: Karthik
layout: newspaper
---

`python deploy.py deploy`. First run provisions a Hetzner VPS, sets up a Cloudflare tunnel, rsyncs the app, and starts the containers. Every run after that just rsyncs and restarts. No SSH session. No manual steps.

The full `deploy.py` for this blog:

```python
from dockeasy import fasthtml_app, env_set
from cfeasy import CF
from vpseasy import hetzner_deploy, caddy_stack

sd, domain, srv = 'lego', 'sankalpa.sh', '/srv/app'

def mk_compose():
    df = fasthtml_app(pkgs=pkgs, vols=vols, healthcheck='/health',
                      cmd=['python', 'main.py'])
    return caddy_stack(joins('.', [sd, domain]), df, vols=vols)

def deploy2prod():
    mk_env(env2push(), path=root/'.env')
    mk_compose()
    tid, tok = CF().setup_tunnel(domain, tunnel_name=f'{sd}_{domain}')
    env_set('CF_TUNNEL_TOKEN', tok, path=root/'.env')
    r = hetzner_deploy(sd, root, include=inc, exclude=exc, path=srv)
    env_set('HETZNER_IP', r.ip, path=root/'.env')
```

Three imports. Three function calls. The packages handle the rest.

## dockeasy

`fasthtml_app()` generates the Dockerfile — right base image, uv cache mounts, healthcheck, entrypoint. `caddy_stack()` wraps it in a Compose file with a Caddy reverse proxy configured for the domain and a cloudflared sidecar.

The app gets no public port. Traffic enters through the tunnel, hits Caddy, Caddy proxies to the app container. Nothing to open in the VPS firewall.

## vpseasy

`hetzner_deploy()` is idempotent. First call: provisions a Hetzner server with cloud-init, waits for it to come up, rsyncs the project, runs `docker compose up`. Second call: rsyncs and restarts.

The same cloud-init YAML runs in a local Multipass VM. Before touching Hetzner you test the full stack locally:

```python
from vpseasy import Multipass, deploy_mp, multi_init

mp = Multipass()
mp.launch('lego', cloud_init=multi_init('lego', docker=True))
deploy_mp('lego', src='.', path='/srv/app')
```

Identical to prod. The local variant skips UFW and fail2ban so it comes up faster, but the application definition is the same.

```col
```

## cfeasy

`CF().setup_tunnel()` creates the Cloudflare Zero Trust tunnel if it doesn't exist, or reuses it. Creates the CNAME record pointing the domain at the tunnel. Returns the token you pass to cloudflared. One call, idempotent.

Without cfeasy the same operation takes five separate API calls with IDs threaded between them — zone ID, account ID, tunnel ID, CNAME target construction, record creation. Run it twice and you have duplicate records. With cfeasy it's one line and the second run does nothing.

## gheasy

`gh_setup()` wires CI. It generates `.github/workflows/gheasy.yml` with lint, test, and publish jobs, installs a pre-commit hook, and routes secrets from your local env to GitHub Actions using a schema:

```python
from gheasy.core import GheasyConfig, gh_push_env

cfg = GheasyConfig(app='lego', env_schema={
    'PORT': '5001',
    'DOMAIN': 'https://lego.sankalpa.sh',
    'JWT_SCRT': None,
    'RESEND_API_KEY': None,
    'CF_TUNNEL_TOKEN': None,
})
gh_push_env(dict(os.environ))
```

Keys with `None` become GitHub secrets. Keys with a string default become variables. `gh_push_env` sends them in one pass — `gh secret set` for the secrets, `gh variable set` for the rest.

## kosha

Dev-time only. `k.sync()` indexes the repo and every installed package into a litesearch database. It installs a Claude Code skill into `.claude/skills/kosha/` that loads automatically on session start.

The agent runs `k.status()` first, then queries before writing anything. It surfaces `fasthtml_app` from dockeasy, `hetzner_deploy` from vpseasy, the existing route patterns in your codebase — what already exists, before generating from scratch. The call graph tells it which functions are load-bearing.

---

Clone [github.com/Karthik777/lego](https://github.com/Karthik777/lego). `uv sync` installs everything including the dev toolchain. Add your env vars, run `python deploy.py deploy`. The blog, auth, backups, CI, and code intelligence for your agent all come with the template.
