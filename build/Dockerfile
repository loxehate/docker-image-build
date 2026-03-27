# syntax=docker/dockerfile:1.9

# Stage 1: provide Go toolchain (required by setup.py -> build_agfs_artifacts -> make build)
FROM golang:1.26-trixie AS go-toolchain

# Stage 2: provide Rust toolchain (required by setup.py -> build_ov_cli_artifact -> cargo build)
FROM rust:1.88-trixie AS rust-toolchain

# Stage 3: build Python environment with uv (builds AGFS + Rust CLI + C++ extension from source)
FROM ghcr.io/astral-sh/uv:python3.13-trixie-slim AS py-builder

# Reuse Go toolchain from stage 1 so setup.py can compile agfs-server in-place.
COPY --from=go-toolchain /usr/local/go /usr/local/go
# Reuse Rust toolchain from stage 2 so setup.py can compile ov CLI in-place.
COPY --from=rust-toolchain /usr/local/cargo /usr/local/cargo
COPY --from=rust-toolchain /usr/local/rustup /usr/local/rustup
ENV CARGO_HOME=/usr/local/cargo
ENV RUSTUP_HOME=/usr/local/rustup
ENV PATH="/usr/local/cargo/bin:/usr/local/go/bin:${PATH}"
ARG OPENVIKING_VERSION=0.0.0
ARG TARGETPLATFORM
ENV SETUPTOOLS_SCM_PRETEND_VERSION_FOR_OPENVIKING=${OPENVIKING_VERSION}

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
 && rm -rf /var/lib/apt/lists/*

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_NO_DEV=1
ENV UV_CONCURRENT_DOWNLOADS=16
ENV UV_CONCURRENT_BUILDS=8
ENV UV_CONCURRENT_INSTALLS=8
WORKDIR /app

# Copy source required for setup.py artifact builds and native extension build.
COPY Cargo.toml Cargo.lock ./
COPY pyproject.toml uv.lock setup.py README.md ./
COPY build_support/ build_support/
COPY crates/ crates/
COPY openviking/ openviking/
COPY openviking_cli/ openviking_cli/
COPY src/ src/
COPY third_party/ third_party/
COPY examples/ examples/

# Install project and dependencies (triggers setup.py artifact builds + build_extension).
RUN --mount=type=cache,target=/root/.cache/uv,id=uv-${TARGETPLATFORM} \
    uv sync --no-editable \
 && uv pip install --no-cache-dir "mcp>=1.8.0"

# Stage 4: runtime
FROM python:3.13-slim-trixie

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    libstdc++6 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=py-builder /app/.venv /app/.venv
# Ensure console frontend static assets are present in runtime site-packages.
# Some wheel/install flows may miss package_data in minimal images.
COPY --from=py-builder /app/openviking/console/static /app/.venv/lib/python3.13/site-packages/openviking/console/static
# MCP query example runtime files.
COPY --from=py-builder /app/examples/mcp-query /app/examples/mcp-query
COPY --from=py-builder /app/examples/common /app/examples/common

ENV PATH="/app/.venv/bin:$PATH"
ENV OPENVIKING_CONFIG_FILE="/app/ov.conf"
ENV OPENVIKING_HOST="0.0.0.0"
ENV OPENVIKING_PORT="1933"
ENV OPENVIKING_CONSOLE_HOST="0.0.0.0"
ENV OPENVIKING_CONSOLE_PORT="8020"
ENV OPENVIKING_CONSOLE_OPENVIKING_URL="http://127.0.0.1:1933"

ENV OPENVIKING_ENABLE_MCP="1"
ENV OPENVIKING_MCP_COMMAND="python /app/examples/mcp-query/server.py --config /app/ov.conf --data /app/data --host 0.0.0.0 --port 2033 --transport streamable-http"
ENV OPENVIKING_MCP_HOST="0.0.0.0"
ENV OPENVIKING_MCP_PORT="2033"
ENV OPENVIKING_MCP_TRANSPORT="streamable-http"
ENV OPENVIKING_MCP_DATA="/app/mcp-data"


EXPOSE 1933
EXPOSE 8020
EXPOSE 2033

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -fsS http://127.0.0.1:1933/health || exit 1


# Default runs server, console, and MCP in one container.
# Override command to run CLI, e.g.:
# docker run --rm <image> -v "$HOME/.openviking/ovcli.conf:/root/.openviking/ovcli.conf" openviking --help
CMD ["sh", "-c", "openviking-server & SERVER_PID=$!; python -m openviking.console.bootstrap --host 0.0.0.0 --port 8020 --openviking-url http://127.0.0.1:1933 --write-enabled & CONSOLE_PID=$!; MCP_PID=''; if [ \"${OPENVIKING_ENABLE_MCP}\" = '1' ] && [ -n \"${OPENVIKING_MCP_COMMAND}\" ]; then sh -c \"${OPENVIKING_MCP_COMMAND}\" & MCP_PID=$!; fi; trap 'kill $SERVER_PID $CONSOLE_PID ${MCP_PID:-} 2>/dev/null || true' TERM INT; wait $SERVER_PID $CONSOLE_PID ${MCP_PID:-}"]