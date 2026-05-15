---
slug: cfeasy-cloudflare-tunnels
date: 2026-03-01
title: cfeasy: Cloudflare tunnels without the ID management
summary: A thin, idempotent wrapper around the Cloudflare Python SDK. Create DNS records and Zero Trust tunnels from Python. One call to set up a tunnel, wire the DNS, and get the token back.
visibility: public
author_name: Karthik
layout: newspaper
---

The Cloudflare API does everything you need. It is also the kind of API that makes you keep a notes file of IDs.

Zone ID. Account ID. Tunnel ID. Record ID. Every operation requires one of them. Create a DNS record manually once and it works. 
Write a script that runs twice and you have two identical records.

cfeasy is a wrapper that handles the ID bookkeeping and makes operations idempotent. The code is at [github.com/vedicreader/cfeasy](https://github.com/vedicreader/cfeasy).

## Setup

```python
from cfeasy import CF

c = CF()           # reads CLOUDFLARE_API_TOKEN from env
c.verify()         # lists zones and tunnels, confirms permissions
```

## Idempotent DNS

```python
c.upsert_record('myapp.com', 'api', '1.2.3.4', type='A', proxied=True)
```

`upsert_record` checks whether the record already exists with the same content before creating anything. If it matches, it skips. If there is a conflicting record with different content, it deletes the old one and creates the new one. Running it three times produces the same result as running it once.

```col                                                                                                                                                                                                                             
``` 
## Tunnel setup in one call

```python
tunnel_id, token = c.setup_tunnel('myapp.com', name='myapp')
```

`setup_tunnel` creates the tunnel if it does not exist, or reuses an existing one with the same name. It then creates a CNAME record pointing `myapp.com` at the tunnel's Cloudflare address. It returns the tunnel ID and the token string you pass to `cloudflared`.

The Compose service is then:

```yaml
cloudflared:
  image: cloudflare/cloudflared
  command: tunnel run
  environment:
    - CF_TUNNEL_TOKEN=${CF_TUNNEL_TOKEN}
```

No inbound firewall rules. No SSL configuration. The tunnel handles it.

## What it replaces

Without cfeasy, the same operation requires: fetch zone ID, fetch account ID, create tunnel, copy tunnel ID, construct CNAME target (`<tid>.cfargotunnel.com`), create DNS record. Each step is a separate API call with IDs threaded through.

With cfeasy, it is one call. If you run it again, it does nothing.

---

The implementation is a thin layer over the official cloudflare-python SDK. All validation is delegated to the SDK. cfeasy adds only idempotency and the convenience wrappers — it does not reinvent auth or request handling.
