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
- `errors` for module-owned exception types.
- `utils` for small technical helpers without a more specific owner.
- `tests` for colocated tests of module behavior.
- `tests.make` for reusable test-object constructors.
- `tests.helpers` for reusable test setup and behavior-verification helpers.

These submodules are optional unless the applicable architecture requires them for an implemented responsibility.
A module that defines expected fatal errors MUST provide an `errors` submodule as required by the error architecture.
An implementation MUST NOT introduce them solely for layout symmetry.

## Import boundaries

Public import boundaries MUST be explicit enough to distinguish supported interfaces from implementation details.
A public import boundary MAY be a package root or a declared public submodule.
Package initializers SHOULD re-export names only when doing so improves the supported interface and keeps ownership clear.
An initializer with no public names MAY remain empty.

Cross-module production dependencies MUST use declared public boundaries.
Implementation submodules inside the same owning module MAY import each other directly.
Production code MUST NOT import tests, test helpers, or repository development scripts.

Configured module boundaries MUST reflect implemented ownership and dependency direction.
New modules MUST update the architecture configuration when their addition changes a configured boundary.
