# opstty/containers

Container images for Kubernetes tooling, published to [GitHub Container Registry](https://github.com/orgs/opstty/packages). All images live under the [`opstty/`](./opstty/) directory.

## Images

| Image | Description |
|-------|-------------|
| [trino-password-authentication](./opstty/trino-password-authentication/) | Reads a JSON password file, bcrypt-hashes passwords, and writes htpasswd format for Trino |
| [trino-register-table](./opstty/trino-register-table/) | Registers Delta Lake tables in Trino via Trino + Postgres (Hive Metastore) connections |
| [trino-superset-syncer](./opstty/trino-superset-syncer/) | Syncs Trino access control rules and catalogs into Apache Superset |

## Usage

```bash
docker pull ghcr.io/opstty/trino-password-authentication:latest
docker pull ghcr.io/opstty/trino-register-table:latest
docker pull ghcr.io/opstty/trino-superset-syncer:latest
```

### trino-password-authentication

Converts a JSON password map into a bcrypt-hashed htpasswd file for Trino's file-based password authentication.

```bash
docker run --rm \
  -v /path/to/password.json:/tmp/password.db \
  -v /path/to/output:/etc/trino/auth/password \
  ghcr.io/opstty/trino-password-authentication:latest
```

### trino-register-table

Registers catalogs and Delta Lake tables in Trino, and inserts catalog metadata into the Hive Metastore PostgreSQL database.

```bash
docker run --rm \
  -e TRINO_HOST=trino.example.com \
  -e TRINO_PASSWORD=secret \
  -e POSTGRES_HOST=postgres.example.com \
  -e POSTGRES_PASSWORD=secret \
  -v /path/to/register_table.json:/etc/trino/register/register_table.json \
  ghcr.io/opstty/trino-register-table:latest
```

### trino-superset-syncer

Syncs Trino databases and access control roles into Apache Superset via its REST API.

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

## Release

Push to `master` → GitHub Actions builds changed images and pushes to `ghcr.io/opstty/` with the `latest` tag.

To publish a versioned release, create a git tag matching `<image-name>-<version>`:

```bash
git tag trino-register-table-0.1.0
git push origin trino-register-table-0.1.0
```

This builds and pushes both `ghcr.io/opstty/trino-register-table:0.1.0` and `ghcr.io/opstty/trino-register-table:latest`.

## License

Apache 2.0
