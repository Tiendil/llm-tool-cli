### Changes

- Prepared the empty Python package, development containers, quality checks, CI, release helpers, Donna and Depmesh integrations, and base specifications.
- Add Tomli as the shared TOML 1.1 parsing dependency.
- Add configuration discovery, explicit path resolution, TOML reading, and exclusive starter creation, with shared exceptions in `core.errors` and configuration-specific failures in `config.errors`.
- Share error messages, codes, shallow-copied context, and diagnostic records through `core.errors.Error`; configuration errors expose their original diagnostic text as `reason`.
