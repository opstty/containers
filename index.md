# opstty/containers

Container images for Kubernetes tooling, published to [GitHub Container Registry](https://github.com/orgs/opstty/packages).

## Pull images

```bash
docker pull ghcr.io/opstty/<image-name>:latest
```

## Images

| Image | Description |
|-------|-------------|
| [trino-password-authentication](images/trino-password-authentication/) | Bcrypt htpasswd generator for Trino file-based auth |
| [trino-register-table](images/trino-register-table/) | Delta Lake table registration via Trino + Postgres |
| [trino-superset-syncer](images/trino-superset-syncer/) | Trino access control sync into Apache Superset |

Click an image name for usage details and environment variable reference.

## Release

Push to `master` → GitHub Actions builds changed images and pushes to `ghcr.io/opstty/`.

For versioned releases, tag with `<image-name>-<version>`:

```bash
git tag trino-register-table-0.1.0
git push origin trino-register-table-0.1.0
```

## Source

Source code and full documentation: [github.com/opstty/containers](https://github.com/opstty/containers)
