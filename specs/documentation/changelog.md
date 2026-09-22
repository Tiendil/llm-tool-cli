# Changelog documentation

## Goal of the document

This document describes the changelog tooling, source files, version-record structure, and entry format.

## Scope

This specification applies to changelog documentation artifacts.
Release version selection, package publishing, Git tagging, and release automation are out of scope.

## Dictionary

- `changelog artifact` — a Changy source file in `changes/` or the generated root `CHANGELOG.md`.
- `version record` — Markdown content describing changes for one released or unreleased version.

## Tooling

The project MUST use [Changy](https://github.com/Tiendil/changy/) to manage the changelog.
Changelog source files MUST live in `changes/`.
The root `CHANGELOG.md` MUST be generated from those sources.
Unreleased changes MUST be recorded in `changes/unreleased.md`.

## Version record structure

A version record MAY contain these parts, in this order:

1. A short introduction when coordinated changes benefit from context.
2. A `Migration` section when users need manual upgrade instructions.
3. A `Changes` section listing notable changes.
4. A `Deprecations` section listing deprecated capabilities or contracts.

These sections MUST use h3 headings.
The `Changes` section SHOULD be present when the version contains notable user-visible, developer-visible, or project-maintenance changes.
The `Migration` section MUST be present when users need manual steps before, during, or after upgrading.
The `Deprecations` section MUST be present when a version deprecates a documented capability or public contract.
Additional h3 sections MAY be used for a distinct concern not covered by these categories.

## Entry format

Entries SHOULD use concise bullet points describing the change and its impact.
Entries SHOULD link to an issue, task, or pull request when such a reference exists.
GitHub issue references SHOULD use `gh-<number>`.
References MUST NOT be invented when no tracked item exists.
Additional details MAY use nested bullets when they explain an impact or required action.
