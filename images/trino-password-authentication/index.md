---
layout: default
title: trino-password-authentication
---

# trino-password-authentication

Reads a JSON password map, bcrypt-hashes each password, and writes an htpasswd file for [Trino's file-based password authentication](https://trino.io/docs/current/security/password-file.html).

## Pull

```bash
docker pull ghcr.io/opstty/trino-password-authentication:latest
```

## Usage

```bash
docker run --rm \
  -v /path/to/password.json:/tmp/password.db \
  -v /path/to/output:/etc/trino/auth/password \
  ghcr.io/opstty/trino-password-authentication:latest
```

### Input format

The input file is a JSON object mapping usernames to plaintext passwords:

```json
{
  "admin": "s3cret",
  "analyst": "p@ssw0rd"
}
```

### Output format

Standard htpasswd with bcrypt hashes:

```
admin:$2b$10$...
analyst:$2b$10$...
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `INPUT_PASSWORD_FILE` | Path to the source JSON password file | `/tmp/password.db` |
| `OUTPUT_PASSWORD_FILE` | Path to write the htpasswd output | `/etc/trino/auth/password/password.db` |
| `BCRYPT_ROUNDS` | Bcrypt cost factor | `10` |

## Kubernetes Usage

Typically used as an init container on the Trino coordinator pod to generate the password file from a Kubernetes Secret before Trino starts.

## Source

[github.com/opstty/containers](https://github.com/opstty/containers/tree/master/opstty/trino-password-authentication)
