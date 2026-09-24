# Error architecture

## Goal of the document

This document describes how library modules represent environment errors, internal exceptions, and warnings, and separate failure ownership from consumer presentation.

## Scope

This specification applies to failure handling in library capabilities and CLI integration boundaries.
Capability-specific error inventories and presentation formats are out of scope.

## Dictionary

- `fatal error` — a problem that prevents the requested operation from completing successfully.
- `non-fatal problem` — a problem discovered during an operation that does not prevent it from producing useful requested output.
- `error code` — a stable machine-readable identifier for an expected fatal error.
- `module environment-error root` — a module-owned base model that classifies its expected operational failures.
- `module internal-exception root` — a module-owned base exception that classifies its internal and technical failures.
- `exception boundary` — a module boundary with defined recovery, translation, or context-enrichment behavior for exceptions.
- `stored-state integrity failure` — an unexpected failure to validate or reconstruct persisted library-owned state according to its owning model.

## Failure ownership

Each capability MUST distinguish expected failures from successful outcomes in its documented public contract.
Expected fatal errors MUST be returned as `Result` values containing library-specific environment errors before they cross module boundaries.
Module-specific error types MUST be owned by the module that can explain the condition and provide the most useful context.
Callers MUST NOT need to parse human-readable message text to distinguish failures they are expected to handle.

Shared base error types MUST be owned by a common lower-level module that does not depend on CLI behavior or consumer presentation.
Production errors MUST NOT be defined in test modules.
Test-only error classes MAY be defined in test modules when they are required to verify error handling behavior.

Code SHOULD NOT define duplicate functions that differ only by error handling strategy, so each operation has one clear failure contract.

## Error hierarchies

The library MUST define a shared root exception named `InternalError` for internal and technical failures.
The root exception MUST inherit from `Exception` and MUST NOT inherit from Pydantic model classes.
Internal errors represent programming defects, violated invariants, or misuse of an internal interface.
They MUST NOT be converted into environment errors merely because they have a known exception type.

Expected operational failures MUST be represented by a shared Pydantic model named `EnvironmentError`.
The shared environment-error model MUST inherit from the shared base entity so it uses the common validation, copying, and JSON serialization behavior.
Environment errors MUST NOT inherit from `Exception`.
Each module that defines expected fatal errors MUST provide a module environment-error root derived from `EnvironmentError` or a parent module's environment-error root.
All expected fatal errors owned by that module MUST inherit from that root.
Internal exception roots MUST derive from the shared `InternalError` or a parent module's internal exception root.

The two hierarchies MUST remain independent and MUST NOT share a library-defined error base.
Module root names MUST identify their category as `InternalError` or `EnvironmentError`.
An unqualified `Error` MUST NOT serve as a root in either hierarchy.

Module roots in either hierarchy SHOULD be abstract classification classes and SHOULD NOT be instantiated directly when a more specific concrete error is available, so callers can distinguish concrete failure cases.
Intermediate abstract error classes MAY exist under a module root when a narrower classification is useful.
Each distinct expected failure case SHOULD have its own environment-error subclass so callers can handle failures by type.

Concrete error class names SHOULD be short and descriptive so callers can recognize the failure without inspecting its implementation.
They SHOULD omit redundant error-category suffixes when the shorter name remains clear from its ownership and base class.

## Results

Shared result infrastructure MUST belong to the core module and remain independent of capability-specific errors and presentation.
`Result[T, E]` MUST distinguish `Ok(value)` from `Err(error)` while preserving the supplied payload.
The generic error parameter MUST remain unrestricted so the result abstraction does not impose a particular error model.
Operations with expected environment failures MUST use `Result[T, EnvironmentErrors]`, where `EnvironmentErrors` is a list of `EnvironmentError` values.
Operations that do not have expected failure outcomes MAY return their ordinary value.
An expected failure MUST NOT be exposed through both an error result and a separate raised-exception channel of the same operation.

