# Configuration files

## Goal of the document

This document describes shared configuration-file selection, loading, creation, and failure diagnostics.

## Scope

This specification covers reusable configuration-file mechanics.
Application schema semantics, template contents, workspace construction, and CLI presentation and exit policies are out of scope.

## General behavior

Configuration selection and loading MUST be deterministic for the same inputs, working directory, and filesystem state.

## Path resolution

Configuration path resolution MUST expand a leading `~` or `~user` home-directory marker before resolving the path.
Relative paths MUST resolve against the caller-supplied working directory.
Absolute paths MUST be independent of that directory.
Relative working directories MUST resolve against the process working directory.
Resolution MUST follow symlinks without requiring the target or its parent to exist.
Application-specific identifier syntax MUST NOT receive special interpretation.

Path resolution MUST NOT discover configuration files, read their contents, or create files or directories.
Expected home-expansion and filesystem-resolution failures MUST produce configuration path-resolution diagnostics.

## Existing configuration selection

An explicit configuration path MUST take precedence over discovery and use shared configuration path resolution.
An explicit path MUST NOT fall back to discovery when the target is missing or cannot be loaded.

Without an explicit path, selection MUST search from the resolved caller-supplied working directory through its parents to the filesystem root for the caller-supplied filename.
Discovery MUST select the nearest matching file and skip matching directories.
A discovered symlink MUST retain the path of the discovered entry rather than changing the selected path to its target.
Selection MUST NOT read or validate configuration contents.

A discovery-only lookup MUST distinguish no match from a filesystem failure.
Selection that requires a configuration MUST report `config_not_found` when discovery finds no match.
That diagnostic MUST identify the search starting directory in `path` and the filename and search scope in `reason`.

## Initialization target selection

Initialization MUST select an explicit configuration path when supplied.
Otherwise, it MUST select the caller-supplied default filename in the supplied working directory.
The selected target MUST use shared configuration path resolution.
Initialization target selection MUST NOT search parent directories or read or create files or directories.

**Example:** When a parent directory contains `tool.toml`, initialization from its child still selects the child's `tool.toml` unless an explicit path is supplied.
Loading an existing project from that same child can discover the parent's file.

## Configuration loading

Configuration reading MUST accept UTF-8 TOML 1.1 and return the parsed document without applying an application schema.
An empty document MUST produce an empty mapping.
Reading MUST use the supplied path without additional discovery or resolution.

Schema-based loading MUST validate the parsed document using the caller-supplied schema and its defaults.
The caller MUST own field meanings and validation rules.
Read failures MUST propagate unchanged.
Expected schema-validation failures MUST produce configuration validation diagnostics.
Unexpected schema failures MUST propagate as exceptions.

## Configuration creation

Creation MUST write supplied text as UTF-8 without changing the text.
It MUST use the supplied target path without additional discovery or resolution.
Creation MUST be exclusive and MUST refuse an existing filesystem entry at that path, including a symlink.
It MUST NOT overwrite a file created concurrently.
The parent directory MUST already exist; creation MUST NOT create directories.
Creation MUST NOT validate the text as TOML or apply an application schema.
A failed write MAY leave a partial newly created file.

Template-based creation MUST read the caller-selected packaged template as UTF-8 text before attempting target creation.
A template-read failure MUST leave the target untouched, including when the target already exists.
Successful template reading MUST use the same exclusive creation behavior as supplied text.
Creation failures MUST propagate unchanged.

## Configuration initialization

Initialization MUST combine initialization target selection with template-based creation, in that order.
The caller MUST supply the default filename, working directory, resource package, and template, and MAY supply an explicit target path.
Initialization MUST return the resolved configuration path only after successful creation.
A failed stage MUST stop initialization and propagate its diagnostics unchanged without attempting subsequent stages.
Initialization MUST NOT load or validate the created configuration or construct or install an application workspace.

## Failure diagnostics

Expected failures MUST use the shared environment-error result contract.
Configuration diagnostics MUST include `path` and `reason`.
Template-read diagnostics MUST additionally include `template`, with `path` identifying the intended target.
Schema-validation details MUST be carried in `reason`.
Underlying exceptions MUST be retained as private causes when available, outside serialized diagnostic data.

The stable diagnostic codes MUST be:

| Condition | Code |
| --- | --- |
| Configuration path resolution fails | `config_path_resolution_failed` |
| Configuration discovery fails | `config_discovery_failed` |
| Required discovery finds no configuration | `config_not_found` |
| Configuration cannot be opened or read, including a missing explicit file | `config_unreadable` |
| Configuration is not valid UTF-8 | `config_invalid_encoding` |
| Configuration is not valid TOML | `config_invalid_toml` |
| Parsed configuration fails the supplied schema | `config_validation_failed` |
| Creation target already exists | `config_already_exists` |
| Packaged template cannot be read as UTF-8 | `config_template_unreadable` |
| Supplied text cannot be encoded or the target cannot be written | `config_unwritable` |

Configuration operations MUST propagate existing diagnostics without wrapping or reclassifying them.
Unexpected exceptions MUST remain exceptions rather than becoming expected configuration failures.
