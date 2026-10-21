# Entity architecture

## Goal of the document

This document describes typed library data, validation, and serialization ownership.

## Scope

Python data structures representing library concepts; individual schemas, consumer domain models, and external formats are out of scope.

## Dictionary

- `entity` — a typed object representing one library concept.
- `value entity` — an entity compared by data rather than identity.
- `boundary entity` — an entity crossing module or library/consumer boundaries.
- `serialized representation` — plain data for external protocols or storage.

## General principles

Library concepts MUST have explicit typed representations across boundaries, not untyped dictionaries except for serialized data.
Structured models SHOULD use Pydantic v2 for consistent validation and serialization.
Small internal helpers MAY use plain classes when validation adds no value.
Data structures MUST NOT use `dataclasses.dataclass`, keeping one structured modeling system.

Entity behavior SHOULD remain pure and local.
Entities MUST NOT perform:

- filesystem access.
- configuration discovery.
- process execution.
- terminal output.
- other application operations.

Value entities SHOULD be immutable when practical; deduplicatable entities SHOULD be hashable when practical so equivalence needs no separate identity rules.

## Model conventions

For consistent normalization and validation, defaults SHOULD:

- strip surrounding string whitespace.
- validate defaults.
- reject unknown fields.
- prefer immutable values.
- validate assignment when mutation is enabled.
- avoid attribute-based construction unless a boundary needs it.

Normalization MUST preserve significant whitespace and exact compatibility values.
Models SHOULD use Pydantic fields and validators for local constraints and invariants, and field mechanisms for defaults and discriminators, keeping construction and validation consistent.
Validators SHOULD cover cohesive invariants for understandable, independently testable failures; they MAY inspect jointly constrained fields.

The library MUST provide a shared Pydantic base for validation, copying, and JSON serialization.
Models SHOULD inherit it for consistent behavior, but MAY use Pydantic directly for external input shapes or third-party model contracts.
The base MUST deeply copy existing data and apply trusted changes without validation in its copy-with-changes operation, allowing immutable updates.
It MUST support JSON serialization and reconstruct validated instances of the concrete type.

## Semantic types

Boundary names SHOULD preserve external-contract terminology to make their correspondence clear.
Distinct library primitive meanings MUST have semantic Python types across module/public boundaries and in entities and public signatures, preventing silent interchange of unrelated values.
`typing.NewType` SHOULD distinguish roles without runtime changes; small custom classes MAY supply extra validation or behavior.

Raw primitives MAY appear during:

- parsing.
- rendering.
- storage.
- serialization conversion.

They MAY also appear in local helpers after validation or when semantic typing would not clarify a module boundary.

Semantic types MUST belong to their concept's owner.

## Static typing suppressions

For semantic relationships already guaranteed by validation or construction at the same boundary, code SHOULD prefer local `# type: ignore[...]` over `typing.cast(...)` or runtime no-ops such as `str(...)`, exposing checker limitations without implying conversion.
Suppressions MUST be as narrow as practical, include supported error codes, and MUST NOT bypass missing validation, unsafe input conversion, or actual type mismatches.

## Enumeration conventions

Closed named sets MUST use Python enums, not primarily raw strings, giving each finite configured, persisted, or specified concept a nominal type with discoverable members.
String sets MUST use `enum.StrEnum`; library-owned enums persisted in library-owned storage MUST use fixed-value `enum.IntEnum`.
Integer sets MUST use `enum.IntEnum` when values are externally contracted or persisted.
These bases MUST replace `str, enum.Enum` and `int, enum.Enum` for consistent primitive interoperability.
External and persisted representations MUST remain exact.

## Ownership

Entities MUST belong to their concept or external boundary's owner; consumer domain entities MUST remain consumer-owned.
Re-exports MUST keep ownership clear.
Shared infrastructure MUST be capability-independent.
Cross-capability entities MUST be independent of creating/rendering interfaces and MUST NOT depend on CLI parsing, configuration syntax, or rendered record shapes.
Single-capability entities MUST remain with that capability.

## Configuration entities

Configuration entities MAY represent parsed settings and reference validated library entities.
They SHOULD use Pydantic validation before lower layers, which MUST receive validated concepts independent of file shapes.
They MUST preserve useful error context.
File loading MUST remain outside entities and validators.

## Command entities

Command entities MUST represent parsed selection and options before execution, independently from output, and MUST NOT contain rendered output or execute commands.
Normalized, validated library-specific ids and paths MUST use semantic types.

## Command results

Logic cells MUST be the primary successful domain-to-CLI interface.
Command-facing operations MAY submit cells to the scoped emitter and return `Result[None]` when no other result is useful.
Reusable computations MAY return typed values, including cells and ordered cell collections; internal domain operations and low-level capabilities MAY retain their own types.
Cell subclasses MAY hold typed domain data for projection, but MUST NOT require CLI inspection or payload assembly, keeping result assembly independent of CLI parsing and protocol selection.

Cells MUST carry projection data without runtime-state reads or output writes.
Shared journal-record boundary entities MUST be constructed from cell data independently of delivery and application context.
Journal-capable cells MUST define semantic summaries; generic content cells MUST prohibit journaling.
Consumer execution ids MUST remain consumer-owned structured journal attributes.
CLI initialization MUST establish delivery and protocol; the shared emitter MUST buffer and deliver cells.
Expected failures MUST remain structured failed-result errors until the CLI error boundary.
Generic acknowledgements and prepared documents MAY use shared content cells.

## Data structure conventions

User/external ordered input SHOULD use ordered collections to preserve meaning.
Sets MAY deduplicate internally, but observable order MUST follow the behavior contract explicitly.
Stacks, queues, and other ordered state MUST preserve order explicitly.
Semantic-id mappings SHOULD use semantic key types to distinguish unrelated keys.
Optional values MUST use `None`, not sentinel strings.

## Serialization boundaries

Serialized representations MUST be created at protocol/storage boundaries and SHOULD be write-only so internal behavior stays format-independent.
Models SHOULD use Pydantic serialization through explicit boundary code, keeping representation choices with their owner and declared model contract.
Internal behavior MUST NOT depend on incidental dump shapes, which MUST NOT become public contracts without intentional boundary requirements.
Dictionary-returning metadata/logging/storage methods MUST use stable structured keys and MUST NOT format presentation.

## Validation boundaries

Parsing layers SHOULD validate external input before constructing lower-layer entities, rejecting it where failures can be explained.
Model validation MAY enforce always-true local invariants.
Filesystem, discovery, and command-dependent validation MUST stay outside pure entities.
Invalid input MUST follow the error architecture, never produce partially valid entities.
