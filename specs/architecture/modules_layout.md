# Package architecture

## Goal of the document

This document describes the library's package layout, ownership boundaries, and relationship to consuming applications.

## Scope

This specification applies to Python package organization and dependency direction in LLM Tool CLI.
Individual capability behavior and development-tool implementation details are out of scope.

## Package layout

The library MUST be implemented as the `llm_tool_cli` Python package at the repository root.
The distribution name MUST be `llm-tool-cli`.

New modules MUST own a coherent responsibility required by an implemented capability.
Module structure SHOULD grow with actual behavior instead of preallocating a hierarchy for potential features.

## Consumer boundaries

The library owns reusable support for LLM-oriented CLI tools.
Each consumer owns its product-specific behavior and the composition of library capabilities into its application.

Library production code MUST NOT import Donna, Depmesh, or another consumer to implement shared behavior.
Donna and Depmesh integrations used to develop this repository are development tooling and MUST NOT become runtime dependencies through that integration.

**Example:** A library operation can accept application-owned data through a documented boundary without importing the application's workflow engine or dependency-discovery rules.

Shared capabilities MUST have explicit contracts that distinguish library responsibility from consumer responsibility.
Consumer-specific defaults and policies SHOULD remain with the consumer unless they are part of an intentionally adopted common contract.
Consumer-specific domain entities MUST remain with the consumer.

## Module responsibilities

Module names SHOULD describe the responsibility owned by the module so callers can identify where a concept belongs.
Module names SHOULD NOT mention an implementation technique unless that technique is the module's stable responsibility.

Module-specific entities and errors MUST belong to the module that owns their meaning.
Shared infrastructure MUST remain independent of the more specialized capabilities that use it.

Submodules MAY use these conventional names when their responsibilities exist:

- `entities` for module-owned typed values and data structures.
- `errors` for module-owned environment errors and internal exception types.
- `utils` for small technical helpers without a more specific owner.
- `tests` for colocated tests of module behavior.
- `tests.make` for reusable test-object constructors.
- `tests.helpers` for reusable test setup and behavior-verification helpers.

These submodules are optional unless the applicable architecture requires them for an implemented responsibility.
A module that defines expected fatal errors MUST provide an `errors` submodule as required by the error architecture.
An implementation MUST NOT introduce them solely for layout symmetry.

Generic result propagation, shared entity infrastructure, and shared error bases MUST belong to the core module.
The shared callback exception bridge MUST be publicly available as `llm_tool_cli.core.errors.EnvironmentErrorsProxy`.
The shared base entity MUST be publicly available as `llm_tool_cli.core.entities.BaseEntity`.
Capability errors MUST remain with their owning capabilities, and consumer presentation metadata MUST remain with the consumer.

The CLI module MUST own shared parsed global options and command-specific protocol defaults.
Its public `llm_tool_cli.cli.entities` submodule MUST provide `GlobalOptions`, inheriting the shared entity base and containing `protocol: Protocol | None` and `config_path: ProjectConfigPath | None`, both defaulting to `None`.
Its `protocol_for(command_name: str) -> Protocol` method MUST apply explicit protocol precedence and the shared command-default rule without storing derived state.
The parsed options entity MUST remain independent of CLI frameworks and application execution contexts.
The library MUST own the Typer runtime dependency and its supported version constraint for shared CLI context integration.
The public `llm_tool_cli.cli.options` submodule MUST provide the Typer `ConfigOption` annotation, parsing `--config` values into `ProjectConfigPath | None` without filesystem validation or resolution.
The same submodule MUST provide `protocol_option(*, tool_label: str) -> typer.models.OptionInfo` for use with a `Protocol | None` parameter annotation.
It MUST own protocol option aliases, help, value parsing, and invalid-value LLM error-cell emission with the supplied label before command execution.
The public `llm_tool_cli.cli.errors` submodule MUST own `InvalidProtocol`, carrying `reason` under a module-specific `EnvironmentError` root derived from the shared environment-error base.
Consumers MUST use these shared option definitions directly, own their remaining option parsing, and pass the invoked command name when selecting the effective protocol.

The paths module MUST own lexical project-path operations, filesystem resolution and containment, and conversion of resolved filesystem paths to canonical identifiers, together with their semantic types and environment errors.
Lexical operations MUST include canonical identifier checking, normalization, and component extraction.
Lexical normalization MUST remain independent of filesystem resolution.
Consumer-specific artifact or pattern semantics MUST remain consumer-owned.
Its public interfaces MUST include:

