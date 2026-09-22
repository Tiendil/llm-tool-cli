#!/usr/bin/env bash

set -e

echo "Run tests"

TEST_STATUS=0
./bin/dev.sh uv run -- pytest -o cache_dir=/tmp/llm-tool-cli-pytest-cache "$@" || TEST_STATUS=$?

if [[ "$TEST_STATUS" -eq 5 && $# -eq 0 && -f ./llm_tool_cli/__init__.py && ! -s ./llm_tool_cli/__init__.py \
    && -z "$(find ./llm_tool_cli -type f -name '*.py' ! -path './llm_tool_cli/__init__.py' -print -quit)" ]]; then
    echo "No tests collected: the initial library package is empty."
    exit 0
fi

exit "$TEST_STATUS"
