# LLM Tool CLI dictionary

## Goal of the document

This document defines project terminology shared by multiple specifications and dependency metadata rules.

## Scope

The scope of this specification is limited to project-specific terminology.
Detailed behavior, implementation requirements, and configuration schemas are out of scope.

## Terms

Terms defined in this section are stable project vocabulary.
Project artifacts MUST use these terms when referring to the corresponding concepts and MUST preserve them while their definitions remain accurate.
A dictionary term MAY be renamed only when its existing name or definition has become incorrect or ambiguous.

- `library` — the reusable Python distribution named `llm-tool-cli`, imported as `llm_tool_cli`.
- `consumer` — an application that imports the library to support its own CLI behavior.
- `capability` — reusable behavior provided by the library through a documented public contract.
- `public contract` — a documented interface or behavior that library callers can rely on.
- `module boundary` — a declared public Python import boundary and its allowed dependencies, enforced by Tach where configured.
- `CLI boundary` — an interface that connects library operations to command-line input, output presentation, or process exit behavior.
- `semantic primitive type` — a Python type that distinguishes the library-specific meaning of a primitive value.
- `expected failure` — a failure anticipated by the called operation's documented contract for which the caller has a defined response.
- `unexpected failure` — a failure outside expected operational conditions, including programming defects, violated internal invariants, or stored-state integrity failures.
- `warning` — a non-fatal problem discovered while processing a request that can still produce useful requested output.
- `specification` — a Markdown document under `specs/` that describes expected behavior, architecture, terminology, or documentation rules.
- `architecture test` — a test that verifies a project-wide structural rule or convention defined by an architecture specification.
- `development helper` — a repository command under `bin/` used to develop, verify, or release the library.
- `Donna workflow` — a Markdown workflow artifact executed by Donna to coordinate development work.
- `changelog fragment` — a Markdown file under `changes/` consumed by Changy.
