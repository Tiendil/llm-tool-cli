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

Consumer domain and runtime modules MUST own assembly of command-facing domain results as logic cells or ordered collections of their subclasses.
Domain and runtime operations MAY submit those cells directly to the shared output binding.
The CLI MUST configure delivery without converting internal domain results into output payloads.
Consumer protocol modules MUST own domain-cell projections, while the shared protocol module owns the common cell interface and rendering infrastructure.
Constructing a logic cell from typed domain data MUST NOT be treated as protocol-specific rendering or require a dependency on consumer CLI code.

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

The public `llm_tool_cli.core.context` submodule MUST provide `ContextValue[T](name: str)` for independently managed typed bindings.
Its public operations MUST be:

- `get() -> T` for access to the current value.
- `is_set() -> bool` for checking whether a value is bound.
- `initialize(value: T) -> None` for initialization without reassignment.
- `scope(value: T)` returning a synchronous context manager that yields `None` and restores the preceding binding on exit.

The core error module MUST own `ContextValueNotSet` and `ContextValueAlreadySet`, both deriving from `InternalError` and identifying the binding through `details["name"]`.
The binding mechanism MUST remain independent of CLI frameworks and application-owned services.
Applications MUST own their binding instances, supplied objects, and setup boundaries; obtaining values through bindings MUST NOT prohibit explicit function arguments.

The public `llm_tool_cli.core.settings` submodule MUST expose frozen `StaticConfig` with `tool_label: ToolLabel`, `config_filename: ConfigFilename | None = None`, and `static_config: ContextValue[StaticConfig]`.
`ConfigFilename` MUST be a semantic string type owned by this submodule; applications using project setup MUST declare their default filename here instead of maintaining a competing constant.
Callers MUST read application identity through `settings.static_config.get().tool_label`.
Static configuration MUST preserve the label exactly, including whitespace and an empty string, and remain available before command-line parsing.
Its `initialize(*, label, config_filename=None)` boundary MUST accept repeated identical settings and retain the `ToolLabelAlreadyInitialized` diagnostic for conflicting labels.
Changing the filename of an initialized application MUST raise `ContextValueAlreadySet` for `static_config` and preserve the existing settings.
Access to unset static configuration MUST use the shared `ContextValueNotSet` diagnostic.

The configuration module MUST expose `llm_tool_cli.config.runtime.RuntimeConfig` and `runtime_config: ContextValue[RuntimeConfig]` independently of CLI frameworks.
`RuntimeConfig` MUST be frozen and contain the effective `protocol: Protocol`, without project fields or duplicated application identity.
The configuration module MUST expose `llm_tool_cli.config.project.ProjectConfig` and `project_config: ContextValue[ProjectConfig]` independently of CLI frameworks.
`ProjectConfig` MUST be frozen and require an absolute active `config_path: ProjectConfigPath`.
Its read-only `project_dir: ProjectRootPath` property MUST derive the root from that path's parent.
The configuration module MUST expose `load_project(config_class, *, cwd, path=None)` and `initialize_project(config_class, *, package, template, cwd, path=None)`, implemented in `config.project` and re-exported by `config`.
Both MUST return synchronous context managers yielding `Result[T]` for the caller-supplied Pydantic schema, performing preparation on entry and using the filename from static settings.
Loading MUST select an existing configuration; initialization MUST create a starter without upward discovery. Both MUST load and validate the selected file, construct complete project settings, bind them for the scope, and restore the preceding binding on exit.
Expected preparation failures MUST yield their unchanged error result without binding a project. Exceptions from the caller's scope body MUST propagate without being converted into preparation results.
Project setup without a configured static filename MUST raise `config.errors.ConfigFilenameNotSet`, deriving from a module-specific `InternalError` root.
Callers MUST retain the shared context around project-dependent execution and output; CLI callers MUST register it with the framework context's resource lifecycle.
Commands without a project MUST NOT establish a project binding.
Each configuration MUST be the single source of truth for its fields; consumer globals, workspace entities, and command contexts MUST NOT keep competing copies.
Application-specific configuration and compiled workspaces MUST remain consumer-owned and separate from shared settings.
The shared test-only `llm_tool_cli.config.tests.fixtures.runtime_settings` fixture MUST bind fresh runtime settings through a real scope and restore the preceding binding on exit.
The same module's `project_settings` fixture MUST independently scope a project rooted at the test's temporary directory, without loading configuration files.
Its `project_static_settings` fixture MUST scope application metadata for project-preparation tests.

