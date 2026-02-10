import os
from logging import INFO, Logger

from utils.logger import get_logger
from utils.url import get_domain

from .constant import GAMBLING_SITES, NON_GAMBLING_SITES


def check_duplicates(sites: list[str], logger: Logger) -> None:
    logger.info("Checking for duplicate URLs in constant lists")
    all_list = sites
    for site in all_list:
        count = all_list.count(site)
        if count > 1:
            logger.error("Duplicate URLs found: %s site", site)
            raise ValueError(f"Duplicate site found: {site} (count={count})")
    logger.info("No duplicate URLs found in constant lists")


def check_file_existence(sites: list[str], directory: str, logger: Logger) -> None:
    logger.info(f"Checking for dataset file existence in {directory}")
    for site in sites:
        _, domain = get_domain(site)
        expected_files = [
            f"{directory}/{domain}_mobile.png",
            f"{directory}/{domain}_desktop.png",
        ]
        for expected_file in expected_files:
            if not os.path.isfile(expected_file):
                logger.error("Expected dataset file not found: %s", expected_file)
                raise FileNotFoundError(f"Expected dataset file not found: {expected_file}")
    logger.info("All expected dataset files are present in %s", directory)


def check_unexpected_files(directory: str, expected_files: set[str], logger: Logger) -> None:
    logger.info(f"Checking for unexpected dataset files in {directory}")
    if os.path.isdir(directory):
        for file in os.listdir(directory):
            if file not in expected_files:
                logger.warning("Unexpected file found in %s: %s", directory, file)
    logger.info("There are no unexpected dataset files in %s", directory)


def main() -> None:
    logger = get_logger("Validate.Dataset", level=INFO)

    logger.info("Validating dataset...")

    # Check for duplicates
    check_duplicates(NON_GAMBLING_SITES + GAMBLING_SITES, logger)

    # Check for dataset file existence
    check_file_existence(GAMBLING_SITES, "datasets/images/gambling", logger)
    check_file_existence(NON_GAMBLING_SITES, "datasets/images/non_gambling", logger)

    # Check for unexpected dataset files
    expected_gambling_files = {f"{get_domain(site)[1]}_{suffix}.png" for site in GAMBLING_SITES for suffix in ["mobile", "desktop"]}
    expected_non_gambling_files = {f"{get_domain(site)[1]}_{suffix}.png" for site in NON_GAMBLING_SITES for suffix in ["mobile", "desktop"]}

    check_unexpected_files("datasets/images/gambling", expected_gambling_files, logger)
    check_unexpected_files("datasets/images/non_gambling", expected_non_gambling_files, logger)

    logger.info(
        f"Dataset validation completed successfully. Checked {len(GAMBLING_SITES)} gambling sites and {len(NON_GAMBLING_SITES)} non-gambling sites. Total files checked: {len(expected_gambling_files) + len(expected_non_gambling_files)}."  # noqa: E501
    )


if __name__ == "__main__":
    main()
