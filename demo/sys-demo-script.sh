#!/bin/bash

workdir=$PWD
[ ! -d logs ] && mkdir logs

# Make sure all docker compose deployments use same network
export COMPOSE_PROJECT_NAME=intersect

# Initialize Python SDK virtual environment
[ -z "$INTERSECT_PYTHON_SDK_ROOT" ] && echo "Please set INTERSECT_PYTHON_SDK_ROOT" && exit 1
cd $INTERSECT_PYTHON_SDK_ROOT
source venv/bin/activate

if [ ${bootstrap_demo:-0} -eq 1 ]; then
    # Start the INTERSECT message broker and minio
    docker compose up -d
    sleep 5

    # Start the neo4j container
    docker run --network=intersect_default --detach --publish=7474:7474 --publish=7687:7687 neo4j:latest
    # Login to local web interface to set new password (community edition mandatory step)
    # 1. open local web interface at http://localhost:7474/browser/
    # 2. use 'bolt://'' connection, user is neo4j, password is neo4j
    # 3. upon prompt, enter 'intersect' as new password
    read -t 120 -p "Please connect to http://localhost:7474/browser/ and change password to 'intersect'. Hit RETURN when complete" ready
fi

# Start ORNL domain registry
org="ORNL"
lower_org="ornl"
fac=$org
lower_fac=$lower_org
sys="intersect"
subsys="infrastructure-management"
export INTERSECT_ORGANIZATION_NAME=$lower_org
export INTERSECT_FACILITY_NAME=$lower_fac
export INTERSECT_SYSTEM_NAME=$sys
export INTERSECT_SUBSYSTEM_NAME=$subsys
export INTERSECT_SERVICE_NAME="${lower_org}-registry"
export INTERSECT_SERVICE_DESCRIPTION="The domain registrar for $org.$fac"
export INTERSECT_DOMAIN_REGISTRAR="${INTERSECT_ORGANIZATION_NAME}.${INTERSECT_FACILITY_NAME}.${INTERSECT_SYSTEM_NAME}.${INTERSECT_SUBSYSTEM_NAME}.${INTERSECT_SERVICE_NAME}"
( python -m capability_catalog.system.systems_registrar.server ) 2>&1 >$workdir/logs/$INTERSECT_SYSTEM_NAME.$INTERSECT_SERVICE_NAME.$$.log &
sleep 5

# Start ORNL domain ER catalog
subsys="data-management"
export INTERSECT_ORGANIZATION_NAME=$lower_org
export INTERSECT_FACILITY_NAME=$lower_fac
export INTERSECT_SYSTEM_NAME=$sys
export INTERSECT_SUBSYSTEM_NAME=$subsys
export INTERSECT_SERVICE_NAME="${lower_org}-catalog"
export INTERSECT_SERVICE_DESCRIPTION="The domain entity-relationship catalog for $org.$fac"
export INTERSECT_DOMAIN_CATALOG="${INTERSECT_ORGANIZATION_NAME}.${INTERSECT_FACILITY_NAME}.${INTERSECT_SYSTEM_NAME}.${INTERSECT_SUBSYSTEM_NAME}.${INTERSECT_SERVICE_NAME}"
( python -m capability_catalog.data.er_catalog.neo4j_server ) 2>&1 >$workdir/logs/$INTERSECT_SYSTEM_NAME.$INTERSECT_SERVICE_NAME.$$.log &
sleep 5

# Start system management service for OLCF Frontier
fac="OLCF"
lower_fac="olcf"
sys="frontier"
subsys="infrastructure-management"
resources="Frontier-hpc,Orion-lustre,ccshome-nfs,ccsproj-nfs"
export INTERSECT_ORGANIZATION_NAME=$lower_org
export INTERSECT_FACILITY_NAME=$lower_fac
export INTERSECT_SYSTEM_NAME=$sys
export INTERSECT_SYSTEM_RESOURCES=$resources
export INTERSECT_SUBSYSTEM_NAME=$subsys
export INTERSECT_SERVICE_NAME="system-manager"
export INTERSECT_SERVICE_DESCRIPTION="The system management service for $org.$fac.$sys"
( python -m capability_catalog.system.system_manager.server ) 2>&1 >$workdir/logs/$INTERSECT_SYSTEM_NAME.$INTERSECT_SERVICE_NAME.$$.log &
sleep 5

# Start system management service for Spallation Neutron Source (SNS) First Target Station
fac="SNS"
lower_fac="sns"
sys="first-target-station"
resources="EQ-SANS-sans,HYSPEC-spectrometer,MAGREF-reflectometer,NOMAD-diffractometer"
export INTERSECT_ORGANIZATION_NAME=$lower_org
export INTERSECT_FACILITY_NAME=$lower_fac
export INTERSECT_SYSTEM_NAME=$sys
export INTERSECT_SYSTEM_RESOURCES=$resources
export INTERSECT_SUBSYSTEM_NAME=$subsys
export INTERSECT_SERVICE_NAME="system-manager"
export INTERSECT_SERVICE_DESCRIPTION="The system management service for $org.$fac.$sys"
( python -m capability_catalog.system.system_manager.server ) 2>&1 >$workdir/logs/$INTERSECT_SYSTEM_NAME.$INTERSECT_SERVICE_NAME.$$.log &
sleep 5

# Start system management service for Center for Nanophase Materials Scienc (CNMS) STEM system
fac="CNMS"
lower_fac="cnms"
sys="stem"
resources="Jeol-neoarm,Nion-UltraSTEM,Nion-Hermes,FEI-Titan"
export INTERSECT_ORGANIZATION_NAME=$lower_org
export INTERSECT_FACILITY_NAME=$lower_fac
export INTERSECT_SYSTEM_NAME=$sys
export INTERSECT_SYSTEM_RESOURCES=$resources
export INTERSECT_SUBSYSTEM_NAME=$subsys
export INTERSECT_SERVICE_NAME="system-manager"
export INTERSECT_SERVICE_DESCRIPTION="The system management service for $org.$fac.$sys"
( python -m capability_catalog.system.system_manager.server ) 2>&1 >$workdir/logs/$INTERSECT_SYSTEM_NAME.$INTERSECT_SERVICE_NAME.$$.log &
sleep 5

# deactivate virtual environment
deactivate
