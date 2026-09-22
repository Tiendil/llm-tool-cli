FROM python:3.12

COPY --from=ghcr.io/astral-sh/uv:0.11.14 /uv /uvx /bin/

RUN apt-get update \
    && apt-get install --yes --no-install-recommends ripgrep \
    && rm -rf /var/lib/apt/lists/*

ARG UID=1000
ARG GID=1000
ARG PROJECT_USER=llm-tool-cli

RUN groupadd --gid "$GID" "$PROJECT_USER" \
    && useradd --create-home --uid "$UID" --gid "$PROJECT_USER" --shell /bin/bash "$PROJECT_USER"

USER $PROJECT_USER
WORKDIR /repository

ENV UV_PROJECT_ENVIRONMENT=/home/llm-tool-cli/.venv
ENV UV_PYTHON_DOWNLOADS=never
ENV UV_LINK_MODE=copy
ENV LLM_TOOL_CLI_DEV_CONTAINER=1
ENV PATH="/home/llm-tool-cli/.venv/bin:/home/llm-tool-cli/.local/bin:${PATH}"

RUN uv tool install "donna==0.4.1"

COPY --chown=$PROJECT_USER:$PROJECT_USER . /repository

RUN uv sync --locked

ENV UV_NO_SYNC=1

CMD []
