
### Migration

- Initialize identity with `initialize(name=ToolName("tool"))`, importing `ToolName` from `core.entities`; use `tool_name` in static settings and render contexts. Cell labels now derive from the validated name in uppercase.
- Tool names and standalone `PathSegment` values must contain lowercase ASCII letters and digits separated by single hyphens. Construction trims surrounding whitespace and rejects other spelling. Import `PathSegment` from `paths`.

### Changes

- Define the shared cache storage, ownership, coordination, and cleanup contract separately from consumer repository policy, with matching dependency-governance rules.
- Clarify specification ownership for storage locations and cache-clean output; document shared storage and coordination in the README contract and guide.
- Define explicit Tach layers with tests in `meta-tests`, replacing per-file exceptions and requiring declared dependencies between production modules.
- Keep cache cells within the `tool_cache` Tach boundary and use `filesystem_storage` for the cache/state layer above generic protocol support.
- Use the common context-initialization error for all conflicting static settings instead of a dedicated tool-name exception.
- Propagate original state-directory, path, and file-lock diagnostics through project coordination without project-specific error translation.
- Unify static identity, cache names, and state names through `core.entities.ToolName`, removing independent cell-label configuration and the cache-to-state identity dependency.
- Add generic `core.entities.Slug` validation, shared by `core.entities.ToolName` and `paths.entities.PathSegment`, keeping path semantics and path-specification governance within `paths`.
- Add `paths.PathSegment` with whitespace trimming and strict slug validation, reused by cache namespaces and cache directory names.
- Write `identity.toml` markers directly in cache storage and derive `CacheIdentity.digest` from the namespace and literal key independently of marker formatting.
- Verify cache ownership from parsed TOML identities, accepting equivalent formatting and field order during reuse and cleanup.
- Add `file_locks` with reusable native process-lock scopes, persistent coordination files, and typed acquisition diagnostics.
- Add `tool_cache.ToolCache` with namespaced storage, shared locking, ownership markers, and cleanup that preserves unrelated data.
- Add `tool_state.ToolStateDirectory` for per-user state discovery, contained paths, and named locks, with project coordination in `tool_state.project_locks` and independent cache discovery in `tool_cache.resolve_cache_root`.
- Add `register_cache_clean_command` to register one cleanup command on a consumer-supplied app, using a lazy cache factory, shared error handling, and cache result projections.
- Allow applications to scope initialization resources through configuration creation and output delivery, with shared failure handling.
- Add lexical joining and containment helpers for canonical project-path identifiers.
