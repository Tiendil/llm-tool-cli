### Migration

- `cell_shortcuts.environment_error(error)` now returns `protocol.logic_cells.EnvironmentErrorCell`, retaining the concrete error until projection. Access typed data through `cell.error`; obtain content and metadata from `cell.render(protocol)`. Error content now includes formatted corrective guidance when supplied.

- Import `ContentCell` from `protocol.logic_cells` and `LogicCell` from `protocol.logic_cells.base` instead of the removed `protocol.cells` module. Construct `ContentCell` for prepared content and metadata, or subclass `LogicCell` for protocol-specific projections. Construct concrete output cells only inside projections; `OutputCell`, `RenderContext`, `MetaValue`, and `to_meta_value` live in `protocol.output_cells.base`. The `protocol.modes.get_output_cell_type` selector is removed, and message shortcuts no longer accept `cell_type`.
- Replace the removed cell formatter family with `protocol.rendering.render_cells(logic_cells, protocol=..., tool_label=...)`. Construct shared diagnostics with `protocol.cell_shortcuts.environment_error(error)` and render them through that same logic-cell path. Output cells still support direct `render(RenderContext(...))` calls within output-layer integrations. The separate `render_error` function is removed.
- Pass `.` instead of an empty string to `paths.normalize_path` when referring to an explicit directory base below the project root; empty inputs now return `invalid_project_path`.
- Replace `Result[T, EnvironmentErrors]` annotations with `Result[T]`. Failures always carry `EnvironmentErrors`; `Err`, `UnwrapError`, and `map_err` no longer accept arbitrary error payloads.
- Configuration operations now return `Result[T]`; handle or propagate environment-error values instead of catching configuration exceptions. Configuration error models accept keyword fields, expose formatted text through `format_message()`, and retain original exceptions through `cause`.
- Replace imports of `core.errors.Error` with `InternalError`, `config.errors.Error` with `EnvironmentError`, and `ErrorsList` with `EnvironmentErrors`. Internal exceptions carry messages and details; diagnostic codes and records belong to environment errors.
- Result exceptions expose payloads through `details` instead of `arguments` and use the shared `InternalError` message and string representation. Unwrap exceptions inherit directly from `InternalError`; the intermediate `ResultError` base is removed.

### Changes

- Add `protocol.cell_shortcuts.skill(document, content)` to construct shared Markdown skill cells with `document` and `type = skill` metadata.

- Add a shared typed `EnvironmentErrorCell` with deferred projection of the native diagnostic record and corrective guidance into all output protocols.

- Add shared `ContentCell` logic cells and make sequence rendering project and flatten logic cells before calculating output positions. Message shortcuts return logic cells; output identifiers are created during projection.

- Render environment errors as ordinary cells with Markdown message content, native code and diagnostic metadata, generated identifiers, and standard protocol framing. Automation messages move from `message` to `content`; diagnostic context follows ordinary cell metadata conversion.

- Let protocol-specific output cells own final rendering, with a shared context supplying position, sequence size, and tool label. Preserve cell layouts and JSON field precedence; journal formatting remains consumer-owned.
- Add `protocol.cell_shortcuts` for constructing informational, successful-operation, and failed-operation Markdown cells through the shared cell model.
- Add `protocol.output_cells.base.OutputCell`, metadata helpers, and the shared `ContentWithoutMediaType` internal exception, preserving cell construction and compact UUID identifiers.
- Organize shared logic cells in `protocol.logic_cells`, with `LogicCell` in `base` and `ContentCell` in `content`, alongside the existing `protocol.output_cells` package.
- Add `protocol.logic_cells.base.LogicCell` for consumer data with separate human, LLM, and automation projections into ordered output cells.
- Add `protocol.Protocol`, `protocol.to_jsonl`, and `protocol.write_output` for shared protocol names, compact Unicode JSON Lines, and direct text output without automatic newlines or flushing.
- Reject empty inputs in shared mixed path normalization with an empty diagnostic `path`, preserving root-resolution failure precedence.
- Add `paths.UntrustedPath` as a shared semantic type for filesystem inputs without established resolution or containment guarantees, preserving ordinary `Path` runtime behavior.
- Add `paths.resolve_project_path` for resolving identifier or filesystem inputs below a project root, with home expansion, optional rejection of absolute inputs, and shared failure diagnostics.
- Add `paths.normalize_path` for mixed identifier and filesystem inputs, with explicit directory bases, home expansion, shared containment, and structured resolution failures.
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