- `llm_tool_cli.paths.normalize_project_path_id` and `llm_tool_cli.paths.ProjectPathId`.
- `llm_tool_cli.paths.is_project_path_id`, accepting an arbitrary object and returning a boolean indicating whether it is already a canonical project-path identifier.
- `llm_tool_cli.paths.project_path_parts`, accepting an already canonical `ProjectPathId` and returning its components as a tuple of strings without repeated validation.
- `llm_tool_cli.paths.normalize_path`, accepting a textual identifier or filesystem input, a filesystem root, and an optional directory base named `cwd`, and returning a result containing a `ProjectPathId`.
- `llm_tool_cli.paths.resolve_project_path`, accepting a textual identifier or filesystem input, a filesystem root, and an `allow_absolute` option defaulting to `True`, and returning a result containing a `ResolvedProjectPath` with home expansion and project-root containment.
- `llm_tool_cli.paths.resolve_project_root` and `llm_tool_cli.paths.ProjectRootPath`.
- `llm_tool_cli.paths.resolve_inside_project` and `llm_tool_cli.paths.ResolvedProjectPath`.
- `llm_tool_cli.paths.UntrustedPath`, a semantic filesystem input type that establishes no resolution, existence, or project-containment guarantees and adds no runtime validation or conversion to the supplied `Path`.
- `llm_tool_cli.paths.PathInput`, a `NewType` over `pathlib.Path` marking a supplied filesystem path without resolution, existence, or containment guarantees.
- `llm_tool_cli.paths.ProjectConfigPath`, a `NewType` over `pathlib.Path` marking a configuration file path without requiring resolution or existence.
- `llm_tool_cli.paths.RelativeProjectPath`, a `NewType` over `pathlib.Path` marking a filesystem path interpreted relative to a project root, with validation policies owned by the consumer.
- `llm_tool_cli.paths.resolve_root_anchored_path`, accepting a textual identifier and an already resolved project root and returning a result containing the resolved project path.
- `llm_tool_cli.paths.project_path_id_from_resolved`, accepting a `ResolvedProjectPath` and the `ProjectRootPath` used for its containment check and returning a `ProjectPathId` directly.
- `llm_tool_cli.paths.project_path_id_from_filesystem`, accepting a filesystem path and filesystem root and returning a result containing a `ProjectPathId` after root resolution and containment enforcement.
- `llm_tool_cli.paths.errors.InvalidProjectPath` and `llm_tool_cli.paths.errors.PathResolutionFailed`.

These semantic path constructors MUST preserve the supplied `Path` without runtime validation or conversion.

The configuration module MUST own reusable configuration selection, loading, and creation, with behavior specified in `specs/behavior/config.md`.
Its public package interface MUST expose the operations implemented in `config.files`.
The configuration module MUST use the shared `ProjectConfigPath` for successful path values returned by `find_config`, `resolve_config_path`, `resolve_init_config_path`, and `locate_config`.
The target path parameter of `create_config` and `create_config_from_template` MUST also use `ProjectConfigPath`, without requiring resolution or existence.
The configuration module MUST also expose `llm_tool_cli.config.create_config_from_template(path, *, package, template) -> Result[None]`, implemented in `config.files`.
Packaged configuration templates MUST be located at `fixtures/<template>` within the caller-selected package.
The public `config.errors` submodule MUST own configuration environment errors, including `TemplateUnreadable` with target `path`, `template`, `reason`, and the private original exception cause.
The configuration module MUST expose `llm_tool_cli.config.resolve_init_config_path(filename: str, *, path: ProjectConfigPath | None = None, cwd: PathInput) -> Result[ProjectConfigPath]`, implemented in `config.files`.
Consumers MUST supply the default filename and invocation working directory.
Template contents, application schemas, and workspace construction and installation MUST remain consumer-owned.

