# Shared output protocol support

## Goal of the document

This document describes the shared output protocol contract.

## Scope

Reusable output mechanics; consumer-specific records/journal layouts, command parsing/execution, and exit selection are out of scope.

## Output protocols

Stable protocols MUST be `human`, `llm`, and `automation`.
Logical-cell projections MUST support every protocol and MAY produce different representations for each protocol.

## Output cells

Output cells MUST represent prepared output data, carrying:

- UUID id, defaulting to a new UUID4.
- consumer-defined kind.
- optional media type.
- optional text.
- string-keyed metadata, defaulting empty.

Kinds/media types MUST remain consumer-extensible.
Compact ids MUST be URL-safe Base64 UUID bytes without padding.

Construction MUST support general, metadata-only, and Markdown cells, collecting named metadata.
Metadata-only cells MUST omit content/media type; Markdown MUST use `text/markdown`.
Content without media type, including empty text, MUST raise internally.
Construction MUST NOT render/write.

Metadata conversion MUST preserve:

- strings.
- integers.
- booleans.
- nulls.
- string lists, including empty lists.

It MUST stringify everything else without stripping strings or recursively converting collections.

**Example:** String lists remain lists; mixed lists/floats become strings.

## Logic cells

Logic cells MUST hold projection data and render an ordered list of zero or more selected-protocol output cells through explicit projections.
Consumers MUST be able to define application payloads and their order.
Consumers MAY share equivalent projections.
Rendering MUST leave data unchanged and MUST NOT load files, execute commands, or output.
Automatically generated output-cell ids MUST be fresh on repeated rendering.
Output submission MUST accept logic cells.

Content-cell rendering MUST support one identical payload in every protocol, with:

- kind.
- media type.
- content.
- metadata.

Content cells MUST support metadata-only payloads and reject all content without media type, including empty content.
**Example:** Domain data can project to grouped Markdown for text and separate metadata records for automation.

## Cell formatting

Cells MUST render immutable UTF-8 bytes with terminators, without:

- reselection.
- stream choice.
- output.
- error classification.
- exit policy.

Context MUST supply zero-based position, positive total, and tool label, with `0 <= position < total`.
Single/multiple-cell boundaries MUST be preserved.
Text MUST preserve the label exactly; automation MUST ignore it.

### Human and LLM cells

Text MUST emit kind, optional media type, then sorted metadata as strings, including `True`, `False`, and `None`.
Nonempty content MUST follow a blank line with surrounding whitespace stripped; absent/empty content MUST omit that section.

| Protocol | Opening | Fields | Ending |
| --- | --- | --- | --- |
| Human | `----- <label> CELL <id> -----` | `key = value` | Two newlines |
| LLM | `--<label>-CELL <id> BEGIN--` | `key=value` | `--<label>-CELL <id> END--` and one newline |

Ids MUST use compact form.

### Automation cells

Automation MUST use shared JSON Lines with top-level metadata, `id`, and `content`.
Id MUST default to compact form but metadata `id` MUST override it.
Actual content MUST override metadata `content`, stripping nonempty text and converting absent/empty text to null.
Kind, media type, and label MUST NOT be added automatically.
These priorities preserve the flattened record contract.

## Environment-error cells

Error logic cells MUST preserve the supplied diagnostic data for rendering, including typed context and guidance.
Projection MUST produce one ordinary Markdown `error` cell per protocol with identical payloads.
Formatted message MUST become content without a prefix or duplicate `message` metadata.
Guidance MUST be formatted/trimmed:

- one fix: new line prefixed `Way to fix: `.
- multiple fixes, in order:

  - a blank line.
  - `Ways to fix:`.
  - a blank line.
  - `- ` bullets.

- no fixes: no added text.

Remaining native diagnostic fields MUST become converted metadata, including:

- `type = error`.
- code.
- context.
- optional nulls.

Errors MUST remain unchanged; private causes/templates MUST be excluded.
Ids/framing/serialization MUST use ordinary cells.
Error-cell rendering MUST NOT select streams or terminate the process.

## JSON Lines serialization

Serialization MUST return one supplied string-keyed mapping as one JSON object plus newline, without envelopes/extra fields.
Serialization MUST:

- sort keys.
- preserve Unicode.
- escape newlines.
- use compact separators.
- support nested values/empty records.

Unsupported values MUST propagate encoder exceptions.

## Output delivery

Output MUST have an independent, programmatically replaceable scope usable without projects.
Ordinary cells MUST remain pending until explicit flush or successful completion.
Warnings MUST follow results in insertion order without deduplication.
Supported journal/warning defaults MUST be independently overridable.
Disabling flags MUST reroute rather than suppress cells.
Flags MUST NOT serialize.

Cells MAY prohibit journaling; generic content cells MUST do so.
Enabling prohibited delivery MUST fail construction; unsupported conversion MUST raise internally, never derive messages from rendered content.

Before any processor failure, journal-marked submissions MUST synchronously convert to fresh records and process before console delivery/buffering.
Conversion MUST use cell data only, without context reads, I/O, or output projection.
Messages MUST summarize events/results with useful ids/counts independently of stdout.
They MUST NOT copy document bodies, action instructions, or listings; attributes MUST add useful context rather than duplicate stdout.
Explicit journal/diagnostic messages MAY remain messages.

Records MUST contain:

- message.
- timestamp.
- optional actor.
- optional structured attributes.

Dictionary output MUST flatten attributes/common fields, giving common fields precedence and excluding flags.
Existing journal timestamps MUST be preserved; other records MUST receive submission-time timestamps, not flush-time timestamps.
Explicit message journaling MUST use the configured factory, defaulting to a shared journal cell; directly submitted cells MUST bypass it.
Omitted actors MUST become `agent` for LLM and protocol name otherwise; explicit null or other values MUST win.

Successful processing MUST immediately output journals, except journal+warning cells MUST wait with final warnings.
Default no-op processing MUST succeed without effects and MUST NOT suppress console output.
Failure MUST block the affected cell and remaining cells in that submission, propagating the exact failed result regardless of error types or empty error lists.
Thereafter the emitter MUST skip conversion/processing for its lifetime, retaining immediate journal/deferred warning routing.
Flush/discard MUST NOT reset failure; other emitters MUST have independent state.
Flush MUST NOT repeat processing.

Ordering MUST hold within immediate journals, ordinary buffers, and warnings; journals MAY overtake earlier buffered results.
Flush MUST render the complete final batch before writing, clear consumed buffers, and flush the stream.
Every cell in a batch MUST use the same protocol and tool label selected at the start of rendering.
Output MUST preserve submission order and each projection's cell order.
Cell positions and totals MUST describe the complete flattened sequence.
Batch text MUST preserve each cell's UTF-8 output without added separators.

A single output MUST have position zero/total one; empty batches/projections MUST produce no text.
Framing, Unicode, and terminators MUST survive unchanged.
Rendering/decoding failures MUST precede any write.
Stream failures MUST propagate; failed writes MUST NOT be replayed automatically.

All cells from an emitter MUST use one text stream selected when the emitter is created, defaulting to current stdout at each delivery without requiring a binary buffer.
Submissions MUST NOT select streams.
Writing MUST NOT add newlines, alter stream encoding, or close the stream.
Immediate journals MUST flush that same stream.
**Example:** A journal submitted between two results is output immediately.
A subsequent warning waits until flush, which outputs both results followed by the warning.

Logical strings MUST strip surrounding whitespace while retaining internal whitespace/newlines.
Compact journals MUST escape backslashes, carriage returns, and line feeds into one physical line without truncation.
Automation MUST retain normalized values with JSON escaping.
Journal flags MUST NOT replace a cell's own presentation with compact formatting.

External command processors MUST run argument lists directly without shells and capture output.
Whole braced arguments MUST use record-dictionary fields; embedded placeholders MUST remain literal.
Missing/null fields MUST become position-preserving empty arguments without declarations.
Dates/times MUST use ISO format; other values MUST stringify.
Multiline arguments MUST retain normalized values; destination processors MAY format without mutating records.
Empty commands MUST return an invalid-command configuration diagnostic.
OS execution failures/nonzero exits MUST return a distinct command-execution diagnostic with command, available return code, and diagnostic details.
Successful subprocess stdout MUST NOT be copied to console.
