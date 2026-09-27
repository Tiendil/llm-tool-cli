# llm-tool-cli

A small Python support library for LLM-oriented CLI tools.
Its scope and API are still being defined; `llm_tool_cli` provides configuration mechanics, lexical project-path normalization, and shared entity and result infrastructure.

## Development

Requires Docker with Compose.

```bash
./bin/dev-build-containers.sh
./bin/dev-check-formatting.sh
./bin/dev-check-semantics.sh
```

See [AGENTS.md](AGENTS.md) for development instructions and Donna/Depmesh integration.

[Specifications](specs/intro.md) · [Changelog](CHANGELOG.md) · [License](LICENSE)
