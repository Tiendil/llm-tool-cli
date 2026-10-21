Moved common functionality from `donna` and `depmesh` into this library.

### Changes

- Added shared Pydantic entities, `Result[T]`, and structured environment errors.
- Added independent typed `ContextValue` bindings and separate frozen `StaticConfig`, `RuntimeConfig`, and `ProjectConfig` objects for application identity, effective protocol, and prepared project location. Commands that do not use a project need no project configuration.
- Added TOML 1.1 support.
- Added project loading and initialization functionality.
- Added independently reusable `ConfigVersion` and `SessionDir` fields.
- Added typed filesystem inputs and canonical `@/` project identifiers, with lexical normalization, mixed filesystem/identifier resolution, home expansion, and structured failures.
- Added shared glob matching and deterministic file enumeration using the same grammar:

  - Case-sensitive `*`, `?`, bracket classes, and bracket escaping; hidden entries match like ordinary names.
  - `**` may cross directory separators even inside a segment; `**/` may match zero directories.
  - Named `{*name}` and `{**name}` captures support identifier matching.
  - Enumeration returns unique regular files in path-component order and reports filesystem failures instead of returning partial results.

- Established logic cells as the shared domain-to-CLI output interface, with extensible projections into human, LLM, and automation output cells.
- Provided default content, warning, journal, and environment-error cells.
- Automation protocol now outputs compact Unicode JSON Lines with flattened metadata.
- Added a context-bound `OutputEmitter` and stream implementation.
- Added `output.get().journal(...)`, configurable journal-cell factories, and `JournalRecord`.
- Command processors execute argument lists without a shell and substitute whole-argument record placeholders; missing or null fields become empty arguments. Compact text journals occupy one physical line while automation retains normalized multiline messages.
- Added shared exit-status policy.: success uses `0`, explicit invalid arguments `1`, configuration errors `2`, and other environment errors `3` by default. - Added Typer application and command-context helpers.
- Added reusable `init`, `version`, and `skill` command registration.
