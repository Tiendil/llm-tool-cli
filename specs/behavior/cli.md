# Shared command-line options

## Goal of the document

This document describes shared invocation options, their availability within an invocation, and command output protocol selection.

## Scope

This specification covers reusable behavior for parsed global command-line options.
Argument parsing, command execution, configuration loading, and output rendering are out of scope.

## Global options

Global options MUST distinguish an explicitly selected protocol from an unspecified protocol.
They MUST carry an optional configuration file path without expanding home markers, resolving the path, or checking the filesystem.
An absent configuration path MUST remain absent for later configuration selection.

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
