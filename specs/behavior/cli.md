# Shared command-line setup and options

## Goal of the document

This document describes shared application setup, invocation options, output protocol selection, command error handling, and built-in documentation and version commands.

## Scope

This specification covers reusable application setup and shared command-line behavior.
Consumer-specific command execution, configuration loading, and output-cell layouts are out of scope.

## Application setup

The library MUST construct independently configurable applications using the consumer's help description.
Each application MUST be a command group with shared global options registered at its root, even when it has only one command.
The library MUST retain parsed global options as framework inputs before the selected command executes, without loading configuration or selecting a command's default protocol at the root.
Consumers MUST retain ownership of application-specific command registration and startup.
`-h` and `--help` MUST display generated help and exit successfully at the root and subcommand levels.
Help MUST describe registered commands, arguments, and options using the framework's normal text output.
Help MUST NOT require project configuration.

The root application MUST expose `--show-completion` and `--install-completion` using the framework's shell integration.
Showing completion MUST print a script without installing it.
Installing completion MUST require explicit invocation of the installation option.
Application construction and ordinary command execution MUST NOT install completion.
Completion MUST include registered command names, options, and declared document choices.

## Application identity

The application MUST initialize immutable static configuration containing its tool label in the execution context used for command-line parsing or shared sequence rendering, before either operation.
The label MUST preserve its exact string value, including whitespace and an empty string.
The label MUST remain separate from parsed invocation options and MUST NOT be obtained from workspace configuration.
Reading uninitialized static configuration MUST raise an internal exception.
Static configuration MAY also declare the application's default configuration filename; project setup MUST require it, while parsing and rendering MUST remain independent of it.
Repeated initialization with identical static settings MUST succeed without changing them.
Initialization with a different label MUST raise an internal exception and preserve the installed label.
Initialization with a different configuration filename MUST likewise fail and preserve the installed settings.

**Example:** An unsupported protocol can produce an error cell with the application's label before its root command callback runs.

## Global options

Global options MUST distinguish an explicitly selected protocol from an unspecified protocol.
They MUST carry an optional configuration file path without expanding home markers, resolving the path, or checking the filesystem.
An absent configuration path MUST remain absent for later configuration selection.

## Configuration option

`--config PATH` MUST be an optional global option accepted before the subcommand.
Its value MUST be parsed as a filesystem path, preserving home markers and relative paths for shared configuration resolution.
Omission MUST leave the configuration path unspecified.
Parsing MUST NOT expand home markers, resolve the path, or check its existence, file type, or readability.
Filesystem validation and its diagnostics MUST belong to the configuration operation that uses the path.
An unusable configuration path MUST NOT prevent execution of a command that does not use configuration.
An option supplied without a value MUST remain a command-line parsing error.

**Example:** A directory supplied as `--config PATH` reaches configuration loading and produces a shared configuration diagnostic.
A command that only prints a version can run with that same option because it does not use configuration.

## Protocol option

`-p PROTOCOL` and `--protocol PROTOCOL` MUST be aliases for one optional global option accepted before the subcommand.
Accepted values MUST be the exact, case-sensitive names of the shared output protocols.
Omission MUST leave the protocol unspecified for command-default selection.
Help MUST identify the option value as `PROTOCOL` and describe the accepted values and shared command defaults.

An unsupported value MUST stop execution before the command runs, write one LLM error cell to stdout, and exit with status `1`.
The cell MUST use the initialized application tool label and the shared invalid-argument diagnostic, with a `reason` identifying the rejected value and the accepted values.
The fallback MUST always use LLM output because the requested protocol is invalid.
Supplying the option without a value MUST remain a framework command-line parsing error.

## Invalid-argument diagnostics

The library MUST provide a shared environment-error value for explicit argument-validation failures, including invalid protocol values and consumer-owned argument checks.
It MUST use the stable code `invalid_arguments` and a textual `reason` field.
Its formatted message MUST be the reason, using the shared environment-error normalization and serialization rules.
Diagnostic construction MUST NOT select an output protocol or stream, write output, or terminate the process; those responsibilities belong to the handling CLI boundary, which MUST use the error class's declared exit status.
Framework parsing failures MUST retain their existing framework diagnostics unless explicitly handled by a shared option or command.

## Invocation context

Command setup MUST establish immutable context-scoped runtime settings owning the effective output protocol, independently of the CLI framework and project availability.
Project settings MUST have their own independent binding and MUST require an absolute active configuration path.
The project directory MUST be derived from that path, never initialized independently.
All configuration entities MUST be complete when constructed and immutable thereafter.
Unresolved CLI configuration input MUST remain separate from project settings.
Shared project contexts MUST construct and bind project settings after successful configuration loading and validation, including after creation, and retain them around project-dependent execution and output.
Commands that do not use configuration MUST NOT establish project settings, even when `--config` is supplied.
A failed loading or creation operation MUST NOT replace an existing project binding with the failed candidate.
Application-specific loaded configuration MUST remain separate from these shared settings.

