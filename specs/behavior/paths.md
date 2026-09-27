# Project paths

## Goal of the document

This document describes project-path identifiers, their conversion to and from filesystem paths, and their failure behavior.

## Scope

This specification applies to project-path concepts owned by the library.
Application-specific artifact or pattern semantics are out of scope.

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

## Root-anchored resolution

Resolving a root-anchored identifier inside an already resolved project root MUST first apply lexical identifier normalization, then resolve the normalized path below that root with filesystem containment enforcement.
The supplied root MUST determine the base independently of the current working directory.
Resolution MUST NOT expand home markers or require the target to exist or have a particular filesystem kind.
Lexical normalization failures and filesystem containment or resolution failures MUST preserve their respective diagnostics.

**Example:** `@/a/../b` resolves to `b` below the supplied root.
If `a` is a symlink, normalization removes `a/..` before filesystem resolution, while resolving `@/a/b` follows that symlink and enforces containment of its target.

## Filesystem containment

Resolving a supplied filesystem path inside an already resolved project root MUST produce an absolute path strictly below that root or report a failure.
Resolution MUST resolve symlinks and parent-directory segments before checking containment.
It MUST reject the root itself and targets outside the root, including targets reached through symlinks.
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
When the supplied resolved path is a symlink's target, the identifier represents that target rather than the original symlink spelling.

## Filesystem path identifiers

Conversion of a supplied filesystem path and filesystem root to a canonical identifier MUST resolve the root first, enforce filesystem containment of the path, and return the resolved path's identifier.
Neither input needs to have been resolved by the caller.
Relative roots and paths MUST each use the process current working directory as their base; the supplied root MUST NOT implicitly become the base of a relative path.
Conversion MUST NOT interpret `@/` identifiers, expand home markers, or require an existing target or a particular filesystem kind.
Root resolution failures MUST take precedence over target resolution and containment failures.
Failures MUST retain the diagnostics of the failed resolution or containment operation.

**Example:** With the working directory `/workspace`, a filesystem path `project/notes.md` and root `project` produce `@/notes.md`, while the path `notes.md` is outside that root.

## Errors

Rejected input MUST produce one failure diagnostic with the stable code `invalid_project_path`.
Its `path` field MUST contain the rejected input with surrounding whitespace removed; containment failures MUST use the supplied filesystem path.
Consumers MUST be able to identify this failure by its code without parsing the message.

Filesystem failures that prevent root or containment resolution, including permission failures and symlink loops, MUST produce one failure diagnostic with the stable code `path_resolution_failed`.
Its `path` field MUST contain the supplied filesystem root for root resolution or the supplied filesystem path for containment resolution.
Its `reason` field MUST describe the resolution failure, with surrounding whitespace removed from both fields.
The original exception MUST be retained as a private cause and MUST NOT appear in serialized diagnostics.
Unexpected failures outside filesystem resolution MUST remain exceptions.
