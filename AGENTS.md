# Instructions for AI agents

These instructions apply to work in `llm-tool-cli`.

Every agent MUST follow the rules and guidelines outlined in this document when performing their work.

## Project

`llm-tool-cli` is a Python library for reusable support in LLM-oriented command-line tools.
Its import package is `llm_tool_cli`.
The package provides configuration file mechanics and shared exceptions, with no CLI entry point.
Do not add placeholder runtime modules or implement proposed capabilities without a corresponding development request.

Code in `llm_tool_cli`, including comments and docstrings, MUST NOT mention tools that depend on the library unless explicitly requested by the developer.

## Simplicity-first design

- Start with the smallest design that satisfies the current explicit requirements and preserves existing behavior. Do not design for hypothetical future requirements.
- Every proposed abstraction, entity, table, column, persisted value, variant, or workflow must serve a current requirement and have a current consumer. If removing it does not break required behavior or an existing invariant, omit it.
- Prefer one source of truth. Derive information when it is unambiguous, and do not duplicate facts for convenience, symmetry, debugging, auditability, or possible future use unless explicitly required.
- Before presenting or implementing a design, perform a subtraction pass: try removing each newly introduced concept and keep it only when its absence causes a concrete problem.
- Consider corner cases only when they follow from current requirements, existing behavior, or observed data and materially affect the design. Defer speculative cases instead of building for them.
- When several approaches satisfy the requirements, recommend the one with fewer concepts, states, branches, storage paths, and migrations. Present additional flexibility only as an optional extension.
- Simplicity does not mean merging unrelated interfaces at any cost. Do not combine APIs when doing so introduces mutually exclusive optional arguments, invalid states, or pervasive runtime branching.

## Source of truth

Project requirements are specified in `specs/`.
Agents MUST read the relevant specifications before making changes.
Start with `specs/intro.md`, then read the specifications relevant to the change.

The specification approach follows Feeds Fun, with architecture and development organization adapted from Donna and Depmesh.
When adding, deleting, or significantly changing a specification, agents MUST update `specs/intro.md`.
Agents MUST NOT create new specifications or delete or significantly change existing specifications without explicit instructions.
Preserve the wording and structure of existing specifications where they remain accurate.

## Development environment

All development-related operations MUST be performed in Docker Compose containers through the repository helpers.
Agents MUST NOT perform development-related operations directly on the host machine.
Searching, reading, and editing files may be done on the host.
Do not replace the Compose-managed environment with direct `docker run` or `docker build` commands.

Supported helpers:

- `./bin/dev-build-containers.sh` builds the development environment from `uv.lock`.
- `./bin/dev.sh <command>...` runs a command in the development container, preserving its arguments.
- `./bin/dev-format.sh` applies Python formatting and unused-code cleanup.
- `./bin/dev-check-formatting.sh` checks Python formatting.
- `./bin/dev-check-semantics.sh` checks architecture, unused code, lint, and types.
- `./bin/dev-tests.sh [pytest arguments...]` runs pytest.
- `./bin/dev-build-package.sh` builds the source distribution and wheel.
- `./bin/dev-check-runtime.sh` verifies the installed wheel outside the source tree.

After changing dependencies, run `./bin/dev.sh uv lock`.
After changing Docker configuration or dependencies, run `./bin/dev-build-containers.sh` to rebuild the development image.

The same configured static analysis checks SHOULD be available locally and in CI.
Checks MUST propagate failure to the caller and CI.

The empty-package test exception is only for the initial scaffold.
Do not present a zero-test run as application test coverage.

## Restricted operations

The following operations require explicit authorization from the current task or earlier session instructions:

- Change `docker-compose.yml` or Docker-related configuration.
- Change Docker runtime parameters such as resources or volumes.
- Change running Docker services related to other projects or unrelated to the development environment.
- Install new dependencies.
- Update lock files.
- Install new tools, utilities, or software on the host machine or in development containers.
- Change project structure, such as moving files or creating new directories.
- Stage or unstage files in Git, including commands such as `git add`, `git restore --staged`, and `git reset`.

Proceed with changes already authorized by the task; do not request approval again.
If a required operation is not already authorized, ask for explicit permission before doing it.

## Implementation guidance

