# Python architecture

## Goal of the document

This document describes language-level implementation conventions for Python library code.

## Scope

This specification applies to Python implementation conventions in `llm_tool_cli`.
Module ownership, capability behavior, entity modeling, error contracts, and formatting are out of scope.

## Dictionary

- `project-controlled class` — a class whose instance layout is defined by library code rather than generated or prescribed by external machinery or an inherited implementation contract.
- `test class` — a class defined only to organize or support automated tests.
- `instance dictionary` — the per-instance `__dict__` used to store dynamically named attributes.

## Type names

Class, enum, and type alias names SHOULD use singular nouns when each instance represents one concept, so type names distinguish individual concepts from collections.
Plural type names SHOULD be reserved for types whose meaning is a collection or registry.

Type names SHOULD avoid confusion with Python, typing, or framework concepts when a clearer library-specific term is available, so readers can distinguish library concepts from those provided by their dependencies.

## Type annotations

Production interfaces SHOULD carry useful type annotations so callers and type checkers can verify the intended contract.
Type fixes MUST preserve the interface's actual meaning rather than replace useful types with unconstrained values to silence a checker.
New abstractions MUST NOT be introduced solely to satisfy a checker when a local correct annotation or simpler implementation is sufficient.

## Runtime type validation

Functions called through project-controlled typed interfaces SHOULD treat annotated parameter types as caller contracts.
They SHOULD NOT perform runtime checks solely to verify that arguments match their declared types.

Runtime validation remains appropriate at untyped or external boundaries, including configuration, deserialized data, CLI input, and third-party responses.
Code MUST validate semantic constraints that type annotations cannot express.

Code that constructs a semantically specific typed value from raw data MUST validate that type's semantic invariants at the construction boundary.
Code that receives the constructed typed value MUST assume those invariants hold instead of repeating their validation.

## Temporary implementation code

Production code intentionally introduced as a temporary bridge MUST include an adjacent `TODO` comment.
The comment MUST explain why the bridge is necessary and identify the concrete condition or tracked work item after which it MUST be removed.
Keeping the explanation adjacent makes the exception discoverable when the code is maintained.
The comment MUST be removed together with the temporary code.

## Closed value sets

Project-owned closed sets of named values MUST use enum classes to give each concept one discoverable nominal runtime type across typed interfaces.
`typing.Literal` MUST NOT replace an enum as the primary internal representation of a project-owned closed set.
`Literal` MAY name enum members in typed-union discriminators or express exact values required by an external interface.
Raw literal values required by an external interface MUST be converted to the corresponding enum at the boundary when they represent a library-owned closed set.
`Literal` MAY describe values that do not represent independently named project concepts.

Enum type names SHOULD describe what one member represents so annotations identify the value's meaning.
Enum member names SHOULD use the serialized value name when the enum crosses an external boundary and the serialized names are stable, so code and boundary representations use recognizable terminology.

Project-owned enum members MUST use explicit values rather than `enum.auto()` so member identities remain independent of declaration order or generated naming rules.
Project-owned enum values persisted in library-owned storage MUST be fixed integers.
Fixed integers keep persisted identities independent from human-readable names.
Assigned persisted integer values MUST NOT be changed or reused.

Project-owned enum values that are not persisted MAY use another explicit representation when it expresses their runtime meaning or an intentional boundary protocol token.
External-boundary enums MAY use explicit string values when human-readable wire values are an intentional part of the contract.
Those string values MUST be treated as stable compatibility identifiers and MUST NOT be changed or reused without an explicit compatibility transition.
Values that participate in serialization, configuration, or another compatibility contract MUST preserve their specified representation.
Code SHOULD convert explicitly between internal and boundary representations when they have independent compatibility lifecycles.

Code that exhaustively branches over an enum or statically closed union SHOULD pass the unreachable value to `typing.assert_never()` so static analysis detects newly unhandled variants.
Ordinary validation failures remain appropriate when unsupported values can arrive through an external boundary.

## Validation and resolution

Validation functions and methods MUST only verify invariants.
They MUST use `None` as the successful value.
Validation of expected external input failures MUST use `Result[None, EnvironmentErrors]` according to the error architecture.
Internal invariant checks MAY return `None` directly and raise an appropriate internal exception on failure.
This return contract keeps validation distinct from data retrieval and transformation.

Validation functions and methods MUST NOT return information incidentally obtained through any of these operations during validation:

- retrieval.
- resolution.
- transformation.
- extraction.

They MAY perform those operations internally when required to verify invariants.
Callers that need the resulting information MUST obtain it separately unless the operation explicitly acts as a validating constructor.

A validating constructor MAY return the object it constructs when construction is part of its explicit contract.
This exception MUST NOT be used to return dependencies resolved or information incidentally extracted during validation.
Framework validator hooks MUST follow the return protocol required by their framework.
Hooks that must return the validated value or instance, or raise validation exceptions, are exempt from the ordinary validation return contract.

Predicates named `is_*`, `has_*`, or `can_*` SHOULD return `bool` and MUST NOT raise an exception for an ordinary negative result.

## Function extraction

A separate function SHOULD represent a meaningful operation, centralize an invariant, support reuse, or simplify non-trivial control flow.
A trivial collection update used at one call site MUST remain inline and MUST NOT be extracted into a separate function merely to isolate the mutation.
An update is trivial for this rule when its intent is clear from the collection operations and it does not enforce a separate invariant or contain non-obvious control flow.
Keeping those updates inline preserves their local context without introducing a separate operation contract.

## Class instance layout

Project-controlled classes other than test classes MUST define `__slots__` explicitly unless an exception below applies.
This requirement applies to both existing and newly introduced classes.
Explicit slots make attribute ownership predictable and prevent unintended instance dictionaries and dynamically named state.

A class that introduces instance attributes MUST list every attribute it introduces in `__slots__`.
A class that introduces no instance attributes MUST use `__slots__ = ()`.
Every covered subclass MUST define its own `__slots__`, including an empty declaration when it introduces no attributes.
A subclass MUST NOT repeat slot names owned by a base class.

Classes MUST NOT include `__dict__` in `__slots__` unless dynamically named instance attributes are an intentional part of the class contract.
Classes MUST include `__weakref__` only when instances need weak-reference support and no base class already provides it.

### Exceptions

Test classes MAY omit `__slots__` without an explanatory comment.
A class MAY omit an explicit `__slots__` declaration when one or more of the following conditions apply:

- a base class already provides an instance dictionary and preserving that inherited layout is required, so a subclass declaration would not provide the intended restriction.
- framework or generated implementation machinery owns the instance layout or requires dynamic attributes.
- dynamically named instance attributes are intentional behavior of the class.
- a concrete interoperability requirement, such as serialization or proxying, is incompatible with a slotted instance layout.

Pydantic models, enums, and exceptions are common examples where inherited machinery controls instance storage.
When the reason for omitting `__slots__` is not evident from the base class or implemented protocol, an adjacent comment MUST state the concrete reason.