Each command context MUST establish fresh runtime settings without changing unrelated framework context data.
The preceding runtime binding, including an absent binding, MUST be restored when the framework command context closes, including after command errors and early exits.
Consumer setup MUST register shared project contexts with the framework command context so project bindings are restored when it closes.
Runtime readers, including output writing, MUST consult the active settings rather than retained copies.
Constructing a command context MUST NOT resolve configuration paths, load a workspace, or emit output.
The context MUST bind fresh shared output delivery independently of project settings and submit supplied cell iterables to the active emitter, using stdout by default.
The preceding output binding MUST be restored when the framework context closes.
Successful command completion MUST flush buffered results followed by warnings before runtime and project bindings close.
The shared skill and version commands MUST use this context; consumers MAY extend it with application-specific responsibilities.
Explicit function arguments remain permitted for operations that receive values directly.

## Protocol selection

An explicit protocol MUST take precedence over command defaults.
When no protocol is specified, the invoked command named `skill` MUST select `llm` and all other command names MUST select `human`.
The library MUST own both defaults and the selection rule.
Selection MUST publish the effective protocol in runtime settings before command execution.

**Example:** With no explicit protocol, printing a skill document selects LLM output, while the next version command selects human output.
An explicit `human` protocol selects human output for the skill command as well.
Invalid-protocol diagnostics MUST use static application identity and the explicit LLM fallback without requiring runtime or project settings.

## Skill command

The shared `skill [DOCUMENT]` command MUST use the consumer's packaged documents and declared document choices.
The consumer's choices MUST include `usage`.
Omitting the document argument MUST select `usage`.
Explicit document names MUST match the supplied choices exactly and case-sensitively.
Help and shell completion MUST use the same document choices as validation.
Unknown names MUST remain framework argument errors with exit status `2`, before document loading.
The command MUST NOT load workspace configuration or require a consumer command context.

The command MUST select its protocol through the shared invocation options and command-default rule.
It MUST load the selected packaged document and write one skill cell to stdout, exiting with status `0`.
The cell MUST carry Markdown content, kind `skill`, and metadata `type = skill` and `document` naming the selected document.
Document contents MUST remain consumer-owned and use the existing shared cell normalization and formatting.

A document read failure MUST use shared command error handling to emit the `skill_unreadable` diagnostic and exit with status `3`.
Unexpected exceptions MUST propagate without being converted to expected read failures.

## Version command

The shared `version` command MUST report the installed version of the consumer-supplied distribution.
It MUST look up package metadata when the command executes, without caching the version during registration.
Registration and help MUST NOT require the distribution's metadata to be available.
The command MUST NOT accept positional arguments or command-specific options.
It MUST NOT load workspace configuration or require a consumer command context.

The command MUST select its protocol through the shared invocation options and command-default rule.
It MUST write one shared metadata-only version cell to stdout and exit with status `0`.
The cell MUST contain the installed version string using the shared version-cell contract.
Help MUST describe printing the installed package version without consumer-specific wording.

Metadata lookup failures, including missing distribution metadata, MUST propagate without being converted to environment-error cells or successful fallback output.

## Command error handling

The library MUST provide a shared error-handling scope for command execution using an already selected protocol.
It MUST recover only failed result unwrapping, using the validated environment-error accessor from the shared result contract.
It MUST report every recovered error in order as one batch of shared error cells and terminate with the aggregated exit status.
Error cells MUST use the emitter's configured stream, defaulting to stdout in every protocol, independently of the error's package ownership.
Malformed unwrapping payloads MUST propagate unchanged without partial diagnostic output.
Unrelated exceptions and framework control-flow exceptions MUST propagate unchanged.
Successful execution MUST flush the active emitter and leave the scope without forcing process termination.
Expected failures MUST discard buffered ordinary results, report diagnostics, and flush retained warnings after them.
Unexpected exceptions and framework exits MUST NOT flush pending ordinary results.

The same reporting and termination operation MUST be available for explicit error lists, including argument validation before command execution.
Early validation MUST supply its chosen fallback protocol; the reporter MUST use the same stream and exit rules as command failures without consuming an unrelated outer emitter.
Command failure reporting MUST use the command's emitter so its retained warnings follow diagnostics.
An empty error list MUST emit no diagnostics and terminate with the shared aggregation result.

Shared commands MUST use this error-handling scope.
Consumers MUST retain application-specific workspace construction, runtime setup, error journaling, and cleanup.
Consumer journaling MAY observe failures before propagating them to the shared handler and MUST NOT cause duplicate error-cell emission.

## Exit statuses

Shared successful execution MUST use status `0`.
Expected failures MUST use the exit status declared by their environment-error class.
The defaults MUST be `1` for explicit shared invalid-argument diagnostics, `2` for configuration errors, and `3` for other environment errors, including unreadable skill documents.
Error subclasses MUST inherit their parent class's status unless they declare an override.
A CLI handling multiple environment errors MUST render all errors in their original order and use the highest declared status, independently of error order.
An empty list or a list whose errors all declare status `0` MUST produce status `0`.
Exit-status aggregation MUST be provided by the shared core error contract.
Framework parsing failures MUST retain status `2`; they MUST NOT be changed to status `1` merely to use shared exit statuses.
Consumers MAY declare application-specific error-class overrides; emitter configuration and process termination MUST remain at the handling CLI boundary.
