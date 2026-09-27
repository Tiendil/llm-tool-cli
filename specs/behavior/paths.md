# Project paths

## Goal of the document

This document describes lexical project-path normalization, filesystem project-root resolution, and their failure behavior.

## Scope

This specification applies to project-path concepts owned by the library.
Filesystem containment and application-specific artifact or pattern semantics are out of scope.

## Identifiers

A canonical project-path identifier MUST start with `@/` and identify a path below the project root.
It MUST contain one or more non-empty `/`-separated segments after the prefix.
Canonical identifiers MUST NOT contain `.` or `..` segments.

Identifiers MAY refer to files, directories, or locations that do not yet exist.
Identifier validity MUST NOT depend on the target's kind or a filename extension.
Consumers own any additional target-kind, existence, or extension requirements.

**Example:** `@/LICENSE`, `@/assets`, and `@/notes/Заметки проекта.md` are valid canonical identifiers, regardless of whether their targets exist.

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

## Project-root resolution

Resolving a supplied filesystem root MUST produce an absolute path with symlinks and parent-directory segments resolved.
Relative roots MUST use the process current working directory as their base.
Resolution MUST NOT expand home markers or require the target to exist or be a directory.
Consumers MUST enforce any required existence or directory-kind constraints separately.

**Example:** With the working directory `/workspace`, a missing `project` root resolves to `/workspace/project`, while `~/project` resolves to `/workspace/~/project` without home expansion.

Root resolution MUST remain separate from lexical identifier normalization and MUST NOT establish containment of any project path.

## Errors

Rejected input MUST produce one failure diagnostic with the stable code `invalid_project_path`.
Its `path` field MUST contain the rejected input with surrounding whitespace removed.
Consumers MUST be able to identify this failure by its code without parsing the message.

Filesystem failures that prevent root resolution, including permission failures and symlink loops, MUST produce one failure diagnostic with the stable code `path_resolution_failed`.
Its `path` field MUST contain the supplied filesystem path and its `reason` field MUST describe the resolution failure, with surrounding whitespace removed from both fields.
The original exception MUST be retained as a private cause and MUST NOT appear in serialized diagnostics.
Unexpected failures outside filesystem resolution MUST remain exceptions.
