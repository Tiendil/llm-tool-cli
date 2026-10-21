# README documentation

## Goal of the document

This document describes the content and tone of the repository's brief README.

## Scope

This specification applies to the root `README.md`.
Detailed capability contracts, package metadata, and agent workflow instructions are out of scope.

## Content

The README MUST start with one h1 heading containing the project name.
It MUST briefly explain the library's purpose and current development status.
It MUST NOT present proposed runtime behavior or commands as available functionality.

The README MUST address developers building CLI tools with the library.
Its main content MUST follow the topic order below.
It MUST NOT contain installation or repository-development sections.

### Introduction

The introduction MUST explain that the library provides reusable foundations for Python CLI tools used by humans, LLM agents, and automation.
It MUST clarify that the library has no standalone CLI entry point.
It MUST link to existing projects that use the library.
It MUST describe the library's current stage as a personal project of [Tiendil](https://tiendil.org).

### Goals

The README MUST include a `Goals` section stating these aims:

- Provide the ability to quickly construct tools targeted at specific tasks for AI agents.
- Experiment with approaches to improve the usability of CLI tools for agents.
- Unify the behavior of Tiendil’s tools.

### Capabilities

The capabilities section MUST describe the following high-level concepts and the problems they solve for tool developers:

- CLI application foundations.
- unified output for humans, agents, and automation.
- configuration management.
- project filesystem operations.
- journaling and diagnostics.
- scoped application resources.

Concept descriptions MUST NOT enumerate individual Python APIs, helper operations, or implementation details.
The section MUST also list the reusable CLI subcommands provided by the library, with a brief purpose for each.
It MUST clarify that applications register these commands using application-supplied data.

### Output protocols

The README MUST introduce `human`, `llm`, and `automation` before explaining data flow.
It MUST explain the intended audience for each mode and how an invocation selects its protocol.

### Data flow

The README MUST introduce domain code as the application logic performing the tool's tasks independently of CLI parsing and output formatting.
It MUST define the emitter as the shared output service managing buffering, rendering, and writing.
The README MUST explain these stages before the quick-start example:

- CLI command invocation.
- parsing options and arguments and selecting a command.
- command setup selecting the effective protocol and establishing the emitter.
- domain code constructing logical cells.
- the emitter buffering pending logical cells.
- delivery projecting logical cells into output cells for the selected protocol.
- output cells formatting the prepared data.
- the emitter writing formatted output to its stream.

It MUST distinguish submission from delivery and explain that pending ordinary cells are projected and formatted at delivery.
It MUST describe delivery timing for ordinary results, warnings, and journals, including immediate journals overtaking earlier buffered results.
It MUST explain that journal messages keep agents informed about progress during long operations while final results are still pending.

### Error handling

The section MUST lead with the distinction between internal errors and environment errors, explaining their meanings and their representation as raised exceptions and structured diagnostics, respectively.
It MUST build the explanation of propagation and CLI behavior on this distinction and briefly cover:

- optional lists of corrective approaches in environment errors, their inclusion in rendered diagnostics, and their use by agents for automatic recovery.
- environment errors propagated through `Result`.
- conversion to diagnostic logical cells and exit-status selection at the CLI boundary.
- suppression of pending ordinary results on command failure.
- non-fatal warnings and their delivery.
- propagation of internal errors and other unexpected exceptions.

It MUST link to the error and CLI specifications for detailed contracts.

### Scoped resources

The README MUST explain independent typed resource bindings, access to active values, and temporary scopes that restore previous bindings.
It MUST explain that domain code can access bindings independently of the CLI layer and that explicit function arguments remain valid.
It MUST distinguish these configuration lifetimes:

- application identity initialized before CLI parsing.
- invocation settings and an independently bound output emitter.
- selected project settings established after successful configuration validation and unnecessary for projectless commands.

It MUST distinguish shared project-location settings from application-owned configuration schemas and loaded settings.
It MUST explain that applications choose scopes for their own resources without a fixed hierarchy or a requirement to prepare unused resources.
It MUST clarify that binding an object does not construct, copy, or clean it up, and that accessing an unset required binding raises an internal error.
It MUST link to the context architecture and project-scoping contract for details.

### Reusable configuration elements

The README MUST explain composing application-owned schemas from independently reusable shared fields and configuration blocks alongside custom settings.
It MUST briefly describe:

- configuration-version validation and diagnostics.
- session-directory path validation.
- optional external journal forwarding, disabled by default.

It MUST clarify that applications choose which elements to adopt and own their supported versions, defaults, and session storage.
It MUST include a compact schema example combining shared elements with a custom setting and link to the configuration contract for details.

### Quick start

The README MUST include one small, complete, runnable CLI example showing:

- application identity initialization and application creation.
- a domain function producing a logical cell.
- a command using the shared command context and emitter.
- automatic output delivery on successful completion.

The initial example MUST work without project configuration or custom journal setup.
The README MUST show invocations and corresponding output for the same example command in `human`, `llm`, and `automation` modes.

### Integration

The README MUST briefly introduce the following extension points:

- custom logical cells.
- custom output cells.
- application-owned configuration schemas.
- scoped resources.
- journal delivery.

It MUST link to `specs/intro.md` and the relevant capability specifications for deeper contracts.

## Examples

Examples MUST use implemented public interfaces and supported command syntax.
The README MUST also reference existing tools that consume the library, with links to their repositories or relevant integration code.
References MUST identify the shared capability they illustrate without treating application-specific behavior as a library guarantee.

## Style

The README SHOULD remain short, practical, and accurate about implementation status.
Concepts MUST be introduced before examples rely on them.
