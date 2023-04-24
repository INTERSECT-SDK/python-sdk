ARG REPO=code.ornl.gov:4567/rse/images/
FROM ${REPO}miniconda3:4.11.0 as conda_setup

ARG PYTHON_VERSION=3.8

RUN mkdir /app
WORKDIR /app

RUN conda install -c conda-forge python=${PYTHON_VERSION} \
    && echo "conda activate $CONDA_ENV" >> ~/.bashrc

#-------------------------------------------------------------------------------#
# To use a conda environment, must start a new bash session
# This is why we do a multi-stage build since hard / impossible from same stage
FROM conda_setup as base
ARG GITLAB_USERNAME
ARG GITLAB_PASSWORD
ARG INTERSECT_COMMON_VERSION=0.0.6
RUN python -m pip install pip --upgrade \
    && python -m pip install -i https://${GITLAB_USERNAME}:${GITLAB_PASSWORD}@code.ornl.gov/api/v4/groups/5609/-/packages/pypi/simple intersect-common==${INTERSECT_COMMON_VERSION}
