# This Dockerfile allows you to quickly build and run the docs website in Docker.
# it is built from an existing intersect-sdk image, there is no other build context
# run this command to build it from the repository root:
#       docker build --build-arg IMAGE=<YOUR_INTERSCT_SDK_IMAGE_HERE> -t intersect-sdk-python-docs - < docs/Dockerfile

ARG IMAGE
ARG NGINX_IMAGE=

# Build the HTML from docs
FROM ${IMAGE} as docs
WORKDIR /sdk/docs
ENV SPHINXOPTS="-W --keep-going"
RUN pdm run make html

# Nginx to serve HTML
FROM ${NGINX_IMAGE}nginx:1.22-alpine as server
COPY --from=docs /sdk/docs/_build/html /usr/share/nginx/html
