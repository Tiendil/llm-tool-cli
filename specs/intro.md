# LLM Tool CLI specification overview

## Goal of the document

This document indexes the project's specifications and their purposes.

## Scope

The specification index and its maintenance; detailed product requirements are out of scope.

## Index requirements

The index MUST list every specification with its path and a brief description.
Each description MUST identify the specification's stable subject or purpose rather than enumerate its contents.
Descriptions MUST NOT list individual requirements or current implementation details.
Descriptions SHOULD remain accurate when details change within the specification's existing scope.
The index MUST be kept complete and accurate when specifications are added, removed, or change scope.

**Example:** Describe a configuration specification as “The project configuration contract,” without listing its current configuration fields.

## Specification directories

- `specs/` — all specifications, used by specification-governance rules.
- `specs/architecture/` — library architecture.
- `specs/behavior/` — observable contracts at library and CLI boundaries.
- `specs/documentation/` — repository documentation requirements.
- `specs/meta/` — specification-writing requirements.

## Specification documents

- `specs/intro.md` — Index of project specifications.
- `specs/dictionary.md` — Shared project terminology.
- `specs/meta/general.md` — Requirements for specification content and presentation.
- `specs/meta/behavior.md` — Rules for expressing observable behavior in specifications.
- `specs/architecture/modules_layout.md` — Ownership boundaries within the library and between the library and its consumers.
- `specs/architecture/python.md` — Python implementation conventions.
- `specs/architecture/entities.md` — Conventions for modeling project data.
- `specs/architecture/errors.md` — Conventions for representing and propagating diagnostics.
- `specs/architecture/tests.md` — Requirements for verifying project behavior.
- `specs/behavior/cli.md` — Contracts for reusable command-line application support.
- `specs/behavior/config.md` — Contracts for reusable configuration support.
- `specs/behavior/protocol.md` — The shared output protocol contract.
- `specs/behavior/paths.md` — The shared contract for interpreting project paths.
- `specs/behavior/skills.md` — The contract for loading packaged skill documentation.
- `specs/documentation/readme.md` — Requirements for the root README.
- `specs/documentation/changelog.md` — Requirements for maintaining the project changelog.
