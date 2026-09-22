# Test architecture

## Goal of the document

This document describes test organization, behavior coverage, and test isolation for the library and repository tooling.

## Scope

This specification applies to automated tests of Python library code and repository development helpers.
Exact test-runner configuration, CI implementation, and performance benchmarks are out of scope.
Exact fixture names and package publishing checks are also out of scope.

## Dictionary

- `unit test` — a test focused on one module or a small group of closely related functions or entities.
- `integration test` — a test that checks multiple modules through a public boundary.
- `fixture` — test data or setup used by one or more tests.

## General principles

Tests MUST be written as part of the Python project.
Tests MUST verify observable behavior or invariants owned by the subject under test.
Tests MUST NOT be introduced only to mirror an empty module, passive declaration, or unchanged framework behavior.

Tests SHOULD prefer real project code, temporary files, and small explicit fixtures over mocked collaborators.
Tests SHOULD minimize mocking, stubbing, and monkeypatching so coverage exercises real integration behavior.
Tests SHOULD prefer end-to-end coverage through public boundaries when practical so tests verify that cooperating modules satisfy their public contracts.
Tests SHOULD exercise other modules through their public boundaries.
Tests of an owning module MAY use functionality from that module, including directly exercising a private helper as the subject of its required test class.

Tests MUST NOT depend on network access or user-specific files.
Tests MUST NOT modify Docker configuration or runtime parameters.
Tests SHOULD be deterministic for the same inputs and controlled environment.
Tests SHOULD prefer a real current-time baseline for time-related cases when the exact calendar date is not part of the behavior under test, so incidental dates do not constrain the case.
Hard-coded calendar datetimes SHOULD be used only when their specific calendar values or timezone boundaries are relevant to the tested behavior.

Tests that require specific state MUST prepare it explicitly at the start of the relevant test or with an autouse fixture at the test class or test module level.
Tests MUST prepare and mutate application-owned state through the production code that owns the corresponding state transition and invariants.
Tests MUST NOT bypass production logic by writing directly to application-owned state unless the developer explicitly approves the exception.
An approved exception MUST be documented next to the bypass and MUST explain why the required state cannot be produced through production code.
Tests MAY inspect application-owned state directly to assert observable effects; this permission does not allow direct mutation.
Tests MUST NOT clean up shared application-owned state after themselves unless the developer explicitly requests cleanup behavior.

Changes to process state MUST be scoped to the test and restored before the test ends.
The shared-state cleanup restriction MUST NOT be used to skip restoring test-scoped process state.
Process state includes:

- the working directory.
- environment variables.
- mutable global state and registries.
- context variables.
- installed configuration.
- replaced collaborators and mocks.

**Example:** A test that updates shared application-owned files restores its working directory before ending, while the shared files remain available unless cleanup was requested.

Development-related test execution MUST use the project's Docker-backed helpers.
The normal complete test command is `./bin/dev-tests.sh`.
Targeted pytest runs MAY use `./bin/dev.sh uv run pytest <path>`.

## Test placement

Library tests SHOULD live in a `tests` subpackage of the nearest package that owns the tested behavior.
Test file names MUST use the `test_` prefix followed by the tested module's name.
Nested component tests SHOULD remain with their component when this makes ownership clear.
Cross-module integration tests MAY live under the module that owns the public boundary being exercised.
CLI integration tests SHOULD live under the package that owns the CLI boundary so its public behavior and tests share an owner.

**Example:** Tests for `llm_tool_cli/example/paths.py` would belong in `llm_tool_cli/example/tests/test_paths.py` if that module were introduced.
This example does not require an `example` module.

Reusable test-object constructors SHOULD live in the owning test package's `make` module.
The `make` module SHOULD contain small factories for valid test data so setup remains explicit and reusable.
The `make` module MUST NOT contain assertions or behavior-verification helpers.
Constructors MUST NOT contain assertions.
Reusable setup, assertion, and workflow helpers SHOULD live in the owning test package's `helpers` module.
Cleanup helpers for permitted cleanup SHOULD live there with the other test workflow utilities so their ownership is clear.
The `helpers` module MUST NOT contain ordinary test-data constructors when those constructors fit the `make` module.
Tests MAY reuse constructors, fixtures, and helpers from another module's `tests` package to avoid duplicating non-owned setup or to support integration coverage.
Cross-module test helper reuse MUST remain test-only.
Production code MUST NOT import test helpers.

Behavior tests for a function re-exported without a wrapper MUST live with the module that owns its implementation.

## Test organization

