# cfeasy

cfeasy is a thin, idempotent wrapper around the Cloudflare Python SDK. It handles DNS records and Zero Trust tunnels without ID bookkeeping.

## Setup

```python
from cfeasy import CF

c = CF()       # reads CLOUDFLARE_API_TOKEN from env
c.verify()     # lists zones and tunnels, confirms permissions
```

## Idempotent DNS

```python
c.upsert_record('myapp.com', 'api', '1.2.3.4', type='A', proxied=True)
```

`upsert_record` checks whether the record already exists with the same content. If it matches, skips. If there is a conflicting record with different content, deletes the old one and creates the new one. Idempotent — safe to run multiple times.

## Tunnel setup

```python
tunnel_id, token = c.setup_tunnel('myapp.com', name='myapp')
```

`setup_tunnel` creates the tunnel if it does not exist, or reuses an existing one with the same name. Creates a CNAME record pointing the domain at the tunnel's Cloudflare address. Returns the tunnel ID and the token string you pass to `cloudflared`.

The Compose service:

```yaml
cloudflared:
  image: cloudflare/cloudflared
  command: tunnel run
  environment:
    - CF_TUNNEL_TOKEN=${CF_TUNNEL_TOKEN}
```

No inbound firewall rules. No SSL configuration. The tunnel handles it.

## Tunnel management

```python
tid  = c.tunnel_id('myapp')           # look up existing tunnel ID by name
c.delete_tunnel(tid)                   # delete tunnel by ID
```

## What it replaces

Without cfeasy, one tunnel setup requires: fetch zone ID, fetch account ID, create tunnel, copy tunnel ID, construct CNAME target (`<tid>.cfargotunnel.com`), create DNS record — each a separate API call with IDs threaded through. Run it twice and you get duplicate records.

With cfeasy: one call. The second run does nothing.

## Env vars

| var | description |
|---|---|
| `CLOUDFLARE_API_TOKEN` | API token with DNS edit + Zero Trust tunnel permissions |

Implementation is a thin layer over the official `cloudflare-python` SDK. All auth and request handling is delegated to the SDK.
