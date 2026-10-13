# Project paths

## Goal of the document

This document describes project-path identifiers, their conversion to and from filesystem paths, glob matching and captures, file enumeration, and their failure behavior.

## Scope

This specification applies to project-path concepts owned by the library.
Application-specific artifact semantics, template substitution, and rule evaluation are out of scope.

## Identifiers

A canonical project-path identifier MUST start with `@/` and identify a path below the project root.
It MUST contain one or more non-empty `/`-separated segments after the prefix.
Canonical identifiers MUST NOT contain `.` or `..` segments.

Identifiers MAY refer to files, directories, or locations that do not yet exist.
Identifier validity MUST NOT depend on the target's kind or a filename extension.
Consumers own any additional target-kind, existence, or extension requirements.
Path identity MUST be based on the canonical identifier rather than the original input spelling.
Inputs that normalize to the same canonical identifier MUST identify the same project path.

**Example:** `@/LICENSE`, `@/assets`, and `@/notes/Заметки проекта.md` are valid canonical identifiers, regardless of whether their targets exist.

## Identifier checks

A canonical-identifier check MUST return true exactly when the input is a string whose lexical normalization succeeds without changing its text.
It MUST return false for non-string inputs and for malformed or noncanonical strings, without reporting a failure diagnostic.
The check MUST NOT access the filesystem or depend on the current working directory.
It MUST NOT impose application-specific existence or filename-extension requirements.

**Example:** `@/a/b` passes the check, while `@/a/../b` fails even though normalization can produce the valid identifier `@/b`.

## Identifier components

Component extraction MUST accept an already canonical identifier and return its segments in order, excluding the `@/` prefix.
It MUST preserve every segment's text exactly and return the components directly, with no expected failure outcome for canonical inputs.
Callers MUST establish canonical form before extraction.
Extraction MUST NOT repeat normalization or validation.
It MUST NOT access the filesystem or depend on the current working directory.

**Example:** `@/notes/Project Plan.md` produces the two components `notes` and `Project Plan.md`.
The backslash in `@/a\b/file` remains part of the first component.

## Normalization

Normalization MUST accept a textual identifier and either produce its canonical form or report an invalid-path failure.
Invalid input MUST NOT be treated as a successful operation with no identifier.

Normalization MUST require the `@/` prefix and reject empty segments, including repeated and trailing separators.
It MUST remove `.` segments and use each `..` segment to remove the preceding remaining segment.
It MUST reject traversal above the root at any point, even if later segments would return below it.
It MUST reject a normalized identifier that denotes only the root.
It MUST preserve all other segment text exactly, including case and whitespace.
Backslashes and application syntax characters MUST be treated as ordinary segment text.

**Example:** `@/a/./b/../c` normalizes to `@/a/c`, while `@/a/../../c` is invalid because it traverses above the root.
Inputs `@/a//b` and `@/a/` are invalid because they contain empty segments; normalization does not collapse repeated separators or strip trailing ones.

Normalization MUST NOT access the filesystem or depend on the current working directory.
It MUST NOT expand home markers, require an existing target, or resolve symlinks.
A canonical identifier alone MUST NOT be treated as proof of filesystem containment.

## Mixed path normalization

Normalization of an identifier or filesystem input MUST resolve the supplied project root before processing the input.
Root resolution failures MUST take precedence over input normalization and target resolution failures.

Empty textual inputs MUST be rejected with an invalid-path failure whose `path` field is empty, regardless of the supplied directory base.
An empty input MUST NOT identify that base.
An explicit `.` MUST retain ordinary relative filesystem path semantics, and whitespace MUST NOT be removed from non-empty inputs.

**Example:** With root `/project` and directory base `/project/nested`, `""` is invalid while `.` produces `@/nested`.

Inputs starting with `@` MUST use lexical identifier normalization, including rejection of a missing `@/` prefix.
After lexical normalization, this branch MUST check filesystem containment and reject symbolic links below the resolved project root, without requiring an existing target.
An explicit filesystem base MUST NOT affect this branch.

Other inputs MUST be interpreted as filesystem paths, with home markers expanded before resolution.
Absolute filesystem inputs MUST be resolved directly.
Relative filesystem inputs MUST use the supplied directory base, or the resolved project root when no base is supplied.
A relative directory base MUST itself be relative to the process current working directory.
Callers that use a source file as the reference point MUST supply its containing directory as the base without rewriting the input into an identifier first.
The root and directory base MUST NOT undergo home expansion.

Filesystem inputs MUST pass containment resolution before conversion to a canonical identifier.
They MUST NOT require an existing target or a particular filesystem kind.
Containment failures MUST identify the filesystem candidate formed after home expansion and base selection.

**Example:** With root `/home/user/project` and home directory `/home/user`, `~/project/file` produces `@/file`, while `~/elsewhere/file` fails containment.
The identifier `@/~/file` retains its literal `~` segment.
With an explicit base `/home/user/project/nested`, `file` produces `@/nested/file`; without that base it produces `@/file`.

