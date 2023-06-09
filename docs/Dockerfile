ARG IMAGE=code.ornl.gov:4567/intersect/sdk/python-sdk/sdk/base/next
ARG TAG=latest
ARG NGINX_IMAGE=code.ornl.gov:4567/rse/images/

# Build the HTML from docs
FROM ${IMAGE}:${TAG} as docs
WORKDIR /sdk
RUN cd docs && make html

# Nginx to serve HTML
FROM ${NGINX_IMAGE}nginx:1.22-alpine as server
COPY --from=docs /sdk/docs/_build/html /usr/share/nginx/html