Follow existing specifications and local project patterns.
Keep changes scoped to the requested task.
Do not implement behavior that is only mentioned as future or possible functionality unless explicitly requested.

When code is added, tests SHOULD follow `specs/architecture/tests.md`.
When entities, errors, warnings, or module layout are affected, agents MUST check the corresponding architecture specifications.

## Top priority tools

These tools MUST have the highest priority when an agent is deciding which tool to use for a given task:

### `donna`

Use Donna to run project-local deterministic workflows when the developer, these instructions, or an active Donna workflow explicitly asks for one.
Donna controls workflow state only. Agents remain responsible for reading project instructions, using Depmesh where applicable, editing files, running checks, and reporting results.

At the start of each work session, read usage and list workflows:

```bash
./bin/dev.sh donna -p llm skill usage
./bin/dev.sh donna -p llm list
```

Use the LLM protocol for agent-facing invocations unless a human explicitly asks for another protocol.
Do not create or reset a Donna session unless explicitly requested.
Starting a workflow in the existing session is different from resetting the session.

After making changes, run `@/workflows/polish.donna.md` at a point when the repository should be in a working state:

```bash
./bin/dev.sh donna -p llm run @/workflows/polish.donna.md
```

Follow Donna's returned action instructions and report their outcomes.
Run this workflow instead of manually duplicating its formatting, linting, and test sequence.
Run individual operations separately only when a specific operation is needed for a particular reason.

### `depmesh`

Agents MUST use Depmesh for dependency types supported by `depmesh.toml`.
At the start of a work session, read its usage:

```bash
./bin/dev.sh uv run -- depmesh -p llm skill usage
```

Query affected files for governing specifications, related tests, imports, and reverse imports when those relationships are relevant.

### `difftastic`

Use `difft` as the default tool for inspecting code changes and whenever a semantic, syntax-aware diff is useful. Prefer stable, agent-readable output:

```bash
difft --display=inline --color=never --context=6 OLD-PATH NEW-PATH
difft --display=inline --color=never --context=6 --sort-paths OLD-DIR NEW-DIR
GIT_EXTERNAL_DIFF="difft --display=inline --color=never --context=6" git --no-pager diff -- PATH
GIT_EXTERNAL_DIFF="difft --display=inline --color=never --context=6" git --no-pager diff --cached -- PATH
```

Use a classic line-oriented diff, such as `git --no-pager diff --no-ext-diff` or `diff -u`, only when the task explicitly requires raw line-by-line output—for example, producing a patch, inspecting exact whitespace or line endings, or supplying unified-diff input to another tool. Do not choose a classic diff merely because a change is small or limited to text.

### `ast-grep`

`ast-grep` — a tool for searching and manipulating Abstract Syntax Trees in code. Use it when you work with particular code patterns, structures, or constructs in the codebase.

You MUST use it to:

- Search for specific code patterns or structures in the codebase.
- Extract information from code, such as function definitions, variable declarations, or specific code constructs.
- Analyze code for specific patterns or anti-patterns, such as code smells, security vulnerabilities, performance issues, specific usage of libraries or APIs, etc.
- Refactor particular code patterns or structures across the codebase.
- Introduce new small behaviors or features into existing code.

You MUST NOT use it for:

- Implementing huge features or behaviors that require adding massive blocks of code (like adding a new class, module, writing a huge function, etc.).

It is installed in the development environment:

```bash
./bin/dev.sh uv run -- ast-grep --help
```

### `rg`

Use `rg` for text and file searches unless a structural code query is needed.

`ast-grep` has a higher priority than `rg` whenever a structural code query is needed.

### Specification reading

Grep-like tools, including `rg`, MAY be used to discover relevant specification files. Search results MUST be treated only as discovery hints.

Before relying on, interpreting, reviewing, or changing a specification file, an agent MUST read that file in full from beginning to end. Agents MUST NOT use `sed`, `head`, `tail`, line-range readers, grep context output, or any other partial-file reading method to read specification content. If a whole-file read is truncated, the agent MUST repeat it with sufficient output capacity and MUST NOT proceed until the complete file has been read.

## Special instructions

**When the developer asks you a question — answer it as a question, do not implement the answer as a code change or a plan, just answer the question.**
