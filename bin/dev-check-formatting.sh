#!/usr/bin/bash

set -e

echo "run isort"

./bin/dev.sh uv run -- isort --check-only ./llm_tool_cli

echo "run black"

./bin/dev.sh uv run -- black --check ./llm_tool_cli
