### Migration

- Recover result-unwrapping diagnostics through `UnwrapError.errors` instead of casting `details["error"]`. Payloads must be lists of environment errors; the accessor and `unwrap_to_error` now re-raise the original exception for missing or malformed payloads.

- Pass `paths.ProjectConfigPath` to `config.create_config` and `config.create_config_from_template`. The semantic type marks the configuration target without adding runtime validation or path resolution.

- `cell_shortcuts.environment_error(error)` now returns `protocol.logic_cells.EnvironmentErrorCell`, retaining the concrete error until projection. Access typed data through `cell.error`; obtain content and metadata from `cell.render(protocol)`. Error content now includes formatted corrective guidance when supplied.

- Import `ContentCell` from `protocol.logic_cells` and `LogicCell` from `protocol.logic_cells.base` instead of the removed `protocol.cells` module. Construct `ContentCell` for prepared content and metadata, or subclass `LogicCell` for protocol-specific projections. Construct concrete output cells only inside projections; `OutputCell`, `RenderContext`, `MetaValue`, and `to_meta_value` live in `protocol.output_cells.base`. The `protocol.modes.get_output_cell_type` selector is removed, and message shortcuts no longer accept `cell_type`.
- Replace the removed cell formatter family with `protocol.rendering.render_cells(logic_cells, protocol=..., tool_label=...)`. Construct shared diagnostics with `protocol.cell_shortcuts.environment_error(error)` and render them through that same logic-cell path. Output cells still support direct `render(RenderContext(...))` calls within output-layer integrations. The separate `render_error` function is removed.
- Pass `.` instead of an empty string to `paths.normalize_path` when referring to an explicit directory base below the project root; empty inputs now return `invalid_project_path`.
- Replace `Result[T, EnvironmentErrors]` annotations with `Result[T]`. Failures always carry `EnvironmentErrors`; `Err`, `UnwrapError`, and `map_err` no longer accept arbitrary error payloads.
- Configuration operations now return `Result[T]`; handle or propagate environment-error values instead of catching configuration exceptions. Configuration error models accept keyword fields, expose formatted text through `format_message()`, and retain original exceptions through `cause`.
- Replace imports of `core.errors.Error` with `InternalError`, `config.errors.Error` with `EnvironmentError`, and `ErrorsList` with `EnvironmentErrors`. Internal exceptions carry messages and details; diagnostic codes and records belong to environment errors.
- Result exceptions expose payloads through `details` instead of `arguments` and use the shared `InternalError` message and string representation. Unwrap exceptions inherit directly from `InternalError`; the intermediate `ResultError` base is removed.

### Changes

- Standardize the shared Typer runtime dependency on `~=0.25.1`.

- Add `cli.context.set_global_options` and `get_global_options` for shared Typer context storage, nested-command access, and invocation isolation. Add Typer as a runtime dependency.

- Add `config.resolve_init_config_path` for explicit or current-directory initialization targets, with semantic path types and shared resolution diagnostics, without upward discovery or file creation.

- Add shared `cli.entities.GlobalOptions` with a typed configuration path and protocol selection: explicit choices win, `skill` defaults to `llm`, and other commands default to `human`.

- Add typed `UnwrapError.errors` access with validation and original-list preservation, keeping `details["error"]` as the single payload storage location.

- Add `config.create_config_from_template(path, package=..., template=...)` to read a packaged UTF-8 starter and create it exclusively. Template read failures return `config.errors.TemplateUnreadable` with target `path`, `template`, `reason`, and private cause; file-creation diagnostics propagate unchanged.

- Add `skills.load_skill_text(package, document)` to read packaged UTF-8 Markdown, returning shared `SkillUnreadable` diagnostics with document, reason, and private cause on read failures.

- Add `protocol.cell_shortcuts.version(value)` to construct metadata-only version cells with shared `type` and `version` metadata.

- Add `protocol.rendering.write_cells` to render complete logic-cell batches, decode UTF-8, and write to the caller-selected standard stream.

- Default successful-operation cells to `type = operation_succeeded` metadata while preserving explicit caller metadata.

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
