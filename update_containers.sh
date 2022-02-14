#!/bin/bash

DIR=/nfs/dust/atlas/user/pgadow/ftag/containers/btagging
CACHEDIR=/tmp/${USER}/singularity_cache

# set cache dir for singularity
export SINGULARITY_CACHEDIR=${CACHEDIR}

# delete old images
rm -rf $DIR/umamibase

# download new images
singularity build --sandbox $DIR/umamibase docker://gitlab-registry.cern.ch/atlas-flavor-tagging-tools/algorithms/umami/umamibase:latest

# clean up
rm -rf ${CACHEDIR}