Tests SHOULD be grouped around the tested function or class.
Each production module-level function MUST have a corresponding test class.
Each production class SHOULD have a corresponding test class so its owned behavior is discoverable together, subject to the exclusions for passive declarations and unchanged inherited behavior below.
Test classes MUST use `Test<SubjectName>` naming, where `<SubjectName>` is the tested function or class name converted to PascalCase.
Tests for a class MUST group its method tests inside that class's test class.
Tests for a class method MUST use `test_<method_name>__<case>` naming.
The method name MUST be the tested method name in snake case.
The case name MUST describe the execution path or behavior being verified in snake case.
These grouping and naming conventions make coverage discoverable from production subjects.
Tests for one module-level function MAY use `test_<case>` inside its test class.
Test-only helper functions do not need corresponding test classes.
Standalone tests SHOULD be used only for package-level invariants or infrastructure contracts that do not naturally belong to one function or class, so subject-owned behavior remains grouped with its subject.

**Example:** A function named `normalize_path` has a `TestNormalizePath` test class whose cases can use names such as `test_empty_value`.
A class method named `normalize` uses case names such as `test_normalize__empty_value` inside its class's test class.

Every possible execution path of a tested function or method MUST have a corresponding test method or parametrized test case.
Execution paths include:

- successful paths.
- default-value paths.
- empty-input paths.
- invalid-input paths.
- handled error paths.
- warning-producing paths.
- branch-specific paths.

Tests MUST cover corner cases for each tested function or method.
Corner cases include:

- boundary values.
- empty collections and empty strings.
- missing optional values.
- duplicate values.
- unsupported values.
- malformed input.
- paths that do not exist.
- values that require normalization.
- repeated calls that may reveal state leaks.

Boundary cases SHOULD follow from the capability's contract or observed failures rather than hypothetical future requirements.
Orthogonal behaviors SHOULD have separate test cases so failures identify the broken contract.

## Entity and error tests

### Entity tests

Entity tests MUST verify behavior or invariants owned by the entity.
Entity tests SHOULD cover the following owned behavior so validation and representation contracts are checked at their source:

- field constraints and field validation.
- model validation.
- non-trivial defaults and default factories.
- normalization.
- methods and computed properties.
- serialization and deserialization.
- rejection of invalid values.

Entity tests MUST NOT assert that constructor arguments appear unchanged in passive fields.
Entity tests MUST NOT verify simple model construction when the entity has no custom behavior or constraints.
Entity tests MUST NOT verify plain `NewType` declarations, enum member existence, or passive data-container fields unless they verify non-trivial owned behavior or compatibility contracts.
Entity tests SHOULD NOT repeat behavior inherited unchanged from a shared base entity, so inherited behavior is tested at its owner.
Tests MUST NOT repeat inherited Pydantic behavior or inspect annotations merely to restate a declaration.
For modules containing only passive entities, omitting a matching test file SHOULD be preferred over adding meaningless tests.
Entity tests MUST NOT require filesystem access, because entity behavior is required to remain independent of filesystem operations.
Entity tests MUST NOT verify external presentation or CLI rendering.
Low-level entity validation tests MAY assert `pydantic.ValidationError` as permitted by the error architecture.

### Error tests

Error tests SHOULD verify customized behavior and failure translation at the boundary that produces it.
Error-class unit tests SHOULD be added only for behavior beyond inherited construction and static declarations, so producing-boundary tests remain the source of evidence for ordinary failures.
Such tests SHOULD cover customized behavior when present, including:

- constructor logic.
- error-code computation.
- message formatting.
- validation or normalization.
- structured detail derivation.
- behavior added by an intermediate error class.

Error tests MUST NOT assert only that static codes, messages, or constructor fields are present unchanged.
Error tests SHOULD NOT repeat unchanged error inheritance or shared base-error behavior, so each behavior is tested at its owner.
A module-level `tests/test_errors.py` file is optional and SHOULD be omitted when producing-function or entity tests already cover all meaningful error behavior.
Exact production error message text MUST NOT be asserted in ordinary unit tests unless a behavior specification declares that text as a stable external contract.

Tests for exception boundaries SHOULD verify that expected low-level failures are raised as library-specific exceptions, including `pydantic.ValidationError` from external input, so consumers receive the documented failure contract.
Tests for produced errors SHOULD assert the expected exception type, stable error code, and relevant structured fields through the producing boundary so they verify usable failures rather than static declarations.
Tests for unexpected failures MUST verify that the operation remains failed rather than recovering with a successful, empty, or fallback result.
Tests for stored-state integrity failures MUST NOT classify those failures as expected caller-correctable input errors.

## Behavior coverage