## Mixed path resolution

Resolution of an identifier or filesystem input MUST resolve the supplied project root before processing the input.
Root resolution failures MUST take precedence over input rejection, home expansion, and target resolution failures.
Successful resolution MUST produce an absolute filesystem path strictly below the resolved root.
Rejected input MUST produce a failure rather than a successful absence.

Inputs starting with `@` MUST use root-anchored resolution, including lexical normalization before filesystem resolution and rejection of a missing `@/` prefix.
Other inputs MUST be interpreted as filesystem paths with home markers expanded before resolution.
Relative filesystem inputs MUST use the resolved project root as their base.
The root MUST NOT undergo home expansion.

Absolute filesystem inputs MUST be accepted by default.
Callers MUST be able to disable absolute filesystem inputs; this restriction MUST apply after home expansion and MUST NOT reject root-anchored identifiers.
An input rejected by this restriction MUST use the original textual input in its invalid-path diagnostic.
Accepted inputs MUST enforce filesystem containment without requiring an existing target or a particular filesystem kind.
Lexical, home-expansion, and filesystem failures MUST preserve their respective diagnostics.

**Example:** With root and home directory `/project`, both `@/file` and `~/file` resolve to `/project/file` by default.
Disabling absolute filesystem inputs rejects `~/file`, while `@/file` and `file` remain accepted.
The identifier `@/~/file` resolves to `/project/~/file` without home expansion.

## Project-root resolution

Resolving a supplied filesystem root MUST produce an absolute path with symlinks and parent-directory segments resolved.
Relative roots MUST use the process current working directory as their base.
Resolution MUST NOT expand home markers or require the target to exist or be a directory.
Consumers MUST enforce any required existence or directory-kind constraints separately.

**Example:** With the working directory `/workspace`, a missing `project` root resolves to `/workspace/project`, while `~/project` resolves to `/workspace/~/project` without home expansion.

Root resolution MUST remain separate from lexical identifier normalization and MUST NOT establish containment of any project path.

## Root-anchored resolution

Resolving a root-anchored identifier inside an already resolved project root MUST first apply lexical identifier normalization, then resolve the normalized path below that root with filesystem containment enforcement.
The supplied root MUST determine the base independently of the current working directory.
Resolution MUST NOT expand home markers or require the target to exist or have a particular filesystem kind.
Lexical normalization failures and filesystem containment or resolution failures MUST preserve their respective diagnostics.

**Example:** `@/a/../b` resolves to `b` below the supplied root.
If `a` is a symlink, normalization removes `a/..` before filesystem resolution, while resolving `@/a/b` rejects that symlink without following it.

## Filesystem containment

Resolving a supplied filesystem path inside an already resolved project root MUST produce an absolute path strictly below that root or report a failure.
Resolution MUST reject any symbolic link encountered below the resolved project root before following it, including links to internal targets, broken links, and loops.
This check MUST include intermediate path components and filesystem-input components followed by `..`.
Symlinks used to select the project root or its ancestors MAY be resolved; they MUST NOT hide a symbolic link below that root.
Resolution MUST resolve parent-directory segments and enforce containment.
It MUST reject the root itself and targets outside the root.
It MUST NOT require the target to exist or have a particular filesystem kind.

Relative filesystem paths MUST use the process current working directory as their base.
Callers that require another base MUST combine that base with the input before requesting containment resolution.
Containment resolution MUST NOT interpret `@/` identifiers or expand home markers.

**Example:** If `/workspace/project/link` points outside `/workspace/project`, resolving a path through `link` fails containment even though its supplied filesystem path starts with the project root.

## Resolved path identifiers

Conversion to a canonical identifier MUST accept a filesystem path already resolved and checked strictly below the supplied resolved project root.
The caller MUST supply the same root used for that containment check.
Conversion MUST return the path relative to that root with an `@/` prefix and `/` separators, preserving all segment text.
It MUST return the identifier directly, with no expected failure outcome for inputs satisfying these preconditions.

Conversion MUST NOT access the filesystem, depend on the current working directory, or repeat resolution or validation already established by those preconditions.
It MUST support files, directories, and missing targets without imposing existence or filename-extension requirements.

**Example:** A resolved path `/project/notes/Project Plan.md` under `/project` converts to `@/notes/Project Plan.md`.
The supplied path MUST already satisfy the prohibition on symbolic links below the project root.

## Glob patterns

Patterns MUST accept project-root-anchored, root-relative, absolute, and home-relative forms with the same containment and input-normalization rules as mixed path resolution.
Pattern preparation MUST resolve only the literal prefix preceding the first wildcard and normalize the remaining components lexically.
Wildcard syntax MUST NOT be resolved as a concrete filesystem name.
A symbolic link in the literal prefix preceding the first wildcard MUST be rejected before traversal.
The project root itself MUST be treated as a literal path even when its directory names contain glob metacharacters.