Independent validation failures discovered in one pass SHOULD be collected into one error list so callers can address them together.
Propagation MUST preserve existing error values unless translation adds domain meaning or implements recovery.
Package ownership alone MUST NOT require wrapping a returned error.

The `unwrap_to_error` decorator SHOULD be used when it makes composition of result-returning functions easier to follow.
It MUST convert only the technical `UnwrapError` raised by unsuccessful unwrapping back into `Err` with the original payload.
It MUST NOT hide arbitrary exceptions or misuse of error unwrapping on a successful result.
Callers MUST maintain compatibility between propagated error payloads and their declared return contracts.

An external callback boundary that cannot return `Result` MAY use `EnvironmentErrorsProxy` to carry expected error values.
The shared proxy MUST inherit from `InternalError` and carry the original `EnvironmentErrors` list in `details["errors"]`.
It MUST remain distinct from result-unwrapping exceptions so callback recovery does not intercept unrelated internal failures.
Technical propagation exceptions MUST belong to the internal-exception hierarchy and MUST preserve the original failure category of their payloads.
That exception MUST be caught at the nearest controlled boundary and converted back into an error result.
Technical propagation exceptions MUST NOT escape a public result-returning operation during expected failure handling.

## Error data

### Internal exceptions

Internal exceptions MUST carry an exception message and MAY carry structured debugging context or technical propagation payloads through `details`.
The shared internal-exception base MUST shallow-copy the supplied details mapping while preserving its values.
Internal exception subclasses MAY declare a message template whose placeholders refer to keys in `details`.
When no explicit message is supplied, the shared base MUST format that template from `details`, or use the concrete exception class name when no template is declared.
An explicit message MUST take precedence and remain literal, including an empty message or text containing braces.
Internal-exception details MAY contain arbitrary Python objects and MUST NOT be treated as environment-error diagnostic records.
The shared internal-exception base MUST NOT define environment-error codes, corrective guidance, or diagnostic-record serialization.

### Environment errors

Environment errors MUST expose stable error codes.
Error codes MUST contain only lowercase ASCII letters, ASCII digits, `_`, and `.`.
Their exact values and compatibility requirements MUST be specified with the owning capability.

Environment errors MUST carry a human-readable message and MAY carry corrective guidance and typed context fields so consumers can diagnose failures without implementation stack details.
Messages and corrective guidance MAY reference context through `{error.<field>}` formatting.
Environment-error string fields MUST use the shared base entity's normalization, including stripping surrounding whitespace.
The shared environment-error model MUST remain independent of protocol-specific fields and rendering behavior.
Consumers MAY extend it with their own presentation metadata.
Environment-error context MUST contain values that can be rendered deterministically.
When context needs serialization, it SHOULD use plain JSON-compatible scalar and collection values so rendering does not depend on Python object representations.
Native diagnostic records MUST contain `type`, `code`, and the formatted `message`, together with serialized context fields.
The reserved record fields MUST take precedence over conflicting context fields.
Message templates and corrective guidance MUST NOT become context fields in those records.
An original exception retained for debugging MUST remain outside serialized diagnostic data.

## Exception boundaries

Code MUST catch an exception only when the boundary has defined recovery, translation, or context-enrichment behavior for that condition.
Recognizing an exception type alone is not sufficient reason to catch it.

A failure is expected only when it is part of the called operation's documented contract and the caller has a defined response.
Failures caused by any of the following MUST NOT be treated as expected merely because they use a known or library-specific exception type:

- programming defects.
- violated internal invariants.
- invalid persisted state.
- unexpected infrastructure failures.

Modules that call external systems MUST translate expected low-level failures into environment-error results at the nearest boundary that can provide useful library-level context.
External systems include:

- filesystem access.
- parsing.
- model validation.
- external command or service calls.

An expected low-level condition MUST have a defined response supported by at least one of the following:

- the module's behavior explicitly anticipates the condition.
- a third-party contract defines the condition as a normal outcome.
- the condition is a known recurring operational case that the developer has decided to handle.
- the caller can make a useful decision from a module-specific error.

Modules SHOULD NOT catch broad low-level exception classes solely to satisfy the translation rule, because doing so can misclassify unrelated failures as expected.
Unknown third-party failures SHOULD NOT be broadly normalized unless the boundary intentionally treats all failures of that operation as a recoverable outcome.
Expected service failures MUST be converted into module-specific environment errors when those failures are part of normal operation.
When an exception is translated, its cause SHOULD be preserved when useful for diagnosis.

Unexpected failures MAY propagate unchanged until the developer explicitly defines handling for that class of failure.
An external boundary MAY catch an unexpected exception to report it and translate it into the boundary's standard failure behavior.
This translation MUST NOT change whether the failure is expected or unexpected.
Translation of an unexpected failure MUST leave the operation failed and MUST NOT recover with a successful, empty, or fallback result.

A failure to validate or reconstruct persisted library-owned state according to its owning model MUST be treated as an unexpected stored-state integrity failure.

## Pydantic validation errors

Pydantic validation errors MUST NOT be exposed directly across high-level module boundaries for external input.
Modules that create Pydantic entities from external input MUST convert `pydantic.ValidationError` and other expected low-level validation failures into environment-error results at the nearest exception boundary with useful context.
This requirement also applies to user-provided configuration.
Validation failures while reconstructing persisted library-owned state MUST follow the stored-state integrity rule instead of being translated into expected input errors.

Pydantic validation errors MAY be used directly inside tests for low-level entity validation.

## Presentation boundaries

Library operations outside an explicitly documented output or CLI integration boundary MUST NOT print errors or warnings, select terminal formatting, or terminate the process.
Lower-level modules and error types MUST NOT know about CLI exit codes or HTTP status codes.
Consumers own application-level handling and presentation unless they explicitly delegate it to a library capability.

A known error class alone MUST NOT make a failure part of a caller-correctable external error contract.
A boundary MAY report an unexpected stored-state integrity failure as a generic failure, but MUST NOT assign it a stable capability error code or present it as a condition the caller can correct.

When a consumer delegates CLI error handling to the library, the CLI boundary MUST map fatal errors to non-zero exit behavior.
The CLI boundary MUST own the mapping from environment-error classes to exit codes.
It MAY map module environment-error roots to exit categories and map concrete error classes when a module root is too broad.
The mapping MUST define a default non-zero exit code for environment errors that are not explicitly mapped.
The CLI boundary SHOULD choose the most specific matching non-zero exit category so it preserves the available failure classification.
Warnings alone MUST NOT cause a non-zero CLI exit code.

## Non-fatal problems

A non-fatal problem MUST be distinguished from failure to produce the requested valid result.
Warnings represent non-fatal problems discovered while processing a request.
Warnings MUST be used only when processing can continue and the operation can still produce useful requested output.
Warnings MUST NOT be used for invalid command line arguments, invalid configuration that prevents loading, or operation failures that prevent producing a valid result.
Warnings MUST NOT disguise an unusable result as successful.
Code that produces warnings SHOULD include enough context for the consumer to explain the problem.

The library currently has no shared warning storage or warning delivery architecture.
Until such architecture is specified and implemented, modules MUST NOT invent ad hoc warning channels.

## Other exception types

Other exception types MAY be used when required by a Python protocol or third-party interface, including Pydantic validator hooks.
This allowance MUST NOT bypass the translation of expected failures at high-level module boundaries.

`NotImplementedError` MAY be used as a temporary placeholder only while implementation is in progress.
Before a change is considered complete, temporary `NotImplementedError` usages SHOULD be replaced with implemented behavior or an appropriate internal error so incomplete behavior does not become a permanent failure contract.

## Assertions

Assertions MAY express invariants already guaranteed by typed interfaces or earlier control flow.
Assertions MUST NOT replace validation of external input or handling of expected environment failures.