The CLI module MUST own global-option parsing and command-specific protocol defaults.
The public `llm_tool_cli.cli.context.CommandContext(context: typer.Context)` class MUST create a runtime configuration with the effective protocol and bind it through the framework context's resource lifecycle.
It MUST read parsed root parameters from the framework, treating an unspecified protocol as LLM for the invoked command named `skill` and human otherwise.
Its `config_input` property MUST expose the unresolved optional CLI configuration path for the operation that selects or creates a configuration file.
Its `protocol` property MUST read the active runtime configuration without retaining a copy.
It MUST establish a fresh shared output scope through the framework context lifecycle.
Its `write_cells(cells: Iterable[LogicCell]) -> None` method MUST submit a materialized cell batch to the active emitter.
Consumer command contexts MAY inherit this implementation while retaining their own application settings, workspace construction, runtime setup, journal-cell construction, and cleanup.
Shared skill and version commands MUST use this context for protocol selection and cell writing.
The library MUST own the Typer runtime dependency and its supported version constraint for shared CLI context integration.
The public `llm_tool_cli.cli.application.create_app(*, help: str) -> typer.Typer` factory MUST own shared application construction, root option registration, help aliases, and completion-option availability.
The root callback MUST declare `ProtocolOption` and `ConfigOption`, retaining unspecified inputs as `None` in the framework parameters without a parallel global options binding.
The factory MUST return an ordinary Typer application; consumers MUST register application-specific commands themselves.
The public `llm_tool_cli.cli.commands.skills.register_skill_command(app, *, package: str, documents: type[StrEnum]) -> None` boundary MUST register the complete shared skill command using the supplied document enum and resource package.
The CLI module MUST compose shared skill loading, protocol selection, cell writing, and read-failure handling without depending on consumer command contexts.
The public `llm_tool_cli.cli.commands.version.register_version_command(app, *, distribution: str) -> None` boundary MUST register the complete shared version command using the supplied distribution name.
The CLI module MUST own installed package-version lookup, protocol selection, and version-cell emission without depending on consumer command contexts.
The public `llm_tool_cli.cli.entities` submodule MUST provide `ExitCode`, an `enum.IntEnum` with `success = 0`, `invalid_arguments = 1`, and `skill_unreadable = 3` for their respective shared CLI outcomes.
The enum MUST preserve the integer exit-status contract without replacing consumer-specific failure categories.
The public `llm_tool_cli.cli.options` submodule MUST provide the Typer `ConfigOption` annotation, parsing `--config` values into `ProjectConfigPath | None` without filesystem validation or resolution.
The same submodule MUST provide the Typer `ProtocolOption` annotation for `Protocol | None` values.
It MUST own protocol option aliases, help, value parsing, and invalid-value LLM error-cell emission with the initialized application label before command execution.
The public `llm_tool_cli.cli.errors` submodule MUST own `InvalidArguments`, carrying `reason` under a module-specific `EnvironmentError` root derived from the shared environment-error base.
Shared protocol parsing and consumer-owned validation reporting `invalid_arguments` MUST use this same diagnostic type directly, without local wrappers or duplicate error models.
The shared application factory MUST register these option definitions; consumers MUST own their remaining option parsing and use the shared command context to establish effective runtime settings and access unresolved configuration input.

The paths module MUST own lexical project-path operations, filesystem resolution and containment without symlink traversal below the resolved root, deterministic file enumeration, and conversion of resolved filesystem paths to canonical identifiers, together with their semantic types and environment errors.
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
- `llm_tool_cli.paths.PathInput`, a `NewType` over `pathlib.Path` marking a supplied filesystem path without resolution, existence, or containment guarantees.
- `llm_tool_cli.paths.ProjectConfigPath`, a `NewType` over `pathlib.Path` marking a configuration file path without requiring resolution or existence.
- `llm_tool_cli.paths.RelativeProjectPath`, a `NewType` over `pathlib.Path` marking a filesystem path interpreted relative to a project root, with validation policies owned by the consumer.
- `llm_tool_cli.paths.resolve_root_anchored_path`, accepting a textual identifier and an already resolved project root and returning a result containing the resolved project path.
- `llm_tool_cli.paths.project_path_id_from_resolved`, accepting a `ResolvedProjectPath` and the `ProjectRootPath` used for its containment check and returning a `ProjectPathId` directly.
- `llm_tool_cli.paths.project_path_id_from_filesystem`, accepting a filesystem path and filesystem root and returning a result containing a `ProjectPathId` after root resolution and containment enforcement.
- `llm_tool_cli.paths.errors.InvalidProjectPath` and `llm_tool_cli.paths.errors.PathResolutionFailed`.
- `llm_tool_cli.paths.FileGlobPattern`, a `NewType` over `str` owned by `paths.enumeration`, marking a supplied filesystem glob without validity or containment guarantees.
- `llm_tool_cli.paths.enumerate_files(root, pattern: FileGlobPattern = FileGlobPattern("**/*")) -> Result[list[ProjectPathId]]`, implemented in `paths.enumeration`, accepting a filesystem root and glob pattern and returning unique regular-file identifiers in path-component order.
- `llm_tool_cli.paths.errors.FilesUnreadable`, carrying `path`, `reason`, and a private exception cause for enumeration failures.

