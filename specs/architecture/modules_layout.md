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
The configuration module MUST use the shared `ProjectConfigPath` for successful path values returned by `find_config`, `resolve_config_path`, and `locate_config`.
It MUST preserve each operation's existing discovery, resolution, and symlink behavior.

The protocol module MUST own shared output protocols, cell construction, JSON Lines serialization, and direct text writing.
Its public package interface MUST export `Protocol`, `to_jsonl`, and `write_output` from `llm_tool_cli.protocol`.
The protocol enum MUST live in `protocol.entities`, record serialization in `protocol.serialization`, and text writing in `protocol.streams`.
The protocol enum, record serialization, and text writing MUST depend only on the standard library.
The public `llm_tool_cli.protocol.cells` submodule MUST own the complete `Cell` entity, its construction helpers and compact identifier, `MetaValue`, and `to_meta_value`.
Cells MUST inherit the shared `BaseEntity` from the core module.
The public `llm_tool_cli.protocol.errors` submodule MUST own the internal `ContentWithoutMediaType` exception under a protocol-specific `InternalError` root derived from the shared internal-error base.
Consumer-specific cell kinds and content, external record construction, renderers, CLI defaults and parsing, error classification, and exit selection MUST remain consumer-owned.

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
