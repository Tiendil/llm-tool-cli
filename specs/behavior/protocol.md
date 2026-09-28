# Shared output protocol support

## Goal of the document

This document defines shared output protocol names, output cells, cell and error formatting, JSON Lines serialization, and direct text writing.

## Scope

This specification covers reusable protocol mechanics for callers that construct and render output.
Consumer-specific records and journal layouts, command parsing, defaults, error classification, exit status selection, and command execution are out of scope.

## Output protocols

The library MUST provide the stable output protocol values `human`, `llm`, and `automation`.
Consumers MUST select their own defaults and project application data into cells or their own records.
Shared formatter selection MUST support each protocol and raise an internal exception with the supplied mode when the mode is unsupported.

## Output cells

A cell MUST carry:

- a UUID identifier, generated as a new UUID version 4 when omitted.
- a consumer-defined kind.
- an optional media type.
- optional textual content.
- string-keyed metadata, empty by default.

Cells MUST use the shared entity validation and copying conventions.
General cell construction MUST accept consumer-defined kinds and media types rather than a closed library-owned set.
The compact cell identifier MUST be the URL-safe Base64 encoding of the UUID bytes without padding.

Cell construction helpers MUST support general cells, metadata-only cells, and Markdown cells.
Metadata-only construction MUST set both media type and content to absent.
Markdown construction MUST use `text/markdown` as the media type.
The helpers MUST collect additional named metadata into the cell's metadata mapping.
They MUST raise an internal exception when content is supplied without a media type, including when the supplied content is an empty string.
Cell construction MUST NOT render or write output.

Cell shortcuts MUST construct Markdown cells for informational messages, successful operations, and failed operations with the respective kinds `info`, `operation_succeeded`, and `operation_failed`.
They MUST use the supplied message as content and collect additional named metadata through the shared cell construction behavior.
They MUST support empty messages and omitted metadata.

Metadata values MUST support strings, integers, booleans, null values, and lists of strings.
Conversion of arbitrary values to metadata MUST preserve values of those types, including empty lists, and use their string representation for other values.
Conversion MUST NOT strip string whitespace or recursively convert unsupported collections.

**Example:** A list of strings remains a list, while a mixed list or a floating-point value becomes its string representation.

## Cell formatting

Formatters MUST return UTF-8 bytes, including the required record terminators.
They MUST NOT write output, choose streams, classify errors, or select exit statuses.
Formatting MUST NOT mutate the cell.
Text cell boundaries MUST use the caller-supplied tool label without changing it.
The label MUST NOT affect automation records or error formatting.

### Human and LLM cells

Text formatting MUST emit the cell kind, then the media type when present, then metadata in sorted key order.
Metadata values MUST use their string representation, including `True`, `False`, and `None` for boolean and null values.
Nonempty content MUST follow a blank line and have surrounding whitespace stripped.
Absent or empty content MUST omit that content section.

Human cells MUST begin with `----- <label> CELL <id> -----`, using the compact cell identifier.
Fields MUST use `key = value` lines.
Each human cell MUST end with two newlines.

LLM cells MUST begin with `--<label>-CELL <id> BEGIN--` and end with `--<label>-CELL <id> END--`, using the compact cell identifier.
Fields MUST use `key=value` lines.
Each LLM cell MUST end with one newline after its closing boundary.

### Automation cells

Automation cells MUST use the shared JSON Lines serialization.
Each record MUST include `id` and `content` fields together with metadata as top-level fields.
The `id` field MUST default to the compact cell identifier.
Nonempty content MUST have surrounding whitespace stripped; absent or empty content MUST become JSON null.
The formatter MUST NOT automatically add the cell kind, media type, or tool label.

Metadata named `id` MUST override the generated identifier in the record.
The cell content MUST override metadata named `content`.
These precedence rules preserve the existing flattened record contract.

## Error formatting

Human and LLM error formatting MUST return the shared environment error's formatted message followed by a newline.
Automation error formatting MUST serialize the shared error's native diagnostic record as one JSON Line, without a cell envelope or tool label.
Error formatting MUST preserve the error's diagnostic fields and MUST NOT translate the error into a consumer-specific type.

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