Behavior specifications define expected capability contracts.
Architecture specifications define expected project-wide conventions.
Tests SHOULD cover specification examples and rules when the corresponding behavior is implemented and runtime-testable, so implementation coverage remains connected to its requirements.
Coverage requirements apply to implemented library responsibilities and do not require introducing capabilities solely to satisfy a test checklist.

Static typing requirements SHOULD be enforced by static analysis, code review, or dedicated architecture checks rather than ordinary unit tests that inspect runtime annotations, so unit tests remain focused on runtime behavior.
Tests MAY inspect annotations only in dedicated architecture tests that validate a broad project-wide convention.

Configuration tests MUST verify behavior owned by the configuration entity or loading and setup boundary.
Tests for implemented configuration behavior SHOULD cover the following cases so configuration failures are detected at their owning boundary:

- discovery and explicit configuration selection.
- supported input structure.
- environment variable parsing.
- non-trivial defaults.
- path normalization.
- invalid configuration failures.
- initialization failures.

Configuration tests MUST NOT merely verify unchanged literal default assignments when no custom behavior exists.
For modules containing only passive configuration declarations, omitting a matching test file SHOULD be preferred over adding meaningless tests.

CLI integration tests SHOULD exercise implemented library-owned CLI behavior through command execution so parsing, wiring, and presentation are verified together.
Coverage SHOULD include the following implemented responsibilities:

- command forms and wiring.
- argument and option parsing and validation.
- output protocol selection.
- structured output shape and ordering.
- warnings.
- errors and exit behavior.

When the library owns a delegated CLI error boundary, tests SHOULD verify fatal-error exit categories and the default non-zero exit code for unmapped library exceptions so the mapping preserves failure classification.
Tests SHOULD verify that fatal errors use the boundary's documented error representation so consumers can recognize them.
Tests SHOULD verify that warnings alone do not cause a non-zero exit code when the operation otherwise succeeds, so non-fatal problems remain distinct from failure.
Warning tests MUST follow the specified warning architecture and MUST NOT introduce warning storage or delivery channels solely for testing.

Tests for implemented parsing and stateful operations SHOULD cover the following contracts when present so external data and state transitions are verified at their owners:

- supported inputs and their normalization.
- malformed input.
- expected external-system failures.
- persisted state changes and error states.
- idempotency of repeated calls.
- retry behavior.
- coordination across module public boundaries.

## Fixtures and mocking

Test data SHOULD be as small as possible while preserving the behavior under test.
Short external inputs SHOULD be inline; reusable fixture files MAY be used when they improve readability.
Filesystem tests SHOULD use test-created temporary directories.
Fixture paths SHOULD use forward slashes in expected normalized identifiers so expectations use a consistent normalized representation.

When ordinary Python collaborators must be replaced, tests SHOULD use the `pytest-mock` fixture for scoped replacement and call assertions.
Patches SHOULD target the name as it is looked up by the subject under test.
Use `mocker.patch("<import.path>", ...)` for imported module-level collaborators and settings.
Use `mocker.patch.object(...)` when replacing an attribute on an object or class already available in the test.
Direct `unittest.mock.MagicMock` and `unittest.mock.AsyncMock` MUST be used only for local fake objects or callables passed into the code under test.
Tests SHOULD NOT use pytest `monkeypatch` for ordinary Python attribute replacement, so replacement uses the standard mocking fixture's cleanup and call assertions.
Small explicit fakes SHOULD be preferred over mocks when they make collaborator behavior easier to understand.
Tests MAY use specialized testing tools for their own domain boundaries, subject to the network restriction.

## Assertions

Tests SHOULD assert structured values before rendered text when structured data is available.
Tests for machine-readable output SHOULD parse that output before asserting its contents.
Rendered output tests SHOULD assert exact output only for stable public or persisted-state contracts so incidental wording does not become an accidental contract.
Rendered output tests MAY assert selected lines, fields, or records when exact text is outside the relevant specification.
Tests MUST verify both changed state and required unchanged state when those effects are part of the operation's contract.
Persistence operation tests MUST verify affected-record counts when cardinality is part of the contract.
Assertions about persisted effects MUST isolate the operations responsible for those effects.
Count assertions MUST supplement structured assertions about persisted content when record contents are part of the behavior under test.
Tests whose subject is a public count operation MAY verify cardinality through that operation.
Tests SHOULD assert both positive and negative outcomes when a branch excludes another branch so contradictory effects cannot pass unnoticed.
Tests that verify branch-specific behavior through log events MUST assert expected event counts and zero occurrences of mutually exclusive branch events.

Tests MUST NOT use identity assertions except for `None` checks.
Boolean checks MUST use `assert condition` or `assert not condition` rather than identity comparisons.
