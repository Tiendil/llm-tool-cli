# Shared command-line setup and options

## Goal of the document

This document describes shared application setup, invocation options, and output protocol selection.

## Scope

This specification covers reusable application setup and global command-line option behavior.
Command execution, configuration loading, and output-cell layouts are out of scope.

## Application identity

The application MUST initialize its process-wide tool label before command-line parsing or shared sequence rendering.
The label MUST preserve its exact string value, including whitespace and an empty string.
The label MUST remain separate from parsed invocation options and MUST NOT be obtained from workspace configuration.
Reading an uninitialized label MUST raise an internal exception.
Repeated initialization with the same label MUST succeed without changing it.
Initialization with a different label MUST raise an internal exception and preserve the installed label.

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

An unsupported value MUST stop execution before the command runs, write one LLM error cell to stderr, and exit with status `1`.
The cell MUST use the initialized application tool label, the diagnostic code `invalid_arguments`, and a `reason` identifying the rejected value and the accepted values.
The fallback MUST always use LLM output because the requested protocol is invalid.
Supplying the option without a value MUST remain a framework command-line parsing error.

## Invocation context

The library MUST retain parsed global options for the invocation and make them available from its root command and nested subcommands.
Storing options MUST replace the invocation's previous global options without changing unrelated context data.
Retrieval MUST return the stored options without changing them or resolving their configuration path.
When the context contains no recognized global options, retrieval MUST return options with both protocol and configuration path unspecified, without storing the fallback.
Independent invocations MUST NOT share retained options.

**Example:** A protocol and configuration path supplied to the root command remain available inside a nested command group.
A later invocation without those options receives unspecified values instead of inheriting the earlier choices.

## Protocol selection

An explicit protocol MUST take precedence over command defaults.
When no protocol is specified, the command named `skill` MUST select `llm` and all other command names MUST select `human`.
The library MUST own both defaults and the selection rule.
Selection MUST leave the stored options unchanged and MUST NOT retain a previous command's default.

**Example:** With no explicit protocol, printing a skill document selects LLM output, while the next version command selects human output.
An explicit `human` protocol selects human output for the skill command as well.
