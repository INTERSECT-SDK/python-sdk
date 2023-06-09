# Helm chart

Most templates are based off of the [Bitnami Charts Template](https://github.com/bitnami/charts/tree/main/template/])

We also use the Bitnami Common library to try and standardize some boilerplate across all charts.

## Linting

You'll need helm to be installed on your system, but you don't need to have a Kubernetes server configuration set up.

1) Change directory into `chart` if you haven't already.
2) `helm dependency update` (if Chart.lock already exists, use `helm dependency build` instead; if `charts` directory exists in this directory, you can either skip this step or first remove .tgz files from `charts`)
3) `helm lint .`
