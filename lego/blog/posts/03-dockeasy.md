---
slug: dockeasy-dockerfile-builder
date: 2026-04-01
title: dockeasy: Dockerfiles without the archaeology
summary: A fluent Python builder for Dockerfiles, Caddyfiles, and Docker Compose stacks. Smart defaults per language, cache mounts by default, multi-stage without the boilerplate. Caddy, CrowdSec, and Cloudflare tunnel service helpers included.
visibility: public
author_name: Karthik
---

dockeasy generates Dockerfiles, Caddyfiles, and Compose stacks from Python. The code is at [github.com/vedicreader/dockeasy](https://github.com/vedicreader/dockeasy).

## Dockerfile builder

```python
from dockeasy import Dockerfile

df = (Dockerfile()
      .from_('python:3.13-slim')
      .workdir('/app')
      .copy('pyproject.toml', '.')
      .run_mount('uv sync --frozen', target='/root/.cache/uv')
      .copy('.', '.')
      .expose(8000)
      .cmd(['uv', 'run', 'python', '-m', 'myapp']))
```

`run_mount()` adds `--mount=type=cache` automatically. Build cache survives between runs.

## Framework builders

```python
from dockeasy import fasthtml_app, python_app, go_app

df = fasthtml_app()                               # port 5001, uv, single-stage
df = python_app()                                 # port 8000, uv, multi-stage
df = python_app(pkgs=['httpx'], vols=['/app/data'])
df = go_app()                                     # builder + distroless runtime
df = detect_app('.')                              # sniffs go.mod, Cargo.toml, package.json, pyproject.toml
```

## Building and running

```python
from dockeasy import drun, containers, logs, stop, rm

tag = df.build(tag='myapp:latest', path='.')      # builds via docker compose build
cid = drun(tag, detach=True, ports={5001: 5001},
           name='myapp', check=True)
print(logs('myapp', n=20))
stop('myapp'); rm('myapp')
```

## Caddy

`caddy_svc()` writes a Caddyfile and returns service kwargs for `Compose.svc()`. The image it picks depends on what is enabled.

```python
from dockeasy import Compose, caddy_svc, cloudflared_svc, crowdsec

# Direct: Caddy auto-TLS, ports 80 and 443 open
dc = (Compose()
    .svc('app', build='.', networks=['web'], restart='unless-stopped')
    .svc('caddy', **caddy_svc('myapp.com', port=5001))
    .network('web').volume('caddy_data').volume('caddy_config'))

# Cloudflare tunnel: no open ports
dc = (Compose()
    .svc('app', build='.', networks=['web'], restart='unless-stopped')
    .svc('caddy', **caddy_svc('myapp.com', cloudflared=True))
    .svc('cloudflared', **cloudflared_svc())
    .network('web').volume('caddy_data').volume('caddy_config'))

# CrowdSec + tunnel: IPS with no open ports
dc = (Compose()
    .svc('app', build='.', networks=['web'], restart='unless-stopped')
    .svc('caddy', **caddy_svc('myapp.com', crowdsec=True, cloudflared=True))
    .svc('crowdsec', **crowdsec())
    .svc('cloudflared', **cloudflared_svc())
    .network('web')
    .volume('caddy_data').volume('caddy_config')
    .volume('crowdsec-db').volume('crowdsec-config'))
```

`caddy_svc()` also accepts `dns='cloudflare'` for DNS-01 TLS (wildcard certs) and `routes={'/rpc/*': ('ucall', 8545)}` for path-based multi-service routing. `caddy_api()` is a preset that adds rate limiting and body size cap.

## Secrets

```python
from dockeasy import env_set, env_get, secret_set, secret_get

env_set('VPS_IP', '1.2.3.4')            # stored in ~/.config/fastops/.env, mode 0600
secret_set('JWT_SCRT', 'abc123')        # OS keychain on macOS, env fallback on Linux
print(env_get('VPS_IP'))
print(secret_get('JWT_SCRT'))
```

## Compose

```python
from dockeasy import Compose

c = (Compose()
     .svc('web', build='.', ports={8000: 8000})
     .svc('db', image='postgres:16', env={'POSTGRES_DB': 'app'})
     .volume('pgdata'))
```

---

The only dependencies are fastcore and keyring.