These semantic filesystem-path constructors MUST preserve the supplied `Path` without runtime validation or conversion.
The glob-pattern constructor MUST preserve the supplied string without validation; enumeration MUST retain responsibility for path normalization and filesystem checks.

The configuration module MUST own reusable configuration selection, loading, and creation, with behavior specified in `specs/behavior/config.md`.
Its public package interface MUST expose the operations implemented in `config.files`.
The configuration module MUST use the shared `ProjectConfigPath` for successful path values returned by `find_config`, `resolve_config_path`, `resolve_init_config_path`, `initialize_config`, and `locate_config`.
The target path parameter of `create_config` and `create_config_from_template` MUST also use `ProjectConfigPath`, without requiring resolution or existence.
The configuration module MUST also expose `llm_tool_cli.config.create_config_from_template(path, *, package, template) -> Result[None]`, implemented in `config.files`.
Packaged configuration templates MUST be located at `fixtures/<template>` within the caller-selected package.
The public `config.errors` submodule MUST own configuration environment errors, including `TemplateUnreadable` with target `path`, `template`, `reason`, and the private original exception cause.
The configuration module MUST expose `llm_tool_cli.config.resolve_init_config_path(filename: str, *, path: ProjectConfigPath | None = None, cwd: PathInput) -> Result[ProjectConfigPath]`, implemented in `config.files`.
Consumers MUST supply the default filename and invocation working directory.
The configuration module MUST expose `llm_tool_cli.config.initialize_config(filename: str, *, package: str, template: str, cwd: PathInput, path: ProjectConfigPath | None = None) -> Result[ProjectConfigPath]`, implemented in `config.files` by composing shared initialization target selection and template-based creation.
Template contents, application schemas, and application-specific workspace construction and installation MUST remain consumer-owned; shared project settings and their scopes MUST be managed by the shared project contexts.

The protocol module MUST own shared output protocols, cell construction, cell formatting and environment-error cell construction, and JSON Lines serialization.
Its public package interface MUST export `Protocol` and `to_jsonl` from `llm_tool_cli.protocol`.
The protocol enum MUST live in `protocol.entities` and record serialization in `protocol.serialization`.
The protocol enum and record serialization MUST depend only on the standard library.
The public `llm_tool_cli.protocol.output_cells.base` submodule MUST own the abstract `OutputCell` entity, its construction helpers and compact identifier, `MetaValue`, and `to_meta_value`.
It MUST also own `RenderContext`, containing the zero-based cell `index`, sequence `total`, and `tool_label` supplied to `OutputCell.render(context) -> bytes`.
The public `llm_tool_cli.protocol.logic_cells.base` submodule MUST provide the abstract `LogicCell` entity with `render(protocol) -> list[OutputCell]`, dispatching to the subclass's `render_human`, `render_llm`, or `render_automation` method.
Consumer-specific logic-cell subclasses MUST remain consumer-owned and hold the data needed for their projections.
The public `llm_tool_cli.protocol.logic_cells.uniform` submodule MUST provide `UniformCell`, a `LogicCell` specialization for one output cell with the same payload in every protocol.
Its protocol projection methods MUST pass the corresponding output-cell class to the abstract `_render(cell_type: type[OutputCell]) -> OutputCell` method and wrap the returned cell in a one-item list.
Shared content and environment-error cells MUST inherit this projection implementation; consumers MAY use it for their own uniform cells.
Cells with multiple outputs or different protocol payloads MUST retain their own projections through `LogicCell`.
The public `llm_tool_cli.protocol.logic_cells` package MUST expose `ContentCell`, a reusable logic cell holding prepared kind, media type, content, and metadata for a single output cell in each protocol.
Its `content` submodule MUST own the implementation.
The public `llm_tool_cli.protocol.logic_cells` package MUST also expose `EnvironmentErrorCell`, retaining a typed shared environment error until projection.
Its `environment_error` submodule MUST own error-cell content, corrective guidance, and metadata projection.
Logic cells MUST NOT own output identifiers, cached output cells, filesystem access, or output writing.
The public `llm_tool_cli.protocol.cell_shortcuts` submodule MUST provide `info`, `operation_succeeded`, and `operation_failed` for constructing common Markdown content logic cells without selecting an output-cell type.
It MUST provide `configuration_created(path: ProjectConfigPath) -> ContentCell` for constructing configuration-creation success cells, using the semantic path type from the paths module.
It MUST also provide `skill(document: str, content: str) -> ContentCell` for constructing skill-document content logic cells.
Callers MUST select the document and supply already loaded text to the shortcut.
The same shortcut submodule MUST provide `version(value: str) -> ContentCell` for constructing metadata-only version cells.
Package-version lookup and its failure policy MUST belong to the calling CLI boundary, independently of version-cell construction.
Output cells, logic cells, and rendering contexts MUST inherit the shared `BaseEntity` from the core module.
The public `llm_tool_cli.protocol.output_cells` package MUST expose `HumanOutputCell`, `LLMOutputCell`, and `AutomationOutputCell` subclasses, whose `render` methods own complete protocol-specific cell formatting.
Its `human`, `llm`, and `automation` submodules MUST own the respective implementations.
Logic-cell projections MUST construct the corresponding concrete output-cell subtype before final rendering.
The protocol module MUST leave batch-rendering orchestration and stream writing to the shared output emitter.
Individual logic-cell projections and output-cell formatting MUST remain free of output side effects.
Output-cell type selection MUST belong to logic-cell projections rather than a separate selector exposed to application code.
The `llm_tool_cli.protocol.cell_shortcuts.environment_error(error)` helper MUST construct a shared `EnvironmentErrorCell`; it MUST NOT serialize the error, select a protocol, or render content.
The public `llm_tool_cli.protocol.errors` submodule MUST own the internal `ContentWithoutMediaType` and `UnsupportedFormatterMode` exceptions under a protocol-specific `InternalError` root derived from the shared internal-error base.
Consumer-specific cell kinds, content, domain context, and projections MUST remain consumer-owned.
Shared output delivery and command error handling MUST remain independent of consumer implementations.

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

