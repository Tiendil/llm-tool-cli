#!/usr/bin/bash

set -e

echo "run tach"

./bin/dev.sh uv run -- tach check

echo "run autoflake"

./bin/dev.sh uv run -- autoflake --check --quiet ./llm_tool_cli

echo "run flake8"

./bin/dev.sh uv run -- flake8 ./llm_tool_cli

echo "run mypy"

./bin/dev.sh uv run -- mypy --show-traceback ./llm_tool_cli
