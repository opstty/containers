# PROJECT KNOWLEDGE BASE

**Branch:** master

## OVERVIEW
Multi-container image repository for Kubernetes tooling, published to GitHub Container Registry (`ghcr.io/opstty/`). All images live under `opstty/`. Follows Bitnami's containers repo layout.

## STRUCTURE
```
containers/
├── opstty/                                  # All images live here
│   ├── trino-password-authentication/       # Bcrypt htpasswd generator for Trino
│   ├── trino-register-table/                # Delta Lake table registration tool
│   └── trino-superset-syncer/               # Trino → Superset access control sync
├── README.md                                # Repo-level README (image table, usage)
└── .github/workflows/
    └── build.yaml                           # CI: detect changes → build → push to ghcr.io
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Add a new image | `opstty/<image-name>/` | Dockerfile + source + requirements.txt |
| CI pipeline | `.github/workflows/build.yaml` | Matrix build, change detection, GHCR push |
| Image usage docs | `README.md` | Pull commands, env vars, volume mounts |

## IMAGES

### trino-password-authentication
- **Purpose**: Reads a JSON password map, bcrypt-hashes passwords, writes htpasswd format for Trino file-based auth.
- **Base**: `python:3.14-slim`
- **Entrypoint**: `python password.py`
- **Config via env**: `INPUT_PASSWORD_FILE`, `OUTPUT_PASSWORD_FILE`, `BCRYPT_ROUNDS`
- **Registry**: `ghcr.io/opstty/trino-password-authentication`

### trino-register-table
- **Purpose**: Registers Delta Lake catalogs/schemas/tables in Trino and inserts catalog metadata into Hive Metastore PostgreSQL.
- **Base**: `python:3.14-slim`
- **Entrypoint**: `python register_table.py`
- **Config via env**: `TRINO_HOST`, `TRINO_PORT`, `TRINO_USER`, `TRINO_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `SSL_CERT_PATH`, `JSON_FILE`
- **Registry**: `ghcr.io/opstty/trino-register-table`

### trino-superset-syncer
- **Purpose**: Syncs Trino databases and access control roles into Apache Superset via its REST API.
- **Base**: `python:3.14-slim`
- **Entrypoint**: `python syncer.py`
- **Config via env**: `SUPERSET_URL`, `SUPERSET_USERNAME`, `SUPERSET_PASSWORD`, `TRINO_HOST`, `TRINO_PORT`, `RULES_FILE`, `PASSWORD_FILE`, `ROLES_FILE`, `SSL_CERT_PATH`
- **Registry**: `ghcr.io/opstty/trino-superset-syncer`

## CONVENTIONS
- **Directory layout**: `opstty/<image-name>/` — each image is self-contained with Dockerfile, source, and requirements.
- **Base image**: All images use `python:3.14-slim` from public Docker Hub.
- **Env config**: All runtime configuration via environment variables — no hardcoded paths or credentials.
- **Entrypoint**: `CMD ["python", "<script>.py"]` — single script per image.
- **Branch**: `master` (not `main`).
- **Registry**: `ghcr.io/opstty/<image-name>`.

## ANTI-PATTERNS (THIS PROJECT)
- **DO NOT** use private registry base images — always use public Docker Hub.
- **DO NOT** hardcode credentials, hostnames, or paths — use environment variables.
- **DO NOT** push directly to master without testing the Docker build locally first.

## CI/CD
- **Trigger**: Push to `master` (path filter: `opstty/**`) or tag matching `*-[0-9]*`.
- **Change detection**: Diffs `HEAD~1..HEAD` under `opstty/`, extracts changed image names.
- **Tag-based release**: Tag `<image-name>-<version>` (e.g. `trino-register-table-0.1.0`) builds and pushes both `:<version>` and `:latest`.
- **Manual dispatch**: `workflow_dispatch` with `image` input for ad-hoc builds.
- **Registry auth**: `GITHUB_TOKEN` → `ghcr.io` (no external secrets needed).

## COMMANDS
```bash
# Build locally
docker build -t trino-register-table opstty/trino-register-table/

# Run locally
docker run --rm -e TRINO_HOST=localhost ghcr.io/opstty/trino-register-table:latest

# Tag a release
git tag trino-register-table-0.1.0
git push origin trino-register-table-0.1.0
```

## NOTES
- All three images are Python-based single-script tools designed to run as Kubernetes init containers or Jobs.
- These images are used by the `opstty/trino` Helm chart (in the sibling `charts` repo) for register-table and superset-syncer Jobs.
- The `trino-password-authentication` image is used as an init container on the Trino coordinator pod.
