# Shared output protocol support

## Goal of the document

This document defines shared output protocol names, output cells, JSON Lines serialization, and direct text writing.

## Scope

This specification covers reusable protocol mechanics for callers that construct their own output.
External record schemas, rendering layouts, command parsing, defaults, error classification, exit status selection, and command execution are out of scope.

## Output protocols

The library MUST provide the stable output protocol values `human`, `llm`, and `automation`.
Consumers MUST select their own defaults and interpret each protocol through their own renderers.

## Output cells

A cell MUST carry:

- a UUID identifier, generated as a new UUID version 4 when omitted.
- a consumer-defined kind.
- an optional media type.
- optional textual content.
- string-keyed metadata, empty by default.

Cells MUST use the shared entity validation and copying conventions.
Kinds and media types MUST remain consumer-defined rather than a closed library-owned set.
The compact cell identifier MUST be the URL-safe Base64 encoding of the UUID bytes without padding.

Cell construction helpers MUST support general cells, metadata-only cells, and Markdown cells.
Metadata-only construction MUST set both media type and content to absent.
Markdown construction MUST use `text/markdown` as the media type.
The helpers MUST collect additional named metadata into the cell's metadata mapping.
They MUST raise an internal exception when content is supplied without a media type, including when the supplied content is an empty string.
Cell construction MUST NOT render or write output.

Metadata values MUST support strings, integers, booleans, null values, and lists of strings.
Conversion of arbitrary values to metadata MUST preserve values of those types, including empty lists, and use their string representation for other values.
Conversion MUST NOT strip string whitespace or recursively convert unsupported collections.

**Example:** A list of strings remains a list, while a mixed list or a floating-point value becomes its string representation.

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
