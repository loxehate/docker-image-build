# syntax=docker/dockerfile:1

FROM docker:29-cli AS docker_cli
FROM ghcr.io/astral-sh/uv:0.13.5 AS uv_binary

FROM python:3.13-slim-trixie

COPY --from=uv_binary /uv /uvx /bin/
COPY --from=docker_cli /usr/local/bin/docker /usr/bin/docker

WORKDIR /app

ENV UV_NO_DEV=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:${PATH}"

COPY pyproject.toml uv.lock README.md LICENSE ./
RUN uv sync --locked --no-install-project

COPY src ./src
COPY run.py ./
RUN uv sync --locked

ENTRYPOINT ["/app/.venv/bin/python", "/app/run.py"]
CMD ["--help"]
