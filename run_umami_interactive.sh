#!/bin/bash

# Settings
WORKDIR="/afs/desy.de/user/p/pgadow/atlas/ftag/umami"
IMAGE="/nfs/dust/atlas/user/pgadow/ftag/containers/btagging/umamibase"

# Run Umami interactively
singularity exec \
    --contain \
    --bind /afs:/afs --bind /nfs:/nfs --bind /cvmfs:/cvmfs --bind /pnfs:/pnfs --bind /tmp:/tmp \
    ${IMAGE} \
    /bin/bash -rcfile ${PWD}/singularity/singularity_bashrc
