# README documentation

## Goal of the document

This document describes the content and tone of the repository's brief README.

## Scope

This specification applies to the root `README.md`.
Detailed capability contracts, package metadata, and agent workflow instructions are out of scope.

## Content

The README MUST start with one h1 heading containing the project name.
It MUST briefly explain the library's purpose and current development status.
It MUST NOT present proposed runtime behavior or commands as available functionality.

The README SHOULD show the basic commands to build the development environment and run checks, with their prerequisites.
It MUST link to `specs/intro.md`, `AGENTS.md`, and `CHANGELOG.md`.
Detailed development instructions and tool integrations SHOULD remain in `AGENTS.md` rather than be duplicated in the README.

## Style

The README SHOULD remain short, practical, and accurate about implementation status.
Examples MUST use commands supported by the repository's current helpers.
