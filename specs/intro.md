# LLM Tool CLI specification overview

## Goal of the document

This document lists LLM Tool CLI specification documents and specification directories, and briefly describes their purpose.

## Scope

The scope of this specification is limited to the specification index.
Detailed requirements for individual specifications are out of scope except for brief descriptions needed to keep the index useful.

## Specification directories

- `specs/` contains all project specifications used by depmesh governance rules.
- `specs/architecture/` contains specifications related to package ownership, Python conventions, entities, errors, and tests.
- `specs/behavior/` contains specifications for library capability contracts.
- `specs/documentation/` contains specifications related to repository documentation artifacts.
- `specs/meta/` contains specifications related to requirements for specification documents.

## Specification documents

- `specs/intro.md` is this file and indexes all specification documents.
- `specs/dictionary.md` defines project terminology shared by multiple specifications and dependency metadata rules.
- `specs/meta/general.md` defines general rules for project specification documents.
- `specs/meta/behavior.md` defines the content and abstraction level of behavior specifications, separating observable contracts from implementation interfaces.
- `specs/architecture/modules_layout.md` describes package organization, package initializer responsibilities, shared pytest fixture ownership and distribution, public import boundaries including shared global CLI options, typed configuration-option parsing, shared protocol-option construction and diagnostics, and protocol-default selection, canonical identifier checking, component extraction, mixed path normalization and resolution, shared filesystem path types and configuration interfaces, shared protocol utilities, output-cell base ownership, protocol-specific output cells and rendering contexts, the logic-cell package with separate base and content modules and consumer-owned projections, shared typed environment-error cells and deferred diagnostic projection, consumer ownership, and shared result infrastructure; Typer dependency ownership is managed by the shared library; shared application construction, skill-command registration, and the shared exit-code enum are also defined here.
- `specs/architecture/python.md` describes Python typing, result-based validation, and class conventions.
- `specs/architecture/entities.md` describes entity modeling, typed data conventions including static typing suppressions, and validation and serialization boundaries.
- `specs/architecture/errors.md` describes independent internal-exception and environment-error hierarchies, result propagation with typed unwrap-error recovery, warnings, and consumer presentation boundaries.
- `specs/architecture/tests.md` describes test organization, result and failure coverage, reusable pytest fixture placement, and settings isolation with an approved private-state reset.
- `specs/behavior/cli.md` describes shared configuration and protocol-option parsing with LLM invalid-protocol diagnostics, deferred filesystem validation, parsed global options, and shared command protocol defaults with explicit-option precedence; shared application setup covers help, completion, and skill-command behavior.
- `specs/behavior/config.md` describes configuration discovery, path resolution, initialization target selection, TOML loading and schema validation, exclusive creation from text or packaged templates, and shared failure diagnostics.
- `specs/behavior/protocol.md` describes shared output protocols, output cell construction and common message, skill-document, and version shortcuts with default successful-operation record metadata, logic-cell construction and projections, metadata conversion, unified sequence rendering and cell writing with protocol selection, position, total, caller-supplied labels and stream selection, and typed environment-error cells with corrective guidance, compact Unicode JSON Lines serialization, and direct text writing.
- `specs/behavior/paths.md` describes lexical project-path identifiers, canonical identifier checks and component extraction, mixed identifier and filesystem normalization and resolution with home expansion, explicit normalization bases, absolute-input restrictions, filesystem containment and conversion, and failure diagnostics.
- `specs/behavior/skills.md` describes packaged UTF-8 skill-document loading and shared read-failure diagnostics, with module ownership and public interfaces defined in `specs/architecture/modules_layout.md`; loading remains independent of the shared CLI command.
- `specs/documentation/readme.md` describes the content and tone of the brief root README.
- `specs/documentation/changelog.md` describes Changy source files, version-record structure, and entry formatting.
