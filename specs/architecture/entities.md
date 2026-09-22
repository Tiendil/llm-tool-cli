# Entity architecture

## Goal of the document

This document describes conventions for typed library data and the ownership of its validation and serialization.

## Scope

This specification applies to Python data structures representing library concepts.
Individual data schemas, consumer domain models, and external protocol formats are out of scope.

## Dictionary

- `entity` — a typed Python object representing one library concept.
- `value entity` — an entity whose equality is based on its data rather than object identity.
- `boundary entity` — an entity passed between modules or between the library and a consumer.
- `serialized representation` — plain data prepared for an external protocol or storage boundary.

## General principles

Library concepts MUST have explicit typed representations before they cross module boundaries.
Boundary entities MUST NOT use untyped dictionaries unless the data is already a serialized representation.

Structured models SHOULD use Pydantic v2 for consistent validation and serialization.
Very small internal helper values MAY use plain classes when model validation would add no practical value.
Project data structures MUST NOT use `dataclasses.dataclass`.
This keeps structured entity validation and serialization under the Pydantic convention instead of introducing a parallel modeling system.

Entity behavior SHOULD remain pure and local to its data.
Entities MUST NOT perform:

- filesystem access.
- configuration file discovery.
- process execution.
- terminal output.
- other application operations.

Value entities SHOULD be immutable when practical.
Entities that can be used for de-duplication SHOULD be hashable when practical so collections can identify equivalent values without separate identity rules.

## Model conventions

To keep model input normalization and validation consistent, model defaults SHOULD:

- strip surrounding whitespace from string values.
- validate default values.
- reject unknown fields.
- prefer immutable value objects when practical.
- validate assignment when mutation is explicitly enabled.
- avoid attribute-based construction unless a boundary explicitly needs it.

Normalization MUST preserve significant whitespace and exact values required by compatibility contracts.

Models SHOULD express local field constraints and model invariants through Pydantic field metadata and validators so validation stays with the data it governs.
Default factories and discriminators SHOULD use Pydantic's field mechanisms so model construction and validation share one contract.

Validators SHOULD enforce one cohesive invariant or closely related family of constraints so unrelated validation failures remain understandable and independently testable.
A validator MAY inspect multiple fields when they jointly define an invariant.

Shared entity infrastructure SHOULD be introduced only when implemented models need a common behavior or invariant.
When a shared base entity exists, project models SHOULD inherit from it to apply shared validation and serialization conventions consistently.
Models MAY use Pydantic directly when they intentionally mirror external input shapes or must satisfy a third-party model contract.
A shared base entity MUST provide a copy-with-changes operation so callers can derive updated values without mutating immutable entities.

## Semantic types

Names for boundary concepts SHOULD preserve the terminology of the applicable external contract so readers can relate library types to that contract.

Semantically specific primitive values MUST have semantically specific Python types before they cross module boundaries or the library's public boundary.
Entities and public function signatures MUST NOT use unqualified primitive types for values with a distinct library meaning.
These types make semantic distinctions part of the typed interface so callers cannot silently interchange unrelated identifiers or values.

`typing.NewType` SHOULD be used when runtime behavior is identical to the underlying primitive to distinguish semantic roles without changing runtime behavior.
Semantic primitive types MAY use small custom classes when they need validation or behavior beyond the underlying primitive.

Raw primitives MAY be used at boundaries that convert external data into or out of library types:

- parsing.
- rendering.
- storage.
- serialization.

Raw primitives MAY be used inside local helper code when the value has already been validated or a semantic type would not improve module-boundary clarity.
Semantic primitive types MUST belong to the module that owns the corresponding library concept.

## Static typing suppressions

When a static type checker cannot prove a semantic primitive type relationship that is already guaranteed by validation or construction at the same boundary, code SHOULD use a local `# type: ignore[...]` suppression instead of `typing.cast(...)` or a pure runtime no-op conversion such as `str(...)`.
This makes the static analysis limitation explicit without adding a runtime operation that suggests conversion or validation.
Type suppressions MUST be as narrow as practical.
Type suppressions MUST NOT be used to bypass missing validation, unsafe external input conversion, or a real mismatch between runtime behavior and declared types.
Type suppressions MUST name the relevant error code when supported by the checker.