The protocol module MUST own shared output protocols, cell construction, cell formatting and environment-error cell construction, JSON Lines serialization, and direct text writing.
Its public package interface MUST export `Protocol`, `to_jsonl`, and `write_output` from `llm_tool_cli.protocol`.
The protocol enum MUST live in `protocol.entities`, record serialization in `protocol.serialization`, and text writing in `protocol.streams`.
The protocol enum, record serialization, and text writing MUST depend only on the standard library.
The public `llm_tool_cli.protocol.output_cells.base` submodule MUST own the abstract `OutputCell` entity, its construction helpers and compact identifier, `MetaValue`, and `to_meta_value`.
It MUST also own `RenderContext`, containing the zero-based cell `index`, sequence `total`, and `tool_label` supplied to `OutputCell.render(context) -> bytes`.
The public `llm_tool_cli.protocol.logic_cells.base` submodule MUST provide the abstract `LogicCell` entity with `render(protocol) -> list[OutputCell]`, dispatching to the subclass's `render_human`, `render_llm`, or `render_automation` method.
Consumer-specific logic-cell subclasses MUST remain consumer-owned and hold the data needed for their projections.
The public `llm_tool_cli.protocol.logic_cells` package MUST expose `ContentCell`, a reusable logic cell holding prepared kind, media type, content, and metadata for a single output cell in each protocol.
Its `content` submodule MUST own the implementation.
The public `llm_tool_cli.protocol.logic_cells` package MUST also expose `EnvironmentErrorCell`, retaining a typed shared environment error until projection.
Its `environment_error` submodule MUST own error-cell content, corrective guidance, and metadata projection.
Logic cells MUST NOT own output identifiers, cached output cells, filesystem access, or output writing.
The public `llm_tool_cli.protocol.cell_shortcuts` submodule MUST provide `info`, `operation_succeeded`, and `operation_failed` for constructing common Markdown content logic cells without selecting an output-cell type.
It MUST also provide `skill(document: str, content: str) -> ContentCell` for constructing skill-document content logic cells.
Consumers MUST own document selection and supply already loaded text to the shortcut.
The same shortcut submodule MUST provide `version(value: str) -> ContentCell` for constructing metadata-only version cells.
Consumers MUST own package-version lookup and its failures.
Output cells, logic cells, and rendering contexts MUST inherit the shared `BaseEntity` from the core module.
The public `llm_tool_cli.protocol.output_cells` package MUST expose `HumanOutputCell`, `LLMOutputCell`, and `AutomationOutputCell` subclasses, whose `render` methods own complete protocol-specific cell formatting.
Its `human`, `llm`, and `automation` submodules MUST own the respective implementations.
Logic-cell projections MUST construct the corresponding concrete output-cell subtype before final rendering.
The public `llm_tool_cli.protocol.rendering.render_cells` function MUST accept an iterable of logic cells and explicit keyword-only `protocol` and `tool_label` arguments, project the logic cells for that protocol, calculate rendering contexts for the complete output-cell sequence, and concatenate rendered bytes.
The same public submodule MUST provide `write_cells(cells, *, protocol, tool_label, stderr=False) -> None`, composing sequence rendering, UTF-8 decoding, and shared text writing with caller-selected stream routing.
The rendering function MUST remain free of output side effects; the writing function MUST own emission without classifying cells or selecting exit statuses.
Output-cell type selection MUST belong to logic-cell projections rather than a separate selector exposed to application code.
The `llm_tool_cli.protocol.cell_shortcuts.environment_error(error)` helper MUST construct a shared `EnvironmentErrorCell`; it MUST NOT serialize the error, select a protocol, or render content.
The public `llm_tool_cli.protocol.errors` submodule MUST own the internal `ContentWithoutMediaType` and `UnsupportedFormatterMode` exceptions under a protocol-specific `InternalError` root derived from the shared internal-error base.
Consumer-specific cell kinds and content, domain record construction and rendering, journal models and formatting, consumer-specific CLI parsing, output routing, error classification, and exit selection MUST remain consumer-owned.

The skills module MUST own packaged skill-document loading independently of protocol cells.
Its public interface MUST provide `llm_tool_cli.skills.load_skill_text(package: str, document: str) -> Result[str]`, with implementation in `skills.fixtures`.
The public `llm_tool_cli.skills.errors` submodule MUST own `SkillUnreadable` under a module-specific `EnvironmentError` root derived from the shared environment-error base.
Application document enums, package selection, and Markdown resources MUST remain consumer-owned.

## Import boundaries

Public import boundaries MUST be explicit enough to distinguish supported interfaces from implementation details.
A public import boundary MAY be a package root or a declared public submodule.
Capability implementations MUST live in dedicated submodules.
Package initializers MUST be limited to package documentation, metadata, and import or re-export declarations.
Package initializers SHOULD re-export names only when doing so improves the supported interface and keeps ownership clear.
An initializer with no public names MAY remain empty.

Cross-module production dependencies MUST use declared public boundaries.
Implementation submodules inside the same owning module MAY import each other directly.
Production code MUST NOT import tests, test helpers, or repository development scripts.

Configured module boundaries MUST reflect implemented ownership and dependency direction.
New modules MUST update the architecture configuration when their addition changes a configured boundary.
