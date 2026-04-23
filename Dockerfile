ARG BASE_IMAGE=nvidia/cuda:12.8.1-cudnn-runtime-ubuntu24.04
ARG TARGET=gpu

FROM ${BASE_IMAGE} AS base

RUN sed -i 's/archive.ubuntu.com/mirror.uwaterloo.ca\/ubuntu/g' /etc/apt/sources.list.d/ubuntu.sources && \
    sed -i 's/security.ubuntu.com/mirror.uwaterloo.ca\/ubuntu/g' /etc/apt/sources.list.d/ubuntu.sources

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3.12 python3.12-venv python3.12-dev \
        cmake gcc g++ \
        ffmpeg libespeak-ng1 ca-certificates && \
    rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

FROM base AS builder

ARG TARGET

RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml .
RUN uv venv /opt/venv --python python3.12 && \
    . /opt/venv/bin/activate && \
    CMAKE_MAKE_PROGRAM=/usr/bin/gmake CC=/usr/bin/gcc CXX=/usr/bin/g++ uv pip install --no-cache .
# GPU mode: install onnxruntime-gpu, then remove CPU-only onnxruntime
RUN if [ "$TARGET" = "gpu" ]; then \
        . /opt/venv/bin/activate && \
        pip install --no-cache --force-reinstall onnxruntime-gpu; \
    fi
# Fix speed < 1.0 bug: np.int32 -> np.float32 for input_ids model format
RUN sed -i 's/dtype=np.int32)/dtype=np.float32)/' /opt/venv/lib/python3.12/site-packages/kokoro_onnx/__init__.py

FROM base

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY app/ app/
COPY models/ models/
COPY voices/ voices/
COPY static/ static/

EXPOSE 5023

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5023"]