## Enumeration conventions

Closed sets of named library values MUST use Python enum classes so each concept has one nominal runtime type with discoverable members across typed interfaces.
Plain strings MUST NOT be the primary internal representation of values with a finite configured, persisted, or specified set of allowed names.

String-valued closed sets MUST use `enum.StrEnum`.
Library-owned enum values persisted in library-owned storage MUST use `enum.IntEnum` with fixed integer values.
Integer-valued closed sets MUST use `enum.IntEnum` when the integer value is part of an external contract or persisted state.
Enum classes MUST use these standard bases instead of `str, enum.Enum` or `int, enum.Enum` to keep primitive-value interoperability under one enum convention.

Enum values that cross external boundaries MUST preserve their specified serialized or persisted representation exactly.

## Ownership

An entity MUST belong to the module that owns its meaning.
External-boundary transfer entities MUST belong to the module that owns that boundary.
Consumer-specific domain entities MUST remain with the consumer.
Public re-exports MUST keep the defining owner clear.

Shared entity infrastructure MUST remain independent of capability-specific concepts.
Entities for concepts shared across library capabilities MUST model those concepts independently from the concrete interfaces that create or render them.
Those shared entities MUST NOT depend on CLI option parsing, concrete configuration file syntax, or rendered protocol record shapes.
Entities needed by only one capability MUST remain with that capability.

## Configuration entities

Configuration entities MAY represent parsed settings data at a configuration-loading boundary.
They SHOULD use Pydantic validation to reject malformed parsed input before it reaches lower layers so those layers receive validated configuration concepts.
They MUST preserve enough information to report useful configuration errors.
Lower layers MUST receive validated library concepts independently from raw configuration file shapes.
Configuration entities MAY reference other library entities when those concepts have already been validated.

Configuration file loading MUST remain outside entity definitions and Pydantic validators.

## Command entities

Command entities MUST represent parsed user intent before command execution.
They MUST model command selection and parsed options independently from rendered output.
They MUST NOT contain rendered output or perform command execution.
Parsed identifiers and paths with library-specific meaning MUST use semantic primitive types after normalization and validation.

## Data structure conventions

Ordered input from users and external sources SHOULD use ordered collections to preserve meaningful input order.
Sets MAY be used internally for de-duplication, but externally visible output order MUST be produced explicitly according to the applicable behavior contract.
Collections representing stacks, queues, or other ordered state MUST preserve order explicitly.

Mappings keyed by semantic identifiers SHOULD use the semantic identifier type so static analysis can distinguish unrelated keys.
Optional values MUST use `None` instead of sentinel strings.

## Serialization boundaries

Serialized representations MUST be created at protocol or storage boundaries and SHOULD be treated as write-only output data to keep internal behavior independent from output formats.
Models SHOULD use Pydantic serialization methods at boundaries that need model dumps or JSON so serialization follows the model's declared contract.
Explicit boundary code SHOULD produce serialized representations from models to keep representation choices with the boundary that owns them.
Internal entity behavior MUST NOT depend on incidental Pydantic dump shapes.
Incidental Pydantic dump shapes MUST NOT become public contracts without an intentional boundary requirement.

Entity methods that return dictionaries for protocol metadata, logging, or storage MUST return structured values with stable keys and MUST NOT contain presentation formatting.

## Validation boundaries

Parsing layers SHOULD validate external data before creating entities used by lower layers so malformed input is rejected at the boundary that can explain it.
Pydantic model validation MAY enforce local invariants that are always true for an entity.
Validation that requires filesystem access, configuration discovery, or command execution MUST live outside pure entity definitions.
Invalid external input MUST be reported through the error architecture instead of returning partially valid entities.
