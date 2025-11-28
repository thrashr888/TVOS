FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    protobuf-compiler \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster dependency management
RUN pip install uv

# Copy project files
COPY pyproject.toml .
COPY tvos ./tvos
COPY protos ./protos
COPY scripts ./scripts

# Install dependencies
RUN uv pip install --system -e .

# Compile protobufs
RUN mkdir -p tvos/protos && \
    protoc -I=protos --python_out=tvos/protos --pyi_out=tvos/protos protos/events.proto && \
    touch tvos/protos/__init__.py

# Create empty database directory
RUN mkdir -p /data

ENV DUCKDB_PATH=/data/tvos.duckdb

EXPOSE 8000 8001 8002

CMD ["python", "-m", "tvos.api"]
