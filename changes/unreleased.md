
Moved common storage and coordination functionality from `vcsinstall` into this library.

### Migration

- Replace `ToolLabel` with `ToolName` from `llm_tool_cli.core.entities`, and `initialize(label=...)` with `initialize(name=...)`.
- Rename `tool_label` to `tool_name` in static settings and render contexts.
- Supply `cache_dir` when constructing `RuntimeConfig` directly, using `CacheRootPath` from `llm_tool_cli.paths`. Shared

### Changes

- Added reusable process-lock scopes in `file_locks`.
- Added `ToolCache` with namespaced storage, coordinated access, and cleanup that preserves unrelated data.
- Added `ToolStateDirectory` for per-user state locations, contained paths, and named locks, plus project operation locking.
- Added the global `--cache-dir` option and `register_cache_clean_command` for registering a single cleanup command.
- Added `Slug` and `PathSegment` validation, with one `ToolName` shared by output, cache, and state.
- Added lexical `join_path` and `contains_path` helpers for canonical project-path identifiers.
- Added `operation_scope` to `register_init_command` to retain application resources through initialization and output delivery.
