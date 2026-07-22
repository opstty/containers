---
layout: default
title: trino-register-table
---

# trino-register-table

Registers Delta Lake catalogs, schemas, and tables in Trino, and inserts catalog metadata into the Hive Metastore PostgreSQL database.

## Pull

```bash
docker pull ghcr.io/opstty/trino-register-table:latest
```

## Usage

```bash
docker run --rm \
  -e TRINO_HOST=trino.example.com \
  -e TRINO_PASSWORD=secret \
  -e POSTGRES_HOST=postgres.example.com \
  -e POSTGRES_PASSWORD=secret \
  -v /path/to/register_table.json:/etc/trino/register/register_table.json \
  ghcr.io/opstty/trino-register-table:latest
```

### Input format

A JSON file describing catalogs, schemas, and table locations:

```json
{
  "catalogs": {
    "my_catalog": {
      "schemas": {
        "my_schema": {
          "tables": {
            "my_table": {
              "location": "gs://bucket/path/to/table"
            }
          }
        }
      }
    }
  }
}
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `TRINO_HOST` | Trino coordinator hostname | *(required)* |
| `TRINO_PORT` | Trino coordinator port | `8443` |
| `TRINO_USER` | Trino username | `admin` |
| `TRINO_PASSWORD` | Trino password (plain string or JSON map) | *(required)* |
| `SSL_CERT_PATH` | Path to CA cert for Trino TLS | *(optional)* |
| `JSON_FILE` | Path to the registration JSON | `/etc/trino/register/register_table.json` |
| `POSTGRES_HOST` | Hive Metastore PostgreSQL host | *(required)* |
| `POSTGRES_PORT` | PostgreSQL port | `5432` |
| `POSTGRES_USER` | PostgreSQL username | `postgres` |
| `POSTGRES_PASSWORD` | PostgreSQL password | *(required)* |
| `POSTGRES_DB` | PostgreSQL database name | `metastore` |
| `POSTGRES_SSL_MODE` | PostgreSQL SSL mode | `require` |
| `PG_CA_CERT` | Path to PostgreSQL CA certificate | *(optional)* |
| `LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR) | `INFO` |

## Kubernetes Usage

Designed to run as a Helm post-install/post-upgrade Job in the `opstty/trino` chart.

## Source

[github.com/opstty/containers](https://github.com/opstty/containers/tree/master/opstty/trino-register-table)
