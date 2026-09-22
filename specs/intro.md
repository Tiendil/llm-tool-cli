# LLM Tool CLI specification overview

## Goal of the document

This document lists LLM Tool CLI specification documents and specification directories, and briefly describes their purpose.

## Scope

The scope of this specification is limited to the specification index.
Detailed requirements for individual specifications are out of scope except for brief descriptions needed to keep the index useful.

## Specification directories

- `specs/` contains all project specifications used by depmesh governance rules.
- `specs/architecture/` contains specifications related to package ownership, Python conventions, entities, errors, and tests.
- `specs/documentation/` contains specifications related to repository documentation artifacts.
- `specs/meta/` contains specifications related to requirements for specification documents.

## Specification documents

- `specs/intro.md` is this file and indexes all specification documents.
- `specs/dictionary.md` defines project terminology shared by multiple specifications and dependency metadata rules.
- `specs/meta/general.md` defines general rules for project specification documents.
- `specs/architecture/modules_layout.md` describes package organization, public import boundaries, and consumer ownership.
- `specs/architecture/python.md` describes Python typing, validation, and class conventions.
- `specs/architecture/entities.md` describes entity modeling, typed data conventions including static typing suppressions, and validation and serialization boundaries.
- `specs/architecture/errors.md` describes library exceptions and warnings, including failure classification and consumer presentation boundaries.
- `specs/architecture/tests.md` describes test organization, required behavior coverage, and test isolation.
- `specs/documentation/readme.md` describes the content and tone of the brief root README.
- `specs/documentation/changelog.md` describes Changy source files, version-record structure, and entry formatting.
