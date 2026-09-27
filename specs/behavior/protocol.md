# Shared output protocol support

## Goal of the document

This document defines shared output protocol names, JSON Lines serialization, and direct text writing.

## Scope

This specification covers reusable protocol mechanics for callers that construct their own output.
Record schemas, cells, rendering layouts, command parsing, defaults, error classification, exit status selection, and command execution are out of scope.

## Output protocols

The library MUST provide the stable output protocol values `human`, `llm`, and `automation`.
Consumers MUST select their own defaults and interpret each protocol through their own renderers.

## JSON Lines serialization

Serialization MUST accept one string-keyed mapping representing a caller-owned record and return text containing one JSON object followed by one newline.
It MUST preserve the supplied record fields without adding an envelope or presentation metadata.
It MUST sort object keys, preserve Unicode characters, escape embedded newlines, and use compact separators without optional whitespace.
Nested JSON values and empty records MUST be supported.
Values unsupported by the JSON encoder MUST propagate the encoder's exception.

## Text writing

Text writing MUST use the current standard output stream unless the caller selects the standard error stream.
The stream MUST be selected on each call so replaced streams work without a binary buffer interface.
Writing MUST preserve supplied text, including empty text, surrounding whitespace, and existing newlines.
It MUST NOT add a newline, flush explicitly, or change the stream's encoding.
Callers MUST supply any required line or record terminators.
Stream failures MUST propagate to the caller.
