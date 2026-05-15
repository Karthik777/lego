---
slug: vedicreader-to-eight-packages
title: VedicReader and the packages it made necessary
summary: I built a website for Vedic texts. That required search, then code tooling, then deployment, then everything else. Seven packages later, here is lego.
visibility: public
author_name: Karthik
---

VedicReader started as a practical problem. I wanted a good interface for Vedic texts in Tamil, Sanskrit, and Malayalam, 
something I could use on a phone while reading. Nothing available did what I wanted, so I built it. 
The stack is FastHTML,MonsterUI,SQLite.

The first real problem was search. The texts are long, the queries are specific, and standard FTS5 was not good enough on its own. 
So litesearch happened: hybrid search over SQLite using FTS5 and vector similarity with reciprocal rank fusion reranking. 
It is the foundational package. Both kosha and lego depend on it.

Kosha came from a different problem. I was using Claude to work on VedicReader and kept spending the first ten minutes 
of every session re-explaining the codebase. Kosha indexes the repo and installed packages so an LLM session starts with
relevant code already surfaced. It uses litesearch as its search backend.

Deployment was manual for too long. I was SSH-ing into a Hetzner VPS, running commands by hand, forgetting steps.
Dockeasy handles docker, proxy, and docker compose management. Vpseasy handles Hetzner VPS management, 
building on top of dockeasy. Cfeasy handles Cloudflare: DNS records, tunnels, access rules.
Gheasy handles the git side: branch management, PR workflows, the repetitive parts of working across several repositories at once.

## The pattern

Each package is the thing I would otherwise do by hand or copy-paste. The discipline is keeping it small enough that I will actually maintain it. litesearch is around 600 lines. kosha is 800. lego's core is under 500. When a file gets long enough that I cannot hold it in my head, I split it.

Writing code is my happy place. Not the part where it ships, not the part where it scales. The actual writing.
These packages are shaped by an obsession over what code should look like. I like the fastaistyle of code: small functions, clear names, no nesting, no classes unless they are really needed.

The test is whether I like looking at it. Most of these pass. A few have not and got refactored. 

Lego wraps the infrastructure every VedicReader-like project needs before you can write the actual thing: auth, caching, backups, theme switching. 
This blog, on [sankalpa.sh](https://sankalpa.sh), runs on lego. The stack is the same one VedicReader runs on.
