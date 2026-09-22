# Error architecture

## Goal of the document

This document describes how library modules represent expected fatal errors and warnings, translate exceptions, and separate failure ownership from consumer presentation.

## Scope

This specification applies to failure handling in library capabilities and CLI integration boundaries.
Capability-specific error inventories and presentation formats are out of scope.

## Dictionary

- `fatal error` — a problem that prevents the requested operation from completing successfully.
- `non-fatal problem` — a problem discovered during an operation that does not prevent it from producing useful requested output.
- `error code` — a stable machine-readable identifier for an expected fatal error.
- `module root error` — the `Error` exception class in a module's `errors` submodule, which classifies expected fatal errors owned by that module.
- `exception boundary` — a module boundary with defined recovery, translation, or context-enrichment behavior for exceptions.
- `stored-state integrity failure` — an unexpected failure to validate or reconstruct persisted library-owned state according to its owning model.

## Failure ownership

Each capability MUST distinguish expected failures from successful outcomes in its documented public contract.
Expected fatal errors MUST be raised as library-specific exceptions before they cross module boundaries.
Module-specific error types MUST be owned by the module that can explain the condition and provide the most useful context.
Callers MUST NOT need to parse human-readable message text to distinguish failures they are expected to handle.

Shared base error types MUST be owned by a common lower-level module that does not depend on CLI behavior or consumer presentation.
Production errors MUST NOT be defined in test modules.
Test-only error classes MAY be defined in test modules when they are required to verify error handling behavior.

Code SHOULD NOT define duplicate functions that differ only by error handling strategy, so each operation has one clear failure contract.

## Error hierarchy

When expected fatal errors are implemented, the library MUST define a single shared root exception named `Error`.
The root exception MUST inherit from `Exception` and MUST NOT inherit from Pydantic model classes.
This hierarchy gives consumers a single catch boundary and keeps failure propagation under Python's exception protocol.

Each module that defines expected fatal errors MUST define one module root error class named `Error`.
All expected fatal errors owned by that module MUST inherit from its module root error class.
The shared root exception also serves as the module root of its owning module.
Every other module root error class MUST inherit from the shared root exception or from a parent module's root error class.

Module root error classes SHOULD be abstract classification classes and SHOULD NOT be raised directly when a more specific concrete error is available, so callers can distinguish concrete failure cases.
Intermediate abstract error classes MAY exist under a module root when a narrower classification is useful.
Each distinct expected failure case SHOULD have its own exception subclass so callers can handle failures by type.

Concrete error class names SHOULD be short and descriptive so callers can recognize the failure without inspecting its implementation.
They SHOULD omit redundant error-category suffixes when the shorter name remains clear from its ownership and base class.

## Exception data

Library-specific exceptions for expected fatal errors MUST expose stable error codes.
Error codes MUST contain only lowercase ASCII letters, ASCII digits, and `_`.
Their exact values and compatibility requirements MUST be specified with the owning capability.

Exceptions SHOULD carry a human-readable message and relevant structured context so consumers can diagnose failures without implementation stack details.
Structured details MUST contain values that can be rendered deterministically.
When details need serialization, they SHOULD use plain JSON-compatible scalar and collection values so rendering does not depend on Python object representations.

## Exception boundaries

Code MUST catch an exception only when the boundary has defined recovery, translation, or context-enrichment behavior for that condition.
Recognizing an exception type alone is not sufficient reason to catch it.

A failure is expected only when it is part of the called operation's documented contract and the caller has a defined response.
Failures caused by any of the following MUST NOT be treated as expected merely because they use a known or library-specific exception type:

- programming defects.
- violated internal invariants.
- invalid persisted state.
- unexpected infrastructure failures.

Modules that call external systems MUST translate expected low-level failures into library-specific exceptions at the nearest boundary that can provide useful library-level context.
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
Expected service failures MUST be converted into module-specific exceptions when those failures are part of normal operation.
When an exception is translated, its cause SHOULD be preserved when useful for diagnosis.

Unexpected failures MAY propagate unchanged until the developer explicitly defines handling for that class of failure.
An external boundary MAY catch an unexpected exception to report it and translate it into the boundary's standard failure behavior.
This translation MUST NOT change whether the failure is expected or unexpected.
Translation of an unexpected failure MUST leave the operation failed and MUST NOT recover with a successful, empty, or fallback result.

A failure to validate or reconstruct persisted library-owned state according to its owning model MUST be treated as an unexpected stored-state integrity failure.

## Pydantic validation errors

Pydantic validation errors MUST NOT be exposed directly across high-level module boundaries for external input.
Modules that create Pydantic entities from external input MUST convert `pydantic.ValidationError` and other expected low-level validation failures into library-specific exceptions at the nearest exception boundary with useful context.
This requirement also applies to user-provided configuration.
Validation failures while reconstructing persisted library-owned state MUST follow the stored-state integrity rule instead of being translated into expected input errors.

Pydantic validation errors MAY be used directly inside tests for low-level entity validation.

## Presentation boundaries

Library operations outside an explicitly documented output or CLI integration boundary MUST NOT print errors or warnings, select terminal formatting, or terminate the process.
Lower-level modules and error types MUST NOT know about CLI exit codes or HTTP status codes.
Consumers own application-level handling and presentation unless they explicitly delegate it to a library capability.

A library-specific exception class alone MUST NOT make a failure part of a caller-correctable external error contract.
A boundary MAY report an unexpected stored-state integrity failure as a generic failure, but MUST NOT assign it a stable capability error code or present it as a condition the caller can correct.

When a consumer delegates CLI error handling to the library, the CLI boundary MUST map fatal errors to non-zero exit behavior.
The CLI boundary MUST own the mapping from exception classes to exit codes.
It MAY map module root errors to exit categories and map concrete error classes when a module root is too broad.
The mapping MUST define a default non-zero exit code for library-specific exceptions that are not explicitly mapped.
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
Before a change is considered complete, temporary `NotImplementedError` usages SHOULD be replaced with implemented behavior or an appropriate library-specific error so incomplete behavior does not become a permanent failure contract.

## Assertions

Assertions MAY express invariants already guaranteed by typed interfaces or earlier control flow.
Assertions MUST NOT replace validation of external input or handling of expected environment failures.
