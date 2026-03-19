# Development Dockerfile. Installs all development dependencies, runs as root (so the environment is mutable), intends for you to mount the directory as a volume if you're developing inside of it.
#
FROM ghcr.io/astral-sh/uv:python3.12-trixie-slim

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_TOOL_BIN_DIR=/usr/local/bin

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --no-install-project --all-groups --all-extras

COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --all-groups --all-extras

ENV PATH="/app/.venv/bin:$PATH"

ENTRYPOINT ["uv", "run"]
CMD ["/bin/bash"]