Glob matching MUST use `/` as the separator and match case sensitively.
Within a segment, `*`, `?`, and bracket character classes MUST retain shell-style matching semantics.
Bracket escaping MUST allow literal wildcard characters, such as `[*]`, `[?]`, and `[[]`.
Backslashes MUST remain ordinary filename characters rather than escapes.
An unmatched `[` MUST be treated literally, and bracket classes MUST NOT span path separators.
`**` MUST match zero or more characters across path separators, including when embedded in a segment.
`**/` MUST also allow zero directory levels.
Hidden files and directories MUST be treated like ordinary entries, including when selected by wildcards.
All wildcards MUST support line breaks in filenames.

Patterns MAY define named captures using `{*name}` and `{**name}`.
Capture names MUST contain only ASCII letters, ASCII digits, and `_`, MUST NOT start with a digit, and MUST be unique within the pattern.
Malformed capture syntax, including an unclosed capture, MUST fail validation.
`{*name}` MUST capture zero or more characters inside one segment.
`{**name}` MUST capture zero or more characters across separators, including before a literal suffix.
`{**name}/` MUST also allow zero directory levels, exposing an empty string for an omitted directory capture.
Captures MUST be greedy, subject to matching the rest of the pattern.
Capture-name extraction MUST validate syntax without accessing the filesystem or performing template substitution.

**Example:** `@/src/{**module_path}.py` matches `@/src/core/api.py` with `module_path` equal to `core/api`.
The pattern `@/src/{**package}/{*module}.py` matches `@/src/api.py` with an empty `package` and `module` equal to `api`.
The pattern `@/src/a**.py` matches both `@/src/a.py` and `@/src/a/nested.py`.

Matching MUST accept an already canonical identifier and compare the entire identifier against the prepared pattern.
It MUST NOT require the referenced target to exist or repeat the caller's path validation.
A successful match MUST return capture values, including an empty mapping when the pattern has no captures.
A non-match MUST be distinguishable from invalid-pattern and filesystem-resolution failures.

## File enumeration

File enumeration MUST use the same pattern preparation and matching grammar as identifier matching.
It MUST return unique canonical identifiers for existing regular files matching the pattern under the project root.
The default pattern MUST recursively select all files.
Enumeration MUST NOT expose captures as additional result data.
Files MUST be returned in lexicographic path-component order, with duplicates from recursive patterns removed.

Enumeration MUST skip every symbolic link encountered through matching, including file links, directory links, broken links, and cycles, without following its target.
Missing search locations and non-directory search prefixes MUST produce no matches.
Directories and other non-regular files MUST NOT appear in results.
Unreadable directories or other filesystem inspection failures MUST fail enumeration rather than produce a successful partial result.
Consumer-specific extension checks, configured search-directory order, and domain identifier checks remain consumer responsibilities.

## Filesystem path identifiers

Conversion of a supplied filesystem path and filesystem root to a canonical identifier MUST resolve the root first, enforce filesystem containment of the path, and return the resolved path's identifier.
Neither input needs to have been resolved by the caller.
Relative roots and paths MUST each use the process current working directory as their base; the supplied root MUST NOT implicitly become the base of a relative path.
Conversion MUST NOT interpret `@/` identifiers, expand home markers, or require an existing target or a particular filesystem kind.
Root resolution failures MUST take precedence over target resolution and containment failures.
Failures MUST retain the diagnostics of the failed resolution or containment operation.

**Example:** With the working directory `/workspace`, a filesystem path `project/notes.md` and root `project` produce `@/notes.md`, while the path `notes.md` is outside that root.

## Errors

Normalization, resolution, glob preparation, and enumeration MUST report rejected paths, including prohibited symbolic links, with one failure diagnostic with the stable code `invalid_project_path`.
Its `path` field MUST contain the rejected input with surrounding whitespace removed; containment failures MUST use the supplied filesystem path.
Consumers MUST be able to identify this failure by its code without parsing the message.

Invalid glob syntax MUST produce one failure diagnostic with the stable code `invalid_glob_pattern`, the rejected pattern in `pattern`, and a description in `reason`.
Any original compilation exception MUST remain a private cause and MUST NOT appear in serialized diagnostics.

Filesystem failures that prevent root or containment resolution, including permission failures and loops during root resolution, MUST produce one failure diagnostic with the stable code `path_resolution_failed`.
An inability to expand a home marker during mixed path normalization or resolution MUST use the same failure diagnostic.
Its `path` field MUST contain the supplied filesystem root for root resolution, the supplied filesystem path for containment resolution, or the original textual input for home expansion.
Its `reason` field MUST describe the resolution failure, with surrounding whitespace removed from both fields.
The original exception MUST be retained as a private cause and MUST NOT appear in serialized diagnostics.
Unexpected failures outside filesystem resolution MUST remain exceptions.

Filesystem failures during enumeration MUST produce one failure diagnostic with the stable code `files_unreadable`, the resolved root in `path`, and a description in `reason`.
The original exception MUST remain a private cause and MUST NOT appear in serialized diagnostics.
