# llm-tool-cli

Reusable Python foundations for CLI tools used by humans, LLM agents, and automation.
Import it as `llm_tool_cli` to build your own tool; the library has no standalone CLI entry point.

At its current stage, this is a personal project of [Tiendil](https://tiendil.org), developed as the shared foundation for:

- [Donna](https://github.com/Tiendil/donna), which runs deterministic workflows for agents.
- [Depmesh](https://github.com/Tiendil/depmesh), which discovers dependencies between project artifacts.

## Goals

1. Provide the ability to quickly construct tools targeted at specific tasks for AI agents.
2. Experiment with approaches to improve the usability of CLI tools for agents.
3. Unify the behavior of Tiendil’s tools.

## Capabilities

- **CLI application foundations** — Give commands a consistent structure and execution lifecycle.
- **Unified output** — Present application results to people, LLM agents, and automation through a shared output model.
- **Configuration management** — Reuse project configuration handling while keeping application settings under your control.
- **Project filesystem operations** — Use a common interpretation of project paths and file selection.
- **Journaling and diagnostics** — Report progress and problems through a common output system.
- **Scoped application resources** — Make resources available throughout the parts of an invocation that need them.

The library also provides reusable subcommands for applications to register:

- `init` — Create project configuration from the application's template.
- `version` — Print the installed version of the application's distribution.
- `skill [DOCUMENT]` — Print packaged usage or other skill documentation supplied by the application.

## Output protocols

A protocol determines how a tool presents its results and diagnostics:

- `human` — Plain text blocks for people using a terminal.
- `llm` — Text with explicit cell boundaries and metadata for AI agents.
- `automation` — JSON Lines records for programs consuming output.

Select the protocol with the global `-p` option before the subcommand.
All three protocols use stdout by default.

## Data flow

**Domain code** performs the tool's actual work, such as finding dependencies, independently of CLI parsing and output formatting.
The **output emitter** is the shared output service that manages buffering, rendering, and writing.

1. A person, agent, or program invokes a command through the tool's CLI.
2. The CLI parses options and arguments and selects the command to run.
3. The command context chooses the effective protocol and makes an emitter available for the invocation.
4. The command calls domain code, which performs the requested work and constructs **logical cells**: typed data describing the results to present.
5. The command or domain code submits these cells to the emitter, which buffers ordinary results.
6. When delivery is due, each logical cell projects to zero or more **output cells** containing presentation data for the selected protocol.
7. Output cells format the prepared data.
8. The emitter writes the formatted output to its configured stream.

Submission and delivery happen at different times:

- Ordinary results wait for successful command completion or an explicit `flush()`; projection and formatting happen at delivery.
- Warnings are collected in submission order and delivered after results, or after reported errors when execution fails.
- Progress journal cells are processed when submitted and emitted immediately on success, so they can appear before results submitted earlier.
  Use journal messages to keep agents informed about progress during long operations, while final results are still pending.

The [output contract](specs/behavior/protocol.md) describes the complete flow and delivery rules.

## Error handling

The library distinguishes **internal errors** from **environment errors**.

Internal errors indicate programming defects or violated assumptions in the tool itself.
They are raised as exceptions, with `InternalError` as the shared base for library-defined internal failures.
Unexpected exceptions propagate through command handling without flushing pending results.

Environment errors describe expected failures in an operation's documented contract, such as invalid project configuration or an unreadable input file.
They are structured `EnvironmentError` values: a code identifies the failure kind, a message explains it, and context supplies details such as affected paths.
Environment errors can also include suggested corrections in a `ways_to_fix` list.
The rendered diagnostic includes these suggestions, so an agent can select and apply a fix automatically, then retry the command.

Operations return these values through `Result[T]`: `Ok(value)` for success or `Err(errors)` for a list of environment errors.

At the CLI boundary, `command_context` handles unsuccessful `.unwrap()` calls by reporting those environment errors as diagnostic logical cells in the selected protocol.
It discards pending ordinary results, delivers collected warnings after the diagnostics, and exits with the highest status declared by the errors.

Warnings describe non-fatal problems and do not cause command failure.
See the [error architecture](specs/architecture/errors.md) and [command error-handling contract](specs/behavior/cli.md#command-error-handling) for details.

## Scoped resources

`ContextValue[T]` makes a typed resource available to code running within a chosen execution scope.
Each resource has its own independent binding.
Code reads the active value through `.get()`, such as `runtime_config.get()` or `output.get()`; domain code can access these bindings without depending on the CLI layer.
Values can still be passed explicitly as function arguments.

Shared configuration distinguishes three lifetimes:

- **Application identity — `StaticConfig`.** Initialized before CLI parsing, it contains the tool label and optional default configuration filename.
- **Command invocation — `RuntimeConfig`.** Contains the effective output protocol.
  The shared command context establishes it together with an independently bound output emitter.
- **Selected project — `ProjectConfig`.** Contains the selected configuration path and the project directory derived from its parent.
  Shared project preparation establishes this binding after successful configuration validation.
  Commands that do not use a project need no project binding.

The application's loaded settings remain separate from `ProjectConfig`, following the application's schema and defaults.

Applications can define bindings for their own resources, such as caches or execution state, and choose the scope each resource needs.
For example, an operation can make its execution state available only while that operation runs.
Resources are prepared only where needed; these scopes do not have to follow a fixed hierarchy.

Use a binding's `scope(value)` context manager to temporarily supply or override its value; leaving the scope restores the previous binding.
Accessing an unset binding raises an internal error indicating missing setup.
Binding an object does not construct, copy, or close it; the code managing that resource owns its setup and cleanup.

See the [context architecture](specs/architecture/modules_layout.md#core-and-context) and [project scopes](specs/behavior/config.md#project-scopes) for details.

## Reusable configuration elements

Tools compose their own configuration schemas from shared fields and configuration blocks alongside application-specific settings.
Each shared element is independently reusable:

- **Configuration version — `ConfigVersion`.** Validates integer versions and provides clear diagnostics for invalid or unsupported values.
  Each tool chooses its supported versions and defaults.
- **Session directory — `SessionDir`.** Validates a project-relative path, rejecting absolute paths and parent-directory references.
  The tool owns its default location and session storage.
- **Journal configuration — `JournalConfig`.** Configures an optional command for forwarding journal records externally.
  External forwarding is disabled by default.

For example, a tool can combine these elements with its own greeting setting:

```python
from pathlib import Path
from typing import Literal

import pydantic

from llm_tool_cli.config.fields import ConfigVersion, SessionDir
from llm_tool_cli.core.entities import BaseEntity
from llm_tool_cli.output.journal import JournalConfig
from llm_tool_cli.paths import RelativeProjectPath


class Config(BaseEntity):
    version: ConfigVersion[Literal[1]] = 1
    session_dir: SessionDir = RelativeProjectPath(Path(".session"))
    journal: JournalConfig = pydantic.Field(default_factory=JournalConfig)
    greeting: str = "Hello"
```

The version constraint and defaults above belong to this example tool.
See the [configuration contract](specs/behavior/config.md) for shared loading and validation behavior.

## Quick start

This example creates a greeting in domain code and submits it from a CLI command.

With the library available in your Python environment, save this as `example.py`:

```python
import typer

from llm_tool_cli.cli.application import create_app
from llm_tool_cli.cli.context import command_context
from llm_tool_cli.core.settings import ToolLabel, initialize
from llm_tool_cli.output import output
from llm_tool_cli.protocol.logic_cells import ContentCell

initialize(label=ToolLabel("DEMO"))
app = create_app(help="A greeting tool built with llm-tool-cli.")


def greeting(name: str) -> ContentCell:
    return ContentCell(
        kind="greeting",
        media_type="text/plain",
        content=f"Hello, {name}!",
        meta={"type": "greeting", "name": name},
    )


@app.command()
def greet(context: typer.Context, name: str) -> None:
    with command_context(context):
        output.get().emit([greeting(name)]).unwrap()


if __name__ == "__main__":
    app()
```

The command context selects the protocol, establishes the active emitter, and delivers buffered results on successful completion.
No project configuration or journal setup is needed for this example.

Run the greeting command with each of the three protocols:

### Human

```bash
python example.py -p human greet Ada
```

```text
name: Ada

Hello, Ada!

```

### LLM

```bash
python example.py -p llm greet Ada
```

```text
--DEMO-CELL <id> BEGIN--
kind=greeting
media_type=text/plain
name=Ada
type=greeting

Hello, Ada!
--DEMO-CELL <id> END--
```

### Automation

```bash
python example.py -p automation greet Ada
```

```jsonl
{"content":"Hello, Ada!","id":"<id>","name":"Ada","type":"greeting"}
```

`<id>` represents a generated cell identifier.

## Integration

Use these extension points to adapt the library to your tool:

- **Custom logical cells** — Extend `LogicCell` to give protocols different presentations, or use `ContentCell` when they can share a payload.
  [Depmesh](https://github.com/Tiendil/depmesh) uses custom logical cells to present grouped dependency lists as text and individual dependency records for automation.
- **Custom output cells** — Reuse the standard formatters or specialize them, such as by subclassing `HumanOutputCell` and selecting it from a logical cell's human projection.
  Formatting stays separate from stream handling.
- **Application-owned configuration** — Supply your own schema and defaults, then use shared project scopes to locate and validate configuration and expose the active project.
  See the [configuration contract](specs/behavior/config.md).
- **Scoped resources** — Add bindings for application-owned resources using the [scoping mechanism](#scoped-resources).
- **Journal delivery** — Use `output.get().journal("Starting work").unwrap()` to report explicit progress.
  A journal-cell factory can add application context, and a journal processor can deliver records externally; the default processor performs no external delivery.
  [Donna](https://github.com/Tiendil/donna) supplies a factory that adds workflow execution context to journal cells.

See the [specification index](specs/intro.md) for the complete contracts, including [CLI support](specs/behavior/cli.md) and [project paths](specs/behavior/paths.md).
