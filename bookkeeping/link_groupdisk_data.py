#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This Script creates links from local groupdisk to your dust/afs
usage example:
    createLinksToSRMFiles.py --pattern user.jvonahne:user.jvonahne.mc16_13TeV.31168* -o testLinks
    createLinksToSRMFiles --sampleList didList.txt --scope user.jvonahne -o testLinks
"""

import sys
import argparse
import os
import subprocess
import logging
import shutil

LOGGER = logging.getLogger(__name__)


def comandline_argument_parser(parser=None):
    if not parser:
        parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--logging-level",
        default="warning",
        choices=["notset", "debug", "info", "warning", "error", "critical"],
        help="Logging level",
    )
    parser.add_argument("--logging-file", help="Logging file name")
    parser.add_argument(
        "--pattern", type=str, help="Pattern which will be used by rucio to get a list of samples"
    )
    parser.add_argument(
        "--sampleList", type=str, nargs="*", help="List of text files which contain the rucio DIDs"
    )
    parser.add_argument(
        "--containers", type=str, nargs="*", help="List of container names"
    )    
    parser.add_argument("-s", "--scope", default=None, help="rucio scope of samples")
    parser.add_argument("--copy", action='store_true', default=False, help="Copy files instead of symbolic links")
    parser.add_argument(
        "--output_dir",
        "-o",
        default="samples",
        help="Path to the output directory where the symbolic links will be stored. Will be created in case it doesn't exist yet.",
    )
    return parser


def checkArguments(args):
    if not args.output_dir:
        LOGGER.critical("No output directory specified! use -o/--output_dir.")
        sys.exit(1)
    if not only1([args.pattern, args.sampleList, args.containers]):
        LOGGER.critical("Please provider either --sampleList OR --pattern OR --containers")
        sys.exit(1)
    if args.pattern and args.scope:
        if ":" in args.pattern:
            LOGGER.warning("found ':' in pattern so --scope will be ignored")
    elif args.pattern:
        if ":" not in args.pattern:
            try:
                args.scope = ".".join(args.pattern.split(".")[:2])
                LOGGER.warning(
                    "Can't find scope. Guessing scope to be: '{}'. Please use --scope if the guessed scope is wrong.".format(
                        args.scope
                    )
                )
            except:
                LOGGER.critical("Can't find scope. Please use --scope")
                sys.exit(1)
    elif args.sampleList:
        foundMix = False
        foundScope = False
        for f in args.sampleList:
            with open(f, "r") as iFile:
                scopeInLine = map(lambda x: ":" in x, iFile.readlines())
                if all(scopeInLine):
                    foundScope = True
                elif any(scopeInLine):
                    foundMix = True
                    foundScope = True
        if foundMix:
            LOGGER.critical(
                "Found ':' only sometimes. Either use it in all dids or in none and give --scope. Also check for empty lines"
            )
            sys.exit(1)
        if foundScope and args.scope:
            LOGGER.warning("Found scope in dids. Will ignore --scope!")


def only1(l):
    return sum(bool(e) for e in l) == 1


def main(args):
    checkArguments(args)
    if not os.getenv("RUCIO_HOME"):
        LOGGER.critical("Setup rucio and grid credentials ie voms-proxy-init -voms atlas!")
        sys.exit(1)

    if args.pattern:
        pattern = args.pattern.split(":")[-1]
    outputdir = args.output_dir
    scopename = args.scope

    import rucio.client

    ruc = rucio.client.Client()

    #####################
    # Start of the script
    #####################
    samples = []
    if args.sampleList:
        for fi in args.sampleList:
            with open(fi, "r") as sampleListFile:
                for l in sampleListFile:
                    sampleName = l.strip("\n")
                    if ":" not in l:
                        sampleName = args.scope + ":" + sampleName
                    samples.append(l.strip())
    elif args.pattern:
        if ":" in args.pattern:
            scopename = args.pattern.split(":")[0]
        for did in ruc.list_dids(
            scope=scopename, filters={"name": pattern}, long=False
        ):
            samples.append(did)
    elif args.containers:
        for c in args.containers:
            if ":" in c:
                scopename,cname = c.split(":")
            else:
                cname = c
            for did in ruc.list_files(
                    name=cname, scope=scopename, long=False
            ):
                samples.append(did["scope"]+":"+did["name"])
        
    if not samples:
        sys.exit(
            'There were no samples found for the pattern "'
            + pattern
            + '" in scope "'
            + scopename
            + '". (Maybe change the scopename?) Exiting.'
        )
    else:
        LOGGER.info("found %s samples", len(samples))

    # For each sample, make a list of corresponding files
    # For each file, check whether the file can be found on the DESY-HH_LOCALGROUPDISK
    # If a file is not there, print a message and exit
    LOGGER.info(
        "Checking if all datasets were properly replicated to DESY-HH_LOCALGROUPDISK. This might take a few minutes."
    )
    samples_files = []
    bad_samples = []
    i_sample = 0
    n_samples = str(len(samples))
    for sample in samples:
        sampleName = sample
        if ":" in sample:
            scopename = sample.split(":")[0]
            sampleName = sample.split(":")[1]
        i_sample += 1
        LOGGER.info("Checking sample " + str(i_sample) + " of " + n_samples + ": " + sample)
        files = []
        n_bad_files = 0
        n_tot_files = 0
        all_files_ok = True
        for f in ruc.list_replicas([{"scope": scopename, "name": sampleName}]):
            if type(f) is not dict:
                LOGGER.warning("something went wrong for: " + scopename + " " + sampleName)
                bad_samples.append([sample, 0, 0])
                break
            rse_path = f["rses"].get("DESY-HH_LOCALGROUPDISK")
            n_tot_files += 1
            if not rse_path:
                LOGGER.warning(
                    "WARNING: Some files of dataset "
                    + sample
                    + " cannot be found on DESY-HH_LOCALGROUPDISK. Maybe the sample is not finished on grid or replication is stuck/failed."
                )
                all_files_ok = False
                n_bad_files += 1
                continue
            srm_path_unformatted = rse_path[0]
            srm_path_unformatted = srm_path_unformatted.replace(
                "davs://dcache-atlas-webdav.desy.de:2880", "/pnfs/desy.de/atlas"
            )
            srm_path = srm_path_unformatted[srm_path_unformatted.find("/pnfs/") :]
            files.append(srm_path)
        if not all_files_ok:
            bad_samples.append([sample, n_tot_files, n_bad_files])
        samples_files.append([sample, files])

    if not bad_samples:
        LOGGER.info("All samples are OK! Proceeding to create links.")
    else:
        LOGGER.warning(
            "These sample cannot be found at all or only incomplete at DESY-HH_LOCALGROUPDISK:"
        )
        for bs in bad_samples:
            LOGGER.warning(
                "\t" + bs[0] + ": missing " + str(bs[2]) + " out of " + str(bs[1]) + " files."
            )
        user_dec = ""
        while user_dec != "y" and user_dec != "n":
            user_dec = input("Do you want to proceed to create links? [y/n] ")
        if user_dec == "n":
            exit()

    if not outputdir.endswith("/"):
        outputdir += "/"

    if os.path.isdir(outputdir):
        LOGGER.info("Write links into " + outputdir)
    else:
        os.makedirs(outputdir)
        LOGGER.info("Created " + outputdir + ". Write symbolic links here.")

    for sf in samples_files:
        sample = sf[0]
        dirname = sample.split(".root")[0]  # drop .root extension if present
        dirname = dirname.split(":")[-1]  # drop scope if present
        if os.path.isdir(os.path.join(outputdir, dirname)):
            LOGGER.info("Output directory", outputdir + dirname, "exists, skipping.")
            continue

        os.makedirs(os.path.join(outputdir, dirname))
        for logical_file_path in sf[1]:
            linkname = logical_file_path.split("/")[-1]

            if args.copy:
                shutil.copyfile(logical_file_path, os.path.join(outputdir, dirname, linkname))
            else:
                os.symlink(logical_file_path, os.path.join(outputdir, dirname, linkname))

    LOGGER.info("Done creating links. Check if everything went as expected e.g.: ls " + outputdir)


if __name__ == "__main__":
    parser = comandline_argument_parser()
    command_line_arguments = parser.parse_args()
    logging.basicConfig(
        filename=command_line_arguments.logging_file,
        format="%(levelname)s [%(filename)s:%(lineno)s - %(funcName)s() ]: %(message)s",
    )
    LOGGER.setLevel(getattr(logging, command_line_arguments.logging_level.upper()),)
    LOGGER.info(command_line_arguments)
    sys.exit(main(command_line_arguments))

