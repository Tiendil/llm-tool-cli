# Configuration files

## Goal of the document

This document describes shared configuration support.

## Scope

This specification covers reusable configuration fields, file mechanics, and project preparation/scoping.
The following are out of scope:

- application schemas.
- application templates.
- application workspaces.
- CLI presentation.
- exit policy.

## General behavior

Selection/loading MUST be deterministic for the same inputs, cwd, and filesystem.

## Shared root fields

Applications MUST be able to reuse version/session-directory fields independently, owning their constraints and defaults.
The library MUST NOT prescribe versions/defaults.
Shared field failures during file loading MUST use existing schema-validation diagnostics.

### Version

Version validation MUST inspect original inputs, reject non-integers without coercion (including booleans, floats, and strings), and identify received values in integer-required diagnostics.
Unsupported literal-version diagnostics MUST identify received/supported values; other schema failures MUST retain details.

### Session directory

Session directories MUST accept relative paths and reject absolute paths or any `..` component.
Validation MUST remain lexical, without:

- resolution.
- home expansion.
- filesystem inspection.
- creation.

Values MUST retain shared relative-path representation and JSON path-string serialization.
Applications MUST own defaults/storage.

## Path resolution

Paths MUST expand leading `~`/`~user`.
Relative paths MUST use supplied cwd; absolute paths MUST be cwd-independent; relative cwd MUST use process cwd.
Resolution MUST resolve the parent as project root, then apply `specs/behavior/paths.md` containment to the file.
Root/ancestor symlinks MAY resolve; file symlinks MUST be rejected, including internal/broken/looping links.
Neither target nor parent needs to exist.
Application identifier syntax MUST NOT be interpreted.

Resolution MUST NOT discover, read, or create files/directories.
Expected home/parent-resolution failures MUST use configuration-resolution diagnostics; shared containment failures MUST propagate unchanged.

## Existing configuration selection

Explicit paths MUST use shared resolution and override discovery without fallback on missing/unloadable targets.
Otherwise selection MUST search resolved cwd through filesystem-root parents for the supplied filename, choosing the nearest file and skipping directories.
Each candidate MUST pass containment before kind inspection.
Matching symlinks MUST fail without following or falling back.
Selection MUST NOT read/validate contents.

Discovery-only lookup MUST distinguish absence from filesystem failure.
Required selection with no match MUST return a missing-configuration diagnostic, identifying starting directory in `path` and filename/search scope in `reason`.

## Initialization target selection

Initialization MUST resolve an explicit path or the default filename in supplied cwd.
Selection MUST NOT search ancestors, read, or create.
**Example:** Child-directory initialization selects the child's file even when ordinary loading would discover a parent's configuration.

## Configuration loading

Reading MUST use the supplied path without discovery/resolution, accept UTF-8 TOML 1.1, and return parsed data without schema application; empty documents MUST yield empty mappings.
Schema loading MUST apply the supplied schema/defaults.
Callers MUST own schema composition/semantics, preserving reused shared validation.
Read failures MUST propagate unchanged; expected schema failures MUST become validation diagnostics; unexpected failures MUST remain exceptions.

## Configuration creation

Creation MUST write exact supplied UTF-8 text to the supplied path without:

- resolution.
- discovery.
- TOML validation.
- schema validation.

It MUST exclusively refuse every existing entry, including symlinks and concurrent creations.
Parents MUST already exist; creation MUST NOT create directories.
Failed writes MAY leave partial new files.

Template creation MUST first read supplied packaged UTF-8 text, leaving targets untouched on read failure even if already existing, then use the same exclusive creation.
Creation failures MUST propagate unchanged.

## Configuration initialization

Initialization MUST select the target then create from template, returning the resolved path only on success.
Callers MUST supply:

- filename.
- cwd.
- resource package.
- template.

They MAY supply an explicit path.

Failed stages MUST propagate unchanged and stop subsequent stages.
File initialization MUST NOT:

- load the created file.
- validate the created file.
- construct workspaces.
- install workspaces.

## Project scopes

Entering a project-loading scope MUST select and validate configuration; entering a project-initialization scope MUST create and validate it.
Both MUST use the configured default filename and supplied schema/cwd/optional path; initialization MUST also accept template location.
Preparation MUST occur on entry.
Only successful validation MUST expose the selected absolute path and derived parent as the active project and yield loaded configuration as success.
The selected project MUST remain unchanged and available until scope exit.
Selection MUST enforce path policy; subsequent loading MUST use the selected path and root.

Preparation MUST neither require nor alter the effective runtime protocol.
Expected failures MUST yield unchanged errors without replacing the caller's active project or continuing preparation.
Created files MUST remain after subsequent load/validation failure.
Unexpected preparation/body exceptions MUST propagate unchanged.
Missing default filenames MUST raise internally before filesystem access.
Preparation MUST NOT install application-specific settings, construct workspaces, or emit output.

## Failure diagnostics

Expected failures MUST use shared error results with `path`/`reason`; template errors MUST also include `template` and identify target in `path`.
Schema details MUST reside in `reason`.
Available original exceptions MUST remain private causes outside serialized data.

Diagnostics MUST identify the failed operation and distinguish filesystem failures from invalid content.
Content diagnostics MUST distinguish text-decoding failures, invalid TOML, and schema violations.
Creation diagnostics MUST distinguish an existing target from template-read and output-write failures.

Shared containment diagnostics MUST follow `specs/behavior/paths.md`, including rejection of file symlinks.
Existing diagnostics MUST propagate without wrapping/reclassification; unexpected exceptions MUST remain exceptions.
