# container for CI/CD or development - NOT meant to be an extensible Docker image with the installed package

ARG REPO=

# use this stage for development
FROM ${REPO}python:3.8-slim as minimal

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    PDM_VERSION=2.17.3 \
    PDM_HOME=/usr/local
# uncomment to allow prereleases to be installed
#ENV PDM_PRERELEASE=1
ENV PATH="/root/.local/bin:$PATH"

RUN apt update \
    && apt install -y curl make \
    && rm -rf /var/lib/apt/lists/* \
    && curl -sSL https://raw.githubusercontent.com/pdm-project/pdm/main/install-pdm.py | python -

WORKDIR /sdk
# add minimal files needed for build
COPY pyproject.toml pdm.lock README.md ./
COPY src/intersect_sdk/version.py src/intersect_sdk/version.py
RUN pdm sync --dev -G:all

# use this stage in CI/CD, not useful in development
FROM minimal as complete
COPY . .
