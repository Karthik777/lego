---
slug: gheasy-github-workflows
date: 2026-05-10
title: gheasy: GitHub Actions in Python
summary: A fluent DSL for GitHub Actions workflows. Pre-built jobs for uv test, lint, and PyPI publish. Secret routing from env_schema. Config-driven deployment pipelines.
visibility: public
author_name: Karthik
---

gheasy is a Python DSL that generates the YAML. The code is at [github.com/vedicreader/gheasy](https://github.com/vedicreader/gheasy).

## Workflow builder

```python
from gheasy.workflow import Workflow

wfb = Workflow("ci")
wfb.on.push(branches=["main"]).pull_request()
wfb.uv_lint_job()
wfb.uv_test_job(needs="lint")
wfb.uv_pypi_job(needs="test")
print(wfb.build().to_yaml())
```

`uv_lint_job`, `uv_test_job`, and `uv_pypi_job` are pre-built: checkout, setup-uv, install, run. 

For custom steps, the DSL goes lower:

```python
wfb.job("deploy").needs("test").runs_on("ubuntu-latest")\
    .checkout().end_step()\
    .setup_uv().end_step()\
    .step("Deploy").run("fly deploy --remote-only").end_job()
```

## Secrets and variables

`GheasyConfig` holds an `env_schema` that determines how each key is handled. `None` means it is a secret and has no default. 
A string means it is a variable with a default value.

```python
from gheasy.core import GheasyConfig, gh_push_env

cfg = GheasyConfig(app='myapp', env_schema={
    'PORT': '5001',       # variable — has a default
    'DOMAIN': 'http://localhost:5001',
    'JWT_SCRT': None,     # secret — no default
    'RESEND_API_KEY': None,
})
cfg.save()

import os
gh_push_env(dict(os.environ))  # None-schema → gh secret set, string-schema → gh variable set
```

Or push a `.env` file without a schema:

```python
from gheasy.core import gh_secrets_from_file
gh_secrets_from_file('.env')
```

## Full project setup

`gh_setup` writes the config, generates the workflow YAML, and installs the pre-commit hook in one call:

```python
from gheasy.core import gh_setup

gh_setup('myapp', '1.2.3.4', 'myapp.com', deploy_cmd='./deploy.sh')
```

That creates `.gheasy/config.json`, writes `.github/workflows/gheasy.yml`, and installs `uv run nbdev-prepare` as the pre-commit hook.

## Repo health

`gh_check` audits the local repo and, with a token, the remote. `gh_apply` runs the fixes that can be automated.

```python
from gheasy.core import gh_check, gh_apply

findings = gh_check(path='.')
gh_apply(findings)
```

Checks cover: pre-commit hook present, `.gitattributes` LFS block, pyproject.toml on hatchling, dependabot config, and repo topics.

---

The generated YAML is written to `.github/workflows/gheasy.yml` with a `# Managed by gheasy — do not edit directly` header. 
Edit the config, re-run `gh_workflow()`, the file regenerates.