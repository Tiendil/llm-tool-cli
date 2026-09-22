#!/usr/bin/bash

set -e

echo "run autoflake"

./bin/dev.sh uv run -- autoflake ./llm_tool_cli

echo "run isort"

./bin/dev.sh uv run -- isort ./llm_tool_cli

echo "run black"

./bin/dev.sh uv run -- black ./llm_tool_cli
