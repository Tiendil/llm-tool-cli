### Migration

- Replace `Result[T, EnvironmentErrors]` annotations with `Result[T]`. Failures always carry `EnvironmentErrors`; `Err`, `UnwrapError`, and `map_err` no longer accept arbitrary error payloads.
- Configuration operations now return `Result[T]`; handle or propagate environment-error values instead of catching configuration exceptions. Configuration error models accept keyword fields, expose formatted text through `format_message()`, and retain original exceptions through `cause`.
- Replace imports of `core.errors.Error` with `InternalError`, `config.errors.Error` with `EnvironmentError`, and `ErrorsList` with `EnvironmentErrors`. Internal exceptions carry messages and details; diagnostic codes and records belong to environment errors.
- Result exceptions expose payloads through `details` instead of `arguments` and use the shared `InternalError` message and string representation. Unwrap exceptions inherit directly from `InternalError`; the intermediate `ResultError` base is removed.

### Changes

- Add `paths.project_path_id_from_filesystem` to resolve a supplied filesystem root and path, enforce containment, and return a canonical identifier with shared failure diagnostics.
- Add `paths.project_path_id_from_resolved` to convert a path already resolved and contained under its project root into a canonical identifier without filesystem access or repeated validation.
- Add `paths.resolve_root_anchored_path` to resolve `@/` identifiers under an explicit resolved project root, preserving lexical normalization, symlink containment, and shared failure diagnostics.
- Add `paths.resolve_inside_project` and `ResolvedProjectPath` for symlink-aware project containment with shared invalid-path and filesystem-resolution diagnostics.
- Add `paths.resolve_project_root` and `ProjectRootPath` for filesystem root resolution, returning shared `path_resolution_failed` diagnostics with original causes on resolution failure.
- Add `Result.is_err(error_type)` for selective recovery when every diagnostic matches an environment-error type, while preserving failure checks without an argument.
- Add shared lexical `@/` path normalization through `paths.normalize_project_path_id`, with `ProjectPathId` values and structured `invalid_project_path` failures.
- Prepared the empty Python package, development containers, quality checks, CI, release helpers, Donna and Depmesh integrations, and base specifications.
- Add Tomli as the shared TOML 1.1 parsing dependency.
- Add Pydantic as a runtime dependency and `config.load_config(path, config_class)` to read TOML into caller-owned models with shared validation failures.
- Add configuration discovery, explicit path resolution, TOML reading, and exclusive starter creation, with shared error bases in `core.errors` and configuration-specific environment failures in `config.errors`.
- Add `config.locate_config` for explicit-path selection or nearest-file discovery, with a shared `config_not_found` failure; explicit path resolution now expands home markers.
- Share internal exception messages and shallow-copied debugging context through `core.errors.InternalError`; configuration environment errors expose diagnostic text as `reason`.
- Add `Result[T]`, `Ok`, `Err`, and `unwrap_to_error` in `core.result`, with a fixed environment-error list and generic success values, preserving error propagation and unexpected exceptions.
- Add a shared Pydantic `EnvironmentError` model for expected operational failures, with typed context, message templates, corrective guidance, and native diagnostic records. Keep `InternalError` for internal and technical exceptions in a separate hierarchy within the same modules.
- Add `core.entities.BaseEntity` with common validation settings, deep copying with trusted changes, and JSON helpers; `EnvironmentError` inherits these common conventions, including stripping surrounding string whitespace.
- Add `core.errors.EnvironmentErrorsProxy` to carry environment errors through callbacks and recover the original list at the caller's result boundary.
