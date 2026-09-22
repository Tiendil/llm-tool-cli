#!/usr/bin/bash

if [[ "${LLM_TOOL_CLI_DEV_CONTAINER:-}" == "1" ]]; then
    exec "$@"
fi

docker compose run --rm llm-tool-cli "$@"
