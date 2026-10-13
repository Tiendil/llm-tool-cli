# Shared output protocol support

## Goal of the document

This document defines shared output protocol names, output cells, logic-cell rendering, cell formatting and environment-error cells, JSON Lines serialization, and emitter-owned batch rendering and scoped delivery of results, warnings, and journal events.

## Scope

This specification covers reusable protocol mechanics for callers that construct and render output.
Consumer-specific records and journal layouts, command parsing, exit status selection, and application command execution are out of scope.

## Output protocols

The library MUST provide the stable output protocol values `human`, `llm`, and `automation`.
Consumers MUST project application data into cells or their own records.
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
The successful-operation shortcut MUST default to `type = operation_succeeded` metadata when the caller omits it.
Explicit caller metadata MUST retain precedence over that default.

The configuration-creation shortcut MUST construct a protocol-independent Markdown content cell with kind `operation_succeeded` and content `Configuration created.`.
It MUST include `type = operation_succeeded` and the string representation of the caller-supplied configuration path as `path` metadata in every protocol.
It MUST NOT resolve, validate, read, or create the supplied path.

The skill-document shortcut MUST construct a protocol-independent Markdown content cell with kind `skill`.
It MUST use the caller-supplied document name as `document` metadata, include `type = skill` metadata, and use the supplied document text as content.
It MUST accept application-defined document names and empty content without loading resources or selecting a protocol.

The version shortcut MUST construct a protocol-independent metadata-only cell with kind `version`.
It MUST include `type = version` and the caller-supplied version string as `version` metadata, with no media type or content.
It MUST preserve the supplied string without parsing it or looking up package metadata.

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

Callers whose data produces one cell with the same payload in every protocol MUST be able to reuse shared uniform projection behavior.
Uniform projection MUST produce exactly one output cell of the selected protocol's type, preserving the supplied kind, media type, content, and metadata before final formatting.
Each projection MUST recompute the output cell without retaining identifiers or cached projections.

**Example:** The same dependency data can become one grouped Markdown output cell for a text protocol and several metadata-only output cells for automation.

## Cell formatting

Each output cell MUST render itself as UTF-8 bytes, including the required record terminators, without selecting a protocol again.
Rendering MUST NOT write output, choose streams, classify errors, or select exit statuses.
Formatting MUST NOT mutate the cell.
Rendering context MUST provide the cell's zero-based position, the total number of output cells in the supplied sequence, and a tool label.
The position MUST be nonnegative and smaller than the positive total.
The standard output-cell types MUST preserve their boundaries for both single-cell and multiple-cell sequences.
Text cell boundaries MUST use the rendering context's tool label without changing it.
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
Stream routing and exit status selection MUST belong to the calling CLI boundary.

## JSON Lines serialization

Serialization MUST accept one string-keyed mapping representing a caller-owned record and return text containing one JSON object followed by one newline.
It MUST preserve the supplied record fields without adding an envelope or presentation metadata.
It MUST sort object keys, preserve Unicode characters, escape embedded newlines, and use compact separators without optional whitespace.
Nested JSON values and empty records MUST be supported.
Values unsupported by the JSON encoder MUST propagate the encoder's exception.

## Output delivery

Output delivery MUST have an independent scoped binding, usable without a project and replaceable by programmatic callers.
Ordinary cells MUST be buffered until an explicit flush or successful command completion.
Warnings MUST be buffered separately and follow ordinary results in warning insertion order, without deduplication.
Explicit cell construction MUST be able to override journal and warning defaults independently when the cell supports those values.
Cells without a journal representation MUST be able to prohibit journal delivery; generic content cells MUST prohibit it.
Construction MUST reject attempts to enable prohibited journal delivery.
Requesting unsupported journal conversion MUST raise an internal error rather than derive a message from rendered content.
Disabling a delivery flag MUST change routing rather than suppress the cell.
Delivery flags MUST NOT appear in serialized journal records or cell payloads.

