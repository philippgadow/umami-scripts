#!/bin/bash

DIR=/nfs/dust/atlas/user/pgadow/ftag/containers/btagging
CACHEDIR=/tmp/${USER}/singularity_cache

# set cache dir for singularity
export SINGULARITY_CACHEDIR=${CACHEDIR}

# delete old images
rm -rf $DIR/umami
rm -rf $DIR/umami-gpu

# download new images
singularity build --sandbox $DIR/umami docker://btagging/umami:latest
singularity build --sandbox $DIR/umami-gpu docker://btagging/umami:latest-gpu

# clean up
rm -rf ${CACHEDIR}