The public test-only `llm_tool_cli.protocol.tests.helpers.assert_error_cells(records, errors)` boundary MUST accept parsed automation records with identifiers and expected `EnvironmentErrors`.
It MUST own common error-cell assertions; callers MUST own output parsing and record filtering.
The same test-only module MUST provide `cell_payloads(records)`, accepting parsed automation records and returning payload copies without generated identifiers after validating those identifiers.
The error-cell assertion MUST reuse this helper.

Configured module boundaries MUST reflect implemented ownership and dependency direction.
New modules MUST update the architecture configuration when their addition changes a configured boundary.

## Output delivery

The public `llm_tool_cli.output` package MUST expose `OutputEmitter`, `StreamOutputEmitter`, and `output: ContextValue[OutputEmitter]`.
The interface MUST accept `emit(cells: list[LogicCell]) -> Result[None]`, `flush() -> None`, and `discard() -> None`.
`StreamOutputEmitter` MUST accept an optional keyword-only `stream: TextIO | None = None` during construction and deliver every cell to that stream, resolving `None` to current stdout at delivery time.
Stream selection MUST belong to emitter construction rather than individual submissions; the emitter MUST NOT close the supplied stream.
Discarding MUST remove pending ordinary results while retaining warnings for failure reporting.
Stream delivery MUST read the active runtime protocol when rendering and MUST NOT retain a competing protocol value.
The emitter MUST read `settings.static_config.get().tool_label` once per batch, project the logical cells for the active protocol, flatten their outputs in order, construct rendering contexts for the complete output-cell sequence, and concatenate rendered bytes.
It MUST decode the complete batch as UTF-8 before writing directly to its selected text stream and flushing it.
Its protected `_render(cells: list[LogicCell]) -> str` method MUST prepare complete batch text without writing output, allowing subclasses to override preparation while retaining `_write` stream selection, writing, and flushing.
The output module MAY depend on core, configuration, and protocol; those modules MUST NOT depend on output.

The public `output.journal` submodule MUST expose `JournalProcessor.process(cell: LogicCell) -> Result[None]`, `NoopJournalProcessor`, and `CommandJournalProcessor`.
The emitter MUST accept a processor during construction and default to the no-op processor.
The command processor MUST use the cell's explicitly serialized model fields, excluding delivery flags, for whole-argument substitution.
The output error module MUST own journal command configuration and execution failures.

The logic-cell base MUST own overridable `is_journal` and `is_warning` fields, defaulting to false and excluded from serialization.
The public `protocol.logic_cells.journal.JournalCell` MUST supply timestamp, actor, message, compact text projections, and structured automation output with a journal default.
Consumers MAY subclass it to add domain fields and customize text projections.
The public `protocol.logic_cells.warning.WarningCell` MUST provide warning metadata projections with a warning default.
Their output-cell implementations MUST belong to `protocol.output_cells`.
Cells and their projections MUST remain free of delivery side effects.

The public test-only `output.tests.helpers` boundary MAY provide a collecting emitter and warning-message inspection for consumer integration tests.