While the emitter's journal processor has not failed, journal processing MUST occur synchronously when a journal-marked cell is submitted, before its console delivery or buffering.
Each processor call MUST receive a new shared journal record converted from the submitted logical cell.
Conversion MUST use only the cell's data, without accessing application contexts or performing I/O.
Journal messages MUST concisely describe the event or result represented by the cell, including useful identifiers or counts, independently of its stdout content.
Conversion MUST NOT render an output cell or copy document bodies, action instructions, or result listings into the journal record.
Structured attributes MUST provide useful event context rather than duplicate the full stdout payload.
Explicit journal messages and diagnostic messages MAY remain the journal message when they already describe the event or problem.
The record MUST contain a message, a timestamp, an optional actor, and optional structured attributes.
Its dictionary representation MUST flatten attributes alongside the common fields, preserving the common fields on name collisions and excluding delivery flags.
Existing journal-cell timestamps MUST be preserved; other records MUST receive their creation timestamp during submission rather than flushing.
Explicit message journaling MUST use an emitter-configured cell factory, defaulting to the shared journal cell.
The emitter MUST infer an omitted actor as `agent` for LLM output and the protocol name otherwise; an explicit actor, including null, MUST take precedence.
Direct submission of constructed cells MUST NOT invoke the factory.
Successful journal processing MUST be followed immediately by console delivery unless the cell is also marked as a warning.
Cells marked as both journal and warning MUST be processed immediately and delivered to the console with the final warnings.
The default processor MUST succeed without external effects and MUST NOT suppress console journal output.
A failed processor MUST prevent delivery of the affected cell and stop processing subsequent cells in that submission.
The emitter MUST detect failure from the processor's failed result, regardless of the contained error types or whether the error list is empty, and propagate that result unchanged.
After that failure, the emitter MUST skip journal conversion and processing for all subsequent submissions during its lifetime while preserving immediate journal console delivery and deferred warning delivery.
Flushing or discarding buffered cells MUST NOT re-enable journal processing; another emitter MUST have independent failure state.
Flushing MUST NOT repeat journal processing.

Ordering MUST be preserved within immediate journal output, buffered ordinary output, and buffered warnings.
Immediate journal output MAY precede ordinary output submitted earlier.
A flush MUST render the final batch before writing any part of it, clear consumed buffers, and flush the written stream.
The emitter MUST own batch rendering, using the active runtime protocol and reading the initialized application label once per batch.
It MUST flatten logical-cell projections in input order, calculate positions and totals for the complete output-cell sequence, and concatenate rendered bytes without additional separators.
A single output cell MUST receive position zero and total one; empty batches and empty projections MUST produce no output text.
The emitter MUST decode the complete batch as UTF-8 before writing, preserving framing, Unicode content, and record terminators.
Rendering and decoding failures MUST propagate before any text is written; stream failures MUST also propagate.
A failed stream write MUST propagate without automatic replay.
An emitter MUST deliver all cell kinds to one text stream selected during construction, using current stdout by default in every protocol.
The default stream MUST be resolved at each delivery so replaced streams work without a binary buffer interface.
Stream writing MUST preserve the rendered text without adding newlines or changing the stream's encoding.
Individual submissions MUST NOT select a stream. Immediate journal delivery MUST flush the same stream.
The emitter MUST leave stream closure to its caller.

**Example:** Submitting a result, a journal event, a second result, and a warning produces the journal event immediately, followed at flush by both results and the warning.

Logical-cell string fields MUST use the shared entity normalization, stripping surrounding whitespace while retaining internal whitespace and line breaks.
Compact journal text MUST escape backslashes, carriage returns, and line feeds to retain a single physical output line without truncating messages.
Automation journal records MUST retain the normalized logical-cell values and use ordinary JSON escaping.
A cell's journal flag MUST NOT replace its own presentation with compact journal formatting.

The external command processor MUST execute an argument list directly without a shell and capture subprocess output.
Whole arguments enclosed in braces MUST resolve to fields in the journal record's dictionary representation; embedded placeholder-like text MUST remain literal.
Missing or null field values MUST become empty arguments, preserving their positions in the argument list without requiring field declarations.
Date and time values MUST use ISO formatting, and other values MUST use their string representation.
Multiline string arguments MUST retain the normalized journal-record values; destination-specific processors MAY apply their own formatting without mutating records.
Empty commands MUST return `journal_command_config_invalid`.
An operating-system execution failure or nonzero exit MUST return `journal_command_failed` with command, return code when available, and diagnostic details.
Successful external processing MUST NOT copy subprocess stdout into console output.
