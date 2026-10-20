# Package architecture

## Goal of the document

This document describes package ownership, public interfaces, and consumer boundaries.

## Scope

Python package organization and dependency direction; individual capability behavior and development-tool implementation are out of scope.

## Package layout

The distribution MUST be `llm-tool-cli`, with root package `llm_tool_cli`.
New modules MUST own coherent responsibilities required by implemented capabilities.
Structure SHOULD grow with behavior rather than preallocate hypothetical features.

## Consumer boundaries

The library owns reusable CLI support; consumers own product behavior and capability composition.
Production code MUST NOT import or depend on applications that consume the library.
Dependencies used only for repository development MUST NOT become runtime dependencies.
**Example:** Shared configuration loading can validate an application-supplied schema without importing the application.

Shared contracts MUST distinguish library and consumer responsibilities.
Consumer defaults and policies SHOULD remain consumer-owned unless intentionally shared; consumer domain entities MUST remain consumer-owned.

Callers of shared CLI support MUST supply result logic cells or ordered subclass collections and MAY submit them directly to shared output.
The CLI MUST configure delivery without assembling payloads from internal results.
Application-specific projections MUST remain consumer-owned; shared protocol owns interfaces and rendering infrastructure.
Constructing typed logic cells MUST NOT count as protocol-specific rendering or require consumer CLI dependencies.

## Module responsibilities

Module names SHOULD identify responsibilities for discoverability, not implementation techniques unless those are stable responsibilities.
Entities/errors MUST belong to their concept's owner; shared infrastructure MUST remain independent of specialized capabilities.

Optional conventional submodules MAY be:

- `entities` — Typed values and structures.
- `errors` — Environment errors and internal exceptions.
- `utils` — Technical helpers without a narrower owner.
- `tests` — Colocated behavior tests.
- `tests.make` — Reusable test-object constructors.
- `tests.helpers` — Reusable test setup and verification.

These MUST NOT be added merely for symmetry.
Modules defining expected fatal errors MUST provide `errors`; other architecture requirements may also require a listed submodule.

### Core and context

Core MUST own result propagation, shared entities, and error bases.
Capability errors and consumer presentation metadata MUST retain their respective owners.

Public `core.context` MUST provide independent, named, typed resource bindings.
Bindings MUST support:

- access.
- presence checks.
- initialization without reassignment.
- synchronous temporary scopes that restore the previous binding.

Unset access and repeated initialization MUST raise internal errors identifying the affected binding.
Bindings MUST be framework/service-independent.
Applications MUST own binding instances, objects, and setup; bindings MUST NOT prohibit explicit arguments.

### Settings and project preparation

Settings MUST be independent, framework-free frozen values accessed through typed context bindings.
Ownership MUST separate these lifetimes:

- `core.settings` — Static application identity and optional default configuration filename.
- `config.runtime` — Effective invocation protocol, independent of identity and project availability.
- `config.project` — Selected absolute configuration path and project root derived from its parent.

Applications using project setup MUST declare their default filename in static settings without competing constants.
Identity MUST be available before parsing and preserve exact whitespace/empty labels.
Static initialization MUST accept identical repeats and reject conflicting labels or filenames internally without replacing settings.

Project preparation MUST expose synchronous loading and initialization scopes yielding a result for the supplied Pydantic schema.
On entry, project preparation MUST:

1. use the static filename to select an existing file or create a starter without upward discovery.
2. load the configuration.
3. validate the configuration.
4. bind complete project settings.

Expected preparation failures MUST yield unchanged errors without binding; body exceptions MUST propagate unchanged.
Missing static filenames MUST raise an internal configuration error before filesystem access.

Callers MUST retain project contexts through dependent execution/output; CLI callers MUST register them in framework resource lifecycles.
Projectless commands MUST NOT establish project bindings.
Settings MUST be the sole source of their fields, without copies in application state.
Application settings and derived runtime objects MUST remain consumer-owned and separate.

Shared test fixtures MUST support isolated settings scopes with restoration.
Runtime, project, and static settings MUST be independently preparable; tests requiring only a project root MUST NOT need configuration loading.

### CLI

The library MUST own Typer's runtime dependency/version constraint, global-option parsing, and command-specific defaults.
Shared command context MUST read parsed root parameters and bind effective runtime settings and fresh output through framework resources.
It MUST retain unresolved optional configuration input separately and read effective protocol from active settings without copying.
Protocol selection MUST follow `specs/behavior/cli.md`.

