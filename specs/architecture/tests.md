# Test architecture

## Goal of the document

This document describes test organization, coverage, and isolation.

## Scope

This specification covers Python library and development-helper tests.
The following are out of scope:

- runner/CI configuration.
- exact fixture names.
- publishing checks.
- performance benchmarks.

## Dictionary

- `unit test` — tests one module or a small related group of functions/entities.
- `integration test` — tests multiple modules through a public boundary.
- `fixture` — reusable test data or setup.

## General principles

Tests MUST belong to the Python project and verify owned behavior/invariants, not mirror empty modules, passive declarations, or unchanged framework behavior.
Tests SHOULD prefer real code, temporary files, and explicit fixtures, minimizing mocks/stubs/patches to exercise integration.
They SHOULD use public boundaries, including end-to-end coverage when practical; owning-module tests MAY directly test private helpers.

Tests MUST NOT use networks or user-specific files, or modify Docker configuration/runtime parameters.
They SHOULD be deterministic under controlled inputs/environment.
Time tests SHOULD use a current-time baseline unless specific calendar/timezone values matter, avoiding incidental date constraints.

Required state MUST be prepared at test start or through class/module autouse fixtures.
Application-owned state MUST be prepared/mutated through production transitions, not directly, except with developer approval documented beside the bypass and explaining why production code cannot produce that state.
The shared settings-isolation fixture MAY replace static configuration with a fresh binding: production initialization deliberately cannot clear or replace labels.
It MUST use `pytest-mock` to restore the prior binding even on failure; its tests MUST exercise real initialization/access.
Tests MAY inspect application state directly but MUST NOT clean up shared application-owned state unless explicitly requested.

Test-scoped process changes MUST be restored before completion, regardless of the shared-state cleanup restriction, including:

- cwd.
- environment.
- mutable globals/registries.
- context variables.
- installed configuration.
- replaced collaborators/mocks.

**Example:** Restore a test's cwd while retaining shared application files unless cleanup was requested.

Execution MUST use Docker-backed helpers: normally `./bin/dev-tests.sh`; targeted runs MAY use `./bin/dev.sh uv run pytest <path>`.

## Test placement

Tests SHOULD live in the nearest owning package's `tests` subpackage, retaining nested component ownership when clearer.
Files MUST use `test_<module>.py`.
Integration tests MAY belong to the exercised public boundary; CLI tests SHOULD belong to their CLI package.
**Example:** `example/paths.py` maps to `example/tests/test_paths.py`; no example module is required.

Reusable test utilities SHOULD be owned as follows:

- `make` — Small valid-data factories; no assertions or verification.
- `helpers` — No ordinary constructors fitting `make`; owns:

  - Setup.
  - Assertions.
  - Workflows.
  - Permitted cleanup.

Constructors MUST NOT contain assertions.
`make` MUST NOT contain assertions or behavior-verification helpers; `helpers` MUST NOT contain ordinary constructors fitting `make`.
Reusable pytest fixtures MUST live in the owner's `fixtures` module.
Tests MAY reuse another module's test utilities for non-owned setup or integration; reuse MUST remain test-only and production MUST NOT import them.
Directly re-exported functions MUST have behavior tests at their implementation owner.

## Test organization

Tests SHOULD group by subject for discoverable coverage.
Every production module-level function MUST have a test class; production classes SHOULD have one subject to passive/inherited-behavior exclusions.
Classes MUST use `Test<PascalCaseSubject>`, grouping all method tests inside.
Method cases MUST use `test_<snake_case_method>__<snake_case_behavior>`; module-function cases MAY use `test_<case>`.
Test-only helpers need no test class.
Standalone tests SHOULD be limited to package invariants/infrastructure without a natural function/class owner.

**Example:** `normalize_path` has `TestNormalizePath.test_empty_value`; class method `normalize` uses `test_normalize__empty_value`.

Each possible execution path MUST have a method or parametrized case, including:

- success/defaults.
- empty/invalid inputs.
- handled errors.
- warnings.
- individual branches.

Tests MUST cover corner cases, including:

- boundaries.
- empty collections/strings.
- missing optionals.
- duplicates.
- unsupported/malformed values.
- missing paths.
- normalization.
- repeated calls exposing state leaks.

Cases SHOULD follow contracts or observed failures, not hypothetical requirements.
Orthogonal behaviors SHOULD have separate cases to identify failures clearly.

## Entity and error tests

### Entity tests

Tests MUST verify owned behavior/invariants and SHOULD cover:

- field/model constraints.
- non-trivial defaults/factories.
- normalization.
- methods/computed properties.
- serialization/deserialization.
- invalid-value rejection.

Tests MUST NOT merely verify:

- passive construction/field assignment.
- plain `NewType`.
- enum existence.
- passive containers without owned behavior/compatibility contracts.

