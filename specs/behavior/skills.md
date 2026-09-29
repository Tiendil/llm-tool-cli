# Packaged skill documents

## Goal of the document

This document describes loading packaged skill text and reporting read failures.

## Scope

This specification covers retrieval of application-owned skill documentation from package resources.
Document selection, document contents, CLI arguments, output rendering, and exit policies are out of scope.

## Loading

The library MUST load the selected document from `fixtures/<document>.md` in the supplied importable package.
The consumer MUST supply the package and a document name selected from its own document definitions.
The library MUST NOT restrict document names to a library-owned set or select a default document.
Resource loading MUST use Python's standard package-resource support so it does not depend on the working directory or a project configuration.
Text MUST be decoded as UTF-8 and returned as a successful result, retaining empty content and significant whitespace.
Loading MUST NOT render cells, write output, or select an output protocol.

## Failures

Filesystem read failures and invalid UTF-8 MUST return a failed result containing one `skill_unreadable` diagnostic.
The diagnostic MUST identify the selected name in `document` and the original exception's explanation in `reason`, using shared diagnostic string normalization.
It MUST retain the original exception as a private cause, excluded from serialized diagnostic data.
Unexpected exceptions, including invalid package imports, MUST propagate without being converted into read-failure diagnostics.
The consumer MUST retain responsibility for rendering failures, choosing streams, and selecting exit status.