Commands MUST submit cells directly to shared output.
Shared command scope MUST compose context setup, error handling, and output finalization.
Consumer command scopes MUST compose it while retaining ownership of application resources, journal construction, and their setup/cleanup.
Shared error reporting MUST use self-contained errors, without journal delivery, consumer factories, or extended runtime scopes.
Framework-managed output/project bindings MUST survive finalization.

Shared application construction MUST provide:

- an ordinary command group.
- root options.
- help aliases.
- completion availability.

The root callback MUST retain unspecified inputs without a separate global-options binding.
Consumers MUST register their own commands and parse remaining options.

Shared command registration MUST support packaged skill documentation, installed-version reporting, and project initialization independently of consumer command contexts.
Consumers MUST supply their document choices/resources, distribution identity, or schema/template and optional help as appropriate.
Shared commands MUST use shared command scope for protocol selection, output, and finalization.
Initialization MUST use shared project preparation with invocation cwd/unresolved input and emit a creation acknowledgement with the active path.
Registration MUST NOT prepare projects; schema and starter contents MUST remain consumer-owned.

CLI MUST use core exit-status policy and the categories in `specs/behavior/cli.md`, without replacing consumer failure categories.
Shared option parsing MUST defer configuration-path validation and preserve explicit versus unspecified protocol.
Shared parsing and consumer explicit argument validation MUST use the same typed invalid-argument diagnostic directly, carrying the rejection reason without wrappers or duplicates.

### Paths

`paths` MUST own project-path interpretation under `specs/behavior/paths.md`.
Lexical normalization MUST remain filesystem-independent.
Consumers MUST own domain-specific path semantics and policies for handling shared path results.

Public path interfaces MUST distinguish the following through semantic types:

- untrusted filesystem inputs.
- canonical identifiers.
- resolved roots.
- contained paths.
- configuration paths.
- relative project paths.
- glob patterns.

These distinctions MUST communicate interpretation and established guarantees without repeating validation at every call.
Filesystem path types MUST use `pathlib.Path`; identifier and glob types MUST use strings.
Semantic primitive constructors MUST preserve supplied values without conversion or validation.
Merely constructing any of these values MUST NOT establish resolution, existence, or containment:

- input paths.
- configuration paths.
- relative paths.
- glob patterns.

The public path boundary MUST provide:

- canonical checks.
- component extraction.
- normalization.
- filesystem conversion.

Operations MUST distinguish fallible resolution/validation from direct operations whose typed preconditions establish valid input.
`paths.globs` MUST own capture validation, matching, and shared preparation/compilation reused by enumeration.
`paths.enumeration` MUST own enumeration/traversal.
`paths.errors` MUST own typed failures for:

- invalid paths.
- invalid patterns.
- filesystem resolution.
- filesystem enumeration.

Failures MUST preserve relevant input, reason, and private causes.

### Configuration files

`config` MUST own reusable selection/loading/creation under `specs/behavior/config.md` and publicly expose file operations.
`config.fields` MUST provide independently reusable version and session-directory validation without a common application base.
Other relative-path fields MUST be able to reuse the same lexical validation.

Applications MUST own:

- schemas.
- supported versions.
- selected fields.
- defaults.

The library MUST NOT prescribe schema versions/defaults; fields MUST NOT access contexts or filesystems.
Configuration operations MUST preserve the semantic distinction between configuration paths and other filesystem inputs.
Creation MUST accept unvalidated target paths; selection and resolution MUST establish the guarantees required by their contracts.

Consumers MUST supply filename/cwd and own templates, schemas, and application resource setup.
Shared project contexts MUST manage project settings/scopes.
Configuration errors MUST belong to `config.errors`.
Template-read diagnostics MUST retain:

- target.
- template.
- reason.
- private original cause.

### Protocol and skills

`protocol` MUST own:

- protocols.
- cell construction/formatting.
- error cells.
- JSON Lines serialization.

Protocol identifiers and JSON Lines serialization MUST depend only on the standard library.

Ownership MUST separate presentation data from formatting:

- `protocol.logic_cells` — Typed projection data and protocol-specific projection.
- `protocol.output_cells` — Prepared output data and complete format-specific rendering.
- `protocol.journal` — Shared journal records independent of delivery.
- `protocol.errors` — Internal failures of projection and formatting contracts.

