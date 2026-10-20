# Shared command-line setup and options

## Goal of the document

This document describes shared command-line application support.

## Scope

Reusable application setup and CLI behavior; consumer command execution, configuration schemas/loading mechanics, and cell layouts are out of scope.

## Application setup

Applications MUST be independently configurable command groups using consumer help, even with one command.
Root options MUST retain parsed inputs without loading configuration or choosing command defaults.
Applications MUST be able to register custom commands before execution.
Root/subcommand `-h`/`--help` MUST show framework text describing commands/arguments/options and exit successfully without configuration.

Root `--show-completion` MUST print a shell script; `--install-completion` MUST install only when explicitly invoked.
Construction/ordinary execution MUST NOT install completion.
Completion MUST include registered commands, options, and document choices.

## Application identity

Immutable static identity MUST be initialized before parsing/shared rendering, preserving exact labels including whitespace/empty text.
It MUST remain separate from invocation/workspace settings.
Unset access MUST raise an internal exception.
An optional static default filename MUST be required for project setup, not parsing/rendering.
Identical initialization MUST succeed unchanged; conflicting labels or filenames MUST raise internal errors without replacing settings.
**Example:** Invalid-protocol output can use the label before the root callback runs.

## Global options

Options MUST distinguish explicit/unspecified protocol and retain optional unresolved configuration input.
Absent paths MUST remain absent for later selection.

## Configuration option

Global `--config PATH` MUST precede the subcommand and parse filesystem paths without:

- home expansion.
- resolution.
- existence checks.
- kind checks.
- readability checks.

Configuration-dependent operations MUST validate paths and report their diagnostics when used.
Unusable paths MUST NOT prevent configuration-independent commands.
Missing option values MUST remain parsing errors.
**Example:** A directory reaches configuration loading for diagnosis but does not prevent a version command.

## Protocol option

Global `-p PROTOCOL`/`--protocol PROTOCOL` MUST be aliases preceding the subcommand.
Values MUST match shared protocol names exactly/case-sensitively; omission MUST remain unspecified.
Help MUST use `PROTOCOL` and describe accepted values/defaults.

Invalid values MUST stop before execution, emit one LLM error cell on stdout, and exit `1`.
The cell MUST use initialized identity and the shared invalid-argument diagnostic, with a reason naming rejected/accepted values.
This fallback MUST always be LLM and require no runtime/project settings.
Missing option values MUST remain framework parsing errors.

## Invalid-argument diagnostics

Explicit validation, including consumer checks, MUST report an invalid-argument diagnostic with textual `reason` as its formatted message under the Environment-error cells contract in `specs/behavior/protocol.md`.
Construction MUST NOT:

- select protocol.
- select stream.
- output.
- terminate.

The CLI boundary MUST use the declared error exit status.
Unadapted framework parsing MUST retain its diagnostics.

## Invocation context

Command setup MUST expose a complete effective protocol without requiring a framework context or an active project.
An active project MUST identify an absolute configuration path and its parent root.
Project preparation MUST follow the Project scopes contract in `specs/behavior/config.md`, preserving the selected project through dependent execution and output.
Projectless commands MUST NOT establish an active project even with `--config`.

Each command MUST start with fresh output state without changing unrelated caller context.
Command closure MUST restore the caller's preceding protocol, project, and output state, including absence, after success, failure, or early exit.
Preparing command support without entering execution MUST NOT resolve paths, load workspaces, or emit.
Output MUST default to stdout and honor the command's effective protocol throughout execution.

Successful completion MUST deliver results then warnings before command closure.
Skill, version, and init MUST follow the same completion and failure behavior as custom commands.
Error reporting MUST NOT require consumer runtime resources to remain active.

## Protocol selection

Explicit protocol MUST win; otherwise command named `skill` MUST use LLM, all others human.
The effective protocol MUST be available to the caller before execution.
**Example:** Skill defaults to LLM, version to human; explicit human overrides skill's default.

## Skill command

`skill [DOCUMENT]` MUST use consumer choices/resources, including `usage` as the omitted-argument default.
Document retrieval MUST follow `specs/behavior/skills.md`.
Validation/help/completion MUST share exact case-sensitive choices.
Unknown names MUST fail through the framework with exit `2` before loading.
The command MUST NOT require workspace configuration or application-specific runtime preparation.

Protocol selection MUST follow the Protocol selection contract above.
Success MUST emit one stdout Markdown cell with kind/type `skill` and selected `document`, using consumer content and shared normalization/formatting, then exit `0`.
Read failures MUST use shared skill-read diagnostics and exit `3`; unexpected exceptions MUST propagate.

## Version command

Version MUST look up the supplied distribution's installed metadata during execution, never cache it at registration.
Registration/help MUST NOT require metadata.
No positional arguments or command-specific options MUST be accepted.
It MUST NOT require workspace configuration or application-specific runtime preparation.
Protocol selection MUST follow the Protocol selection contract above; success MUST emit one metadata-only version cell to stdout and exit `0` under `specs/behavior/protocol.md`.
Help MUST describe installed-version printing without consumer-specific wording.
Lookup failures, including missing metadata, MUST propagate without error cells or successful fallback.

## Initialization command

Init MUST use:

- the consumer schema.
- the consumer template.
- optional consumer help.
- the static filename.

Registration/help MUST NOT prepare projects or require existing configuration.
No positional arguments or command-specific options MUST be accepted.
Initialization MUST use invocation cwd and optional unresolved input, create/validate before exposing the project or reporting success, and retain the project through output.
Failed validation MUST leave the created file without replacing the caller's active project.
Success MUST emit one creation cell with the active path under the selected protocol and `specs/behavior/protocol.md`.
Expected failures MUST follow Command error handling below without success output; unexpected exceptions MUST propagate.
Application-specific runtime preparation MUST NOT be required.

## Command error handling

Command error reporting MUST use an already selected protocol and accept only valid failed-result payloads.
Malformed payload failures MUST propagate unchanged before any partial diagnostics; unrelated/framework control-flow exceptions MUST also propagate.

Reported errors MUST render in original order under the Environment-error cells contract in `specs/behavior/protocol.md` and terminate with aggregated status.
Command error reporting MUST NOT forward diagnostics to journals or create journal records.
Reporting MUST preserve the original error list without mutation.
Errors MUST use the emitter stream, default stdout in every protocol regardless of package ownership.

Success MUST flush without forced termination.
Expected failure MUST suppress pending ordinary results, report errors, then deliver warnings.
Unexpected exceptions/framework exits MUST NOT flush pending ordinary results.

Explicit error-list reporting MUST offer the same stream/exit behavior, including before command execution.
Early validation MUST use a supplied fallback protocol without consuming another command's pending output.
Command failure MUST preserve that command's pending warnings.
Empty error lists MUST emit nothing and terminate according to the Exit statuses contract below.

Skill, version, and init MUST follow this error-handling contract.

## Exit statuses

Success MUST use `0`; expected failures MUST use each diagnostic's declared exit status, with these defaults unless overridden:

- Explicit shared invalid arguments — status `1`.
- Configuration errors — status `2`.
- Other environment errors, including unreadable skills — status `3`.

Exit-status aggregation MUST choose the highest declared status independently of order, preserving diagnostic order.
Empty/all-zero lists MUST yield `0`.
Framework parsing MUST retain `2`, not become `1` merely for uniformity.
Consumers MAY declare diagnostic exit-status overrides; command termination MUST occur only at the CLI boundary.
