# Shared output protocol support

## Goal of the document

This document defines shared output protocol names, output cells, logic-cell rendering, cell formatting and environment-error cells, JSON Lines serialization, and direct text writing.

## Scope

This specification covers reusable protocol mechanics for callers that construct and render output.
Consumer-specific records and journal layouts, command parsing, defaults, error classification, exit status selection, and command execution are out of scope.

## Output protocols

The library MUST provide the stable output protocol values `human`, `llm`, and `automation`.
Consumers MUST select their own defaults and project application data into cells or their own records.
Logic-cell projections MUST support each protocol and choose the corresponding output-cell type.

## Output cells

An output cell MUST contain prepared content and metadata and own final rendering for its selected protocol.
It MUST carry:

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
Output cell construction MUST NOT render or write output.

Cell shortcuts MUST construct Markdown cells for informational messages, successful operations, and failed operations with the respective kinds `info`, `operation_succeeded`, and `operation_failed`.
They MUST return protocol-independent content logic cells using the caller-supplied message and additional named metadata.
They MUST support empty messages and omitted metadata.

The skill-document shortcut MUST construct a protocol-independent Markdown content cell with kind `skill`.
It MUST use the caller-supplied document name as `document` metadata, include `type = skill` metadata, and use the supplied document text as content.
It MUST accept application-defined document names and empty content without loading resources or selecting a protocol.

Metadata values MUST support strings, integers, booleans, null values, and lists of strings.
Conversion of arbitrary values to metadata MUST preserve values of those types, including empty lists, and use their string representation for other values.
Conversion MUST NOT strip string whitespace or recursively convert unsupported collections.

**Example:** A list of strings remains a list, while a mixed list or a floating-point value becomes its string representation.

## Logic cells

A logic cell MUST hold the consumer data needed to produce output cells for a selected protocol.
Rendering MUST select the consumer-defined projection for that protocol and return an ordered list of zero or more output cells of the corresponding protocol-specific type.
Each supported protocol MUST have an explicit projection; consumers MAY share projection logic when the desired cell payloads are the same.
Consumers MUST own domain-specific projection payloads and ordering; shared logic cells MUST own their common projection contracts.
Rendering MUST leave the input data unchanged and MUST NOT load files, execute commands, or write output.
Output identifiers MUST belong to the produced output cells, independently of the logic cell.
Repeated rendering MUST recompute output cells rather than reuse cached output cells.
Callers with already prepared content MUST be able to use a shared content logic cell that projects the same kind, media type, content, and metadata into one output cell for each protocol.
Content logic cells MUST support metadata-only output and reject content without a media type, including empty content.
They MUST NOT retain generated output identifiers or cached projections.
Application cell-emission boundaries MUST accept logic cells; output-cell construction belongs to their projections.

**Example:** The same dependency data can become one grouped Markdown output cell for a text protocol and several metadata-only output cells for automation.

## Cell formatting

Each output cell MUST render itself as UTF-8 bytes, including the required record terminators, without selecting a protocol again.
Rendering MUST NOT write output, choose streams, classify errors, or select exit statuses.
Formatting MUST NOT mutate the cell.
Rendering context MUST provide the cell's zero-based position, the total number of output cells in the supplied sequence, and the caller's tool label.
The position MUST be nonnegative and smaller than the positive total.
Sequence rendering MUST accept logic cells and a selected protocol, flatten their projections in input order, calculate positions and totals for the complete output-cell sequence, and concatenate the rendered bytes without additional separators.
An empty sequence MUST produce empty bytes; a single cell MUST receive position zero and total one.
The standard output-cell types MUST preserve their boundaries for both single-cell and multiple-cell sequences.
Text cell boundaries MUST use the caller-supplied tool label without changing it.
The label MUST NOT affect automation records.

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
Rendering MUST NOT automatically add the cell kind, media type, or tool label.

Metadata named `id` MUST override the generated identifier in the record.
The cell content MUST override metadata named `content`.
These precedence rules preserve the existing flattened record contract.

## Environment-error cells

The library MUST provide an environment-error logic cell that retains the concrete structured error, including its typed context and corrective guidance, until projection.
Construction MUST NOT serialize the error or prepare output content.
Each projection MUST produce one output cell with kind `error` and media type `text/markdown`, using the ordinary rendering path.
The error's formatted message MUST become cell content rather than duplicated `message` metadata, without adding an introductory prefix.
Corrective guidance MUST be formatted against the error and have surrounding whitespace stripped.
One fix MUST follow the message on a new line prefixed with `Way to fix: `.
Multiple fixes MUST follow a blank line, the heading `Ways to fix:`, and another blank line, with each fix prefixed by `- ` on its own line.
Absent guidance MUST add no text.
The same content and metadata MUST be used for all supported protocols.
The remaining native diagnostic record fields, including `type = error`, `code`, and serialized context, MUST become metadata through the shared metadata conversion rules.
Construction MUST leave the error unchanged, retain its native code, and exclude private causes and message templates.
Optional null context MUST be retained according to the native diagnostic record contract.
Error cells MUST use ordinary cell identifiers, framing, serialization, and sequence rendering in every protocol.
The core environment-error model MUST remain independent of cell construction and rendering.
Stream routing and exit status selection MUST remain consumer-owned.

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