They SHOULD NOT repeat unchanged shared-base behavior and MUST NOT repeat inherited Pydantic behavior or inspect annotations merely to restate declarations.
Passive-only modules SHOULD omit meaningless test files.
Entity tests MUST NOT access filesystems or test external presentation/CLI rendering.
Low-level validation tests MAY assert `pydantic.ValidationError`.

### Error tests

Tests SHOULD verify custom behavior and translation at producing boundaries.
Error unit tests SHOULD exist only beyond inherited construction/static declarations, covering custom:

- construction.
- code computation.
- message formatting.
- validation/normalization.
- detail derivation.
- intermediate-class behavior.

They MUST NOT merely assert unchanged static values/constructor fields and SHOULD NOT repeat inherited error behavior.
Optional `test_errors.py` SHOULD be omitted when producers cover all meaningful behavior.
Exact production messages MUST NOT be asserted unless behavior specs make them stable contracts.

Boundary tests SHOULD verify expected low-level errors, including external-input Pydantic failures, become returned environment errors.
Producer tests SHOULD assert failure type and relevant context fields.
Code propagation tests SHOULD compare against the owning error's declaration; literal code assertions MUST require an independently specified compatibility contract.
Composition tests SHOULD cover:

- complete-list propagation.
- success.
- short-circuiting.
- unrelated raised exceptions.

Unexpected-failure tests MUST verify failure persists, not successful/empty/fallback recovery.
Stored-state integrity failures MUST NOT be tested as expected caller-correctable input errors.

## Behavior coverage

Behavior specs define capability contracts; architecture specs define conventions.
Tests SHOULD cover implemented, runtime-testable examples/rules, without introducing capabilities to satisfy checklists.
Changes to runtime code SHOULD be verified by tests covering affected behavior.
Changes limited to specifications, documentation, or static-analysis configuration MAY omit runtime tests when no runtime behavior is affected.
Typing SHOULD use static analysis/review/architecture checks rather than annotation-inspecting unit tests.
Only dedicated broad-convention architecture tests MAY inspect annotations.

Configuration tests MUST verify owned entity/loading/setup behavior and SHOULD cover:

- discovery/explicit selection.
- input structure.
- environment parsing.
- non-trivial defaults.
- path normalization.
- invalid configuration.
- initialization failures.

They MUST NOT merely verify unchanged literal defaults; passive-only configuration modules SHOULD omit meaningless tests.

CLI tests SHOULD execute commands to cover integrated:

- command forms/wiring.
- argument/option parsing and validation.
- protocol selection.
- record shape/order.
- warnings.
- errors/exits.

Delegated error-boundary tests SHOULD cover:

- inherited/aggregated exits.
- stdout in every protocol.
- explicit streams.
- diagnostic order.
- propagation of unexpected exceptions/malformed unwrap payloads.

They SHOULD verify documented fatal-error representations and successful exits for warnings alone.
Warning tests MUST follow production architecture without test-only storage/delivery channels.

Implemented parsing/stateful tests SHOULD cover applicable:

- inputs/normalization.
- malformed data.
- expected external failures.
- persisted changes/error states.
- idempotency.
- retries.
- public-boundary coordination.

## Fixtures and mocking

Data SHOULD be minimal, short inputs inline, and filesystem fixtures temporary.
Reusable files MAY improve readability.
Expected normalized paths SHOULD use forward slashes for consistency.

Ordinary collaborator replacement SHOULD use scoped `pytest-mock` and patch the lookup location:
`mocker.patch("<import.path>", ...)` for imported names/settings; `mocker.patch.object(...)` for available objects/classes.
Direct `MagicMock`/`AsyncMock` MUST be limited to local fakes passed into subjects.
Ordinary attribute replacement SHOULD NOT use `monkeypatch`, keeping standard cleanup/assertions.
Explicit fakes SHOULD replace mocks when clearer.
Specialized boundary tools MAY be used without networks.

## Assertions

Shared automation extraction MUST validate UUID4 ids, remove only `id` from record copies, and preserve all other fields/order without mutating input; empty input MUST yield an empty list.
Shared error assertions MUST reuse it, checking count/order/native diagnostics with `message` moved to `content`.
This covers errors without guidance whose context retains native JSON representation.
Consumers SHOULD reuse helpers while owning parsing/filtering/policies.
Shared projection tests MUST retain independent expected payloads.

Tests SHOULD prefer structured assertions and parse machine-readable output.
Exact rendering SHOULD be asserted only for stable public/persisted contracts; selected lines/fields/records MAY be asserted otherwise.
Required changed and unchanged state MUST both be verified.
Persistence tests MUST verify contracted affected counts, isolate responsible operations, and supplement counts with structured content assertions when content matters.
Public-count tests MAY verify cardinality through that operation.
Exclusive branches SHOULD assert positive and negative outcomes; log-based branch tests MUST check expected counts and zero mutually exclusive events.
Identity assertions MUST NOT be used except for `None`; booleans MUST use `assert condition`/`assert not condition`.
