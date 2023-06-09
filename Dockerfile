# development container - not meant to be extensible

ARG REPO=code.ornl.gov:4567/rse/images/
FROM ${REPO}python:3.8-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    PDM_VERSION=2.7.1
# uncomment to allow prereleases to be installed
#ENV PDM_PRERELEASE=1
ENV PATH="$HOME/.local/bin:$PATH"

RUN apt update \
    && apt install -y curl make \
    && rm -rf /var/lib/apt/lists/* \
    && curl -sSL https://raw.githubusercontent.com/pdm-project/pdm/main/install-pdm.py | python -

WORKDIR /sdk
COPY . .
# install all optional and development dependencies
RUN pdm install -G:all