Output/logic cells and rendering contexts MUST inherit the shared base entity.
Uniform projection MUST support identical payloads across protocols and be reused by shared content/error cells.
Multiple-output or differing-payload cells MUST retain their own logic-cell projections.
Logic cells MUST hold projection data.
They MUST NOT hold or perform:

- output ids.
- cached output cells.
- filesystem access.
- output writing.

Projections MUST select/construct concrete output types, without a separate application-facing selector.
Projections/formatting MUST have no output side effects; the emitter MUST own batch rendering and writing.
The following MUST remain consumer-owned:

- kinds.
- content.
- domain context.
- projections.

Shared delivery/error handling MUST remain consumer-independent.

`skills` MUST own protocol-independent packaged text loading and typed read failures.
Loading MUST use Python's standard package-resource support to locate installed resources independently of cwd and filesystem package layout.
Consumers MUST own document choices, package selection, and Markdown resources.

## Import boundaries

Public boundaries MUST distinguish supported interfaces from internals and MAY be package roots or declared public submodules.
Implementations MUST live in dedicated submodules.
Initializers MUST contain only documentation, metadata, and imports/re-exports; they MAY be empty.
Re-exports SHOULD improve the supported interface while keeping ownership clear.

Cross-module production imports MUST use declared boundaries; same-owner submodules MAY import directly.
Production MUST NOT import tests, helpers, or development scripts.
Configured boundaries MUST reflect actual ownership/direction and MUST be updated when new modules change them.
Configured dependency checks MUST enforce the specified ownership and dependency direction.
Check configuration MUST NOT permit undeclared dependencies merely to silence a finding.

Shared test-only protocol helpers MUST support generated-id validation, comparison of payloads independently of those ids, and assertions against typed environment errors.
Error assertions MUST reuse payload normalization; callers MUST own output parsing/filtering.

## Output delivery

`output` MUST expose an emitter interface and independent typed context binding.
Emitters MUST support:

- logic-cell submission.
- explicit message journaling.
- flushing.
- discarding pending ordinary results while retaining warnings.

Submission and journaling MUST return shared results.

Emitters MUST accept a consumer factory for explicit message journaling, defaulting to the shared journal cell.
The factory MUST receive message and actor and return a shared journal-cell subtype.
Directly submitted cells MUST bypass that factory.
Omitted actors MUST derive from runtime protocol; explicit values, including absence, MUST remain unchanged.

The shared stream emitter MUST accept an optional text stream at construction.
Every cell MUST use that stream, defaulting to current stdout at delivery; submissions MUST NOT choose streams and the emitter MUST NOT close them.
Delivery MUST read active runtime protocol without storing a copy.
Batch rendering MUST follow `specs/behavior/protocol.md`.
Text preparation MUST be independently overridable without replacing stream selection, writing, or flushing.
Output MAY depend on core/configuration/protocol; those MUST NOT depend on output.

Journal records MUST contain:

- message.
- timestamp.
- optional actor.
- JSON-compatible attributes.

Dictionary conversion MUST produce a fresh flattened mapping with common fields taking precedence and ISO timestamps.
Logic-cell journal conversion MUST be pure and raise an internal error identifying the concrete type when unsupported.
Journal-capable cells MUST create new semantic summaries and structured attributes from existing data independently of projections.
Uniform projection MUST NOT supply fallback conversion.
Cells prohibiting journaling, including generic content cells, MUST express that prohibition in their type and reject enabled construction.

Journal processors MUST consume records and return shared results independently of logic-cell projections.
Shared implementations MUST support no-op delivery and direct subprocess execution.
Reusable journal configuration MUST accept an optional nonempty string-argument list and construct the corresponding processor.
Emitters MUST accept a processor, default to no-op, and privately remember failed processing.
Failure MUST bypass subsequent conversion/processing without altering console routing, including after flush/discard; CLI MUST NOT infer state from error classes.
Command substitution MUST use whole arguments and the record dictionary, without a field registry.
`output.errors` MUST own command configuration/execution failures.

Logic cells MUST carry independently overridable journal/warning flags, defaulting false and excluded from serialization.
Shared journal cells MUST provide:

- timestamp.
- actor.
- message.
- compact text/structured automation projections.
- journal default.

Consumers MAY extend fields/text projections.
Shared warning cells MUST provide warning metadata projections and warning default.
Their output implementations MUST belong to `protocol.output_cells`; cells/projections MUST remain delivery-free.

Shared test helpers MAY provide a collecting emitter and warning inspection for integrations.
