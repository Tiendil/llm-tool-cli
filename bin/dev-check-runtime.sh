#!/usr/bin/env bash

set -e

./bin/dev-build-package.sh

PACKAGE="./dist/llm_tool_cli-$(./bin/dev.sh uv version --short)-py3-none-any.whl"

echo "Check that the built library imports"

./bin/dev.sh env UV_NO_SYNC=0 uv run --isolated --no-project --with "$PACKAGE" python -I -c 'import llm_tool_cli'
