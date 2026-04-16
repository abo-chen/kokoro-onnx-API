ARG BASE_IMAGE=nvidia/cuda:12.8.1-cudnn-runtime-ubuntu24.04

FROM ${BASE_IMAGE} AS base

RUN sed -i 's/archive.ubuntu.com/mirror.uwaterloo.ca\/ubuntu/g' /etc/apt/sources.list.d/ubuntu.sources && \
    sed -i 's/security.ubuntu.com/mirror.uwaterloo.ca\/ubuntu/g' /etc/apt/sources.list.d/ubuntu.sources

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3.12 python3.12-venv python3-pip \
        ffmpeg libespeak-ng1 ca-certificates && \
    rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

FROM base AS builder

WORKDIR /app
COPY pyproject.toml .
RUN uv venv /opt/venv --python python3.12 && \
    . /opt/venv/bin/activate && \
    uv pip install --no-cache . ; \
    if [ "$TARGET" = "gpu" ]; then \
        uv pip install --no-cache --force-reinstall onnxruntime-gpu; \
    fi

FROM base

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY app/ app/
COPY models/ models/
COPY voices/ voices/

ENV PYTHONWARNINGS="ignore::SyntaxWarning"

EXPOSE 5023

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5023"]
