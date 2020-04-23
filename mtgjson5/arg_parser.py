"""
MTGJSON Arg Parser to determine what actions to take
"""
import argparse
import logging
import pathlib
import sys
from typing import List

from .compiled_classes import MtgjsonStructuresObject
from .consts import BAD_FILE_NAMES, OUTPUT_PATH
from .providers import ScryfallProvider

LOGGER = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """
    Parse command line arguments from user to determine how to spawn up
    MTGJSON and complete the request.
    :return: Namespace of requests
    """
    parser = argparse.ArgumentParser("mtgjson5")

    # What set(s) to build
    sets_group = parser.add_mutually_exclusive_group()
    sets_group.add_argument(
        "-s",
        "--sets",
        type=str.upper,
        nargs="*",
        metavar="SET",
        default=[],
        help="Sets to build, using Scryfall set code notation. Non-existent sets shall be ignored.",
    )
    sets_group.add_argument(
        "-a",
        "--all-sets",
        action="store_true",
        help="Build all possible sets, overriding the --sets option.",
    )

    parser.add_argument(
        "-c",
        "--full-build",
        action="store_true",
        help="Trigger a new price build, as well as building MTGSQLite, and constructing compiled outputs.",
    )
    parser.add_argument(
        "-x",
        "--resume-build",
        action="store_true",
        help="While determine what sets to build, ignore individual set files found in the json_* output directory.",
    )
    parser.add_argument(
        "-z",
        "--compress",
        action="store_true",
        help="Compress the json_* output folder's contents for distribution.",
    )
    parser.add_argument(
        "-p",
        "--pretty",
        action="store_true",
        help="When dumping JSON files, prettify the contents instead of minify-ing them.",
    )
    parser.add_argument(
        "-m",
        "--price-build",
        action="store_true",
        help="Compile updated pricing data and only updated pricing, disregarding all other flags and operations.",
    )
    parser.add_argument(
        "--skip-sets",
        type=str.upper,
        nargs="*",
        metavar="SET",
        default=[],
        help="Purposely exclude sets from the build that may have been set using --sets or --all.",
    )
    parser.add_argument(
        "--referrals",
        action="store_true",
        help="Create and maintain a referral map for MTGJSON linkages.",
    )

    # Show help menu if no arguments are passed
    if len(sys.argv) == 1:
        parser.print_help()
        parser.exit()

    return parser.parse_args()


def get_sets_already_built() -> List[str]:
    """
    Grab sets that have already been compiled by the system
    :return: List of all set codes found
    """
    json_output_files: List[pathlib.Path] = list(OUTPUT_PATH.glob("**/*.json"))

    set_codes_found = list(
        {file.stem for file in json_output_files}
        - set(MtgjsonStructuresObject().get_all_compiled_file_names())
    )

    LOGGER.info(f"Sets Built Already: {', '.join(set_codes_found)}")

    set_codes_found = [
        set_code[:-1] if set_code[:-1] in BAD_FILE_NAMES else set_code
        for set_code in set_codes_found
    ]

    return set_codes_found


def get_all_scryfall_sets() -> List[str]:
    """
    Grab all sets that Scryfall currently supports
    :return: Scryfall sets
    """
    scryfall_instance = ScryfallProvider()
    scryfall_sets = scryfall_instance.download(scryfall_instance.ALL_SETS_URL)

    if scryfall_sets["object"] == "error":
        LOGGER.error(f"Downloading Scryfall data failed: {scryfall_sets}")
        return []

    # Get _ALL_ Scryfall sets
    scryfall_set_codes = [
        set_obj["code"].upper()
        for set_obj in scryfall_sets["data"]
        if set_obj["set_type"] != "token"
    ]

    return sorted(scryfall_set_codes)


def get_sets_to_build(args: argparse.Namespace) -> List[str]:
    """
    Grab what sets to build given build params
    :param args: CLI args
    :return: List of sets to construct, alphabetically
    """
    if args.resume_build:
        # Exclude sets we have already built
        args.skip_sets.extend(get_sets_already_built())

    if not args.all_sets:
        # We have a sub-set list, so only return what we want
        return sorted(list(set(args.sets) - set(args.skip_sets)))

    scryfall_sets = get_all_scryfall_sets()

    # Remove Scryfall token sets (but leave extra sets)
    non_token_sets = {
        s for s in scryfall_sets if not (s.startswith("T") and s[1:] in scryfall_sets)
    }

    # Remove sets to skip
    return_list = list(non_token_sets - set(args.skip_sets))

    return sorted(return_list)
