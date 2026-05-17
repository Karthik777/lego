---
slug: vpseasy-vps-deployment
date: 2026-03-15
title: vpseasy: from zero to running container in one call
summary: End-to-end VPS lifecycle in Python. Generate cloud-init, provision Hetzner servers, deploy with Docker Compose. The same cloud-init YAML works in local Multipass VMs and production. Idempotent.
visibility: public
author_name: Karthik
---

vpseasy bundles all steps you need to deploy apps to a production server. The code is at [github.com/vedicreader/vpseasy](https://github.com/vedicreader/vpseasy).

## Cloud-init is the centre

Every provisioning decision lives in a cloud-init YAML file. vpseasy generates two variants: one for local Multipass VMs, one for production Hetzner servers. 
The local variant skips UFW and fail2ban and finishes faster. The production variant adds hardening. The application definition is the same in both.

```python
from vpseasy import multi_init, vps_init

# Local Multipass — fast, no UFW
local_cfg = multi_init('myapp', docker=True)

# Production Hetzner — hardened
prod_cfg = vps_init('myapp', docker=True)
```

## Local first

```python
from vpseasy import Multipass, deploy_mp

mp = Multipass()
mp.launch('myapp', image='24.04', cpus=2, memory='2G', cloud_init=local_cfg)

deploy_mp('myapp', src='.', path='/srv/app')
```

`deploy_mp` rsyncs your code into the VM and runs `docker compose up`. You can test the exact cloud-init that will run in production, locally, before touching a server.

## Production deploy

```python
from vpseasy import hetzner_deploy

hetzner_deploy('myapp', src='.')
```

This provisions the server if it does not exist, waits for cloud-init to complete, rsyncs, and deploys. Run it again and it just rsyncs and restarts the containers.

## Caddy and tunnels

```python
from vpseasy import caddy_stack
from dockeasy import fasthtml_app

compose = caddy_stack('myapp.com', fasthtml_app(), vols=['/app/data'])
```

`caddy_stack` generates a Compose YAML with the app, a Caddy reverse proxy, and a Cloudflare tunnel. The app does not need a public IP. Certificates are automatic. The tunnel replaces inbound firewall rules.

## Claude Code skill

vpseasy ships a Claude Code skill. Agents working on deployment code get the API loaded automatically.

---

It uses dockeasy for Dockerfile generation and fastcloudinit for YAML templating. 
The Hetzner wrapper uses the hcloud Python SDK directly.