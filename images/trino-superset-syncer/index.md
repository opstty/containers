---
layout: default
title: trino-superset-syncer
---

# trino-superset-syncer

Syncs Trino databases and access control roles into Apache Superset via its REST API. Reads Trino access rules, a password file, and a roles definition to automatically create databases and configure role-based access in Superset.

## Pull

```bash
docker pull ghcr.io/opstty/trino-superset-syncer:latest
```

## Usage

```bash
docker run --rm \
  -e SUPERSET_URL=https://superset.example.com \
  -e SUPERSET_PASSWORD=admin \
  -e TRINO_HOST=trino.example.com \
  -v /path/to/rules.json:/etc/trino/access-control/rules.json \
  -v /path/to/password.db:/tmp/password.db \
  -v /path/to/roles.json:/etc/superset/access-control/roles.json \
  ghcr.io/opstty/trino-superset-syncer:latest
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SUPERSET_URL` | Superset base URL | *(required)* |
| `SUPERSET_USERNAME` | Superset admin username | `admin` |
| `SUPERSET_PASSWORD` | Superset admin password | `admin` |
| `TRINO_HOST` | Trino coordinator hostname | *(required)* |
| `TRINO_PORT` | Trino coordinator port | `8443` |
| `SSL_CERT_PATH` | Path to CA cert for TLS | `/etc/superset/certificate-authority/root.ca` |
| `RULES_FILE` | Path to Trino access control rules JSON | `/etc/trino/access-control/rules.json` |
| `PASSWORD_FILE` | Path to JSON password map | `/tmp/password.db` |
| `ROLES_FILE` | Path to Superset roles definition JSON | `/etc/superset/access-control/roles.json` |
| `LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR) | `INFO` |

## What It Does

1. **Database sync**: Creates Trino databases in Superset from the access control rules catalog entries.
2. **Role sync**: Creates or updates Superset roles with resolved permission IDs based on the roles definition file.

## Kubernetes Usage

Designed to run as a Helm post-install/post-upgrade Job in the `opstty/trino` chart.

## Source

[github.com/opstty/containers](https://github.com/opstty/containers/tree/master/opstty/trino-superset-syncer)
