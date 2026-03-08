import csv
import os
from collections import Counter
from logging import INFO, Logger

from constant.link import GAMBLING_SITES, NON_GAMBLING_SITES
from constant.path import (
    GAMBLING_IMAGE_PATH,
    GAMBLING_TEXT_PATH,
    MASTER_DATASET_PATH,
    NON_GAMBLING_IMAGE_PATH,
    NON_GAMBLING_TEXT_PATH,
)
from utils.logger import get_logger
from utils.url import get_domain


def check_duplicates(sites: list[str], logger: Logger):
    logger.info("Checking duplicate URLs")

    duplicates = [s for s, c in Counter(sites).items() if c > 1]

    if duplicates:
        raise ValueError(f"Duplicate URLs detected: {duplicates}")

    logger.info("No duplicate URLs found")


def check_domain_collision(sites: list[str], logger: Logger):
    logger.info("Checking domain collisions")

    domains = [get_domain(site)[1] for site in sites]

    duplicates = [d for d, c in Counter(domains).items() if c > 1]

    if duplicates:
        raise ValueError(f"Duplicate domains after normalization: {duplicates}")

    logger.info("No domain collisions detected")


def check_file_existence(sites: list[str], image_directory: str, text_directory: str, logger: Logger):
    logger.info("Checking dataset files")

    missing = []

    for site in sites:
        _, domain = get_domain(site)

        expected_files = [
            f"{image_directory}/{domain}_mobile.png",
            f"{image_directory}/{domain}_desktop.png",
            f"{text_directory}/{domain}_mobile.txt",
            f"{text_directory}/{domain}_desktop.txt",
        ]

        for file in expected_files:
            if not os.path.isfile(file):
                missing.append(file)

    if missing:
        for f in missing:
            logger.error("Missing file: %s", f)
        raise FileNotFoundError("Dataset files missing")

    logger.info("All expected files exist")


def validate_master_dataset_csv(logger: Logger):
    logger.info("Validating master_dataset.csv")

    if not os.path.isfile(MASTER_DATASET_PATH):
        raise FileNotFoundError("master_dataset.csv missing")

    expected_rows = (len(GAMBLING_SITES) + len(NON_GAMBLING_SITES)) * 2

    ids = set()
    missing_files = []

    with open(MASTER_DATASET_PATH, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if len(rows) != expected_rows:
        raise ValueError(f"CSV row mismatch: expected {expected_rows}, got {len(rows)}")

    for row in rows:
        data_id = row["data_id"]

        if data_id in ids:
            raise ValueError(f"Duplicate data_id: {data_id}")

        ids.add(data_id)

        image_path = row["image_path"]
        text_path = row["text_path"]

        if not os.path.isfile(image_path):
            missing_files.append(image_path)

        if not os.path.isfile(text_path):
            missing_files.append(text_path)

    if missing_files:
        for f in missing_files:
            logger.error("CSV referenced file missing: %s", f)
        raise FileNotFoundError("CSV references missing files")

    logger.info("master_dataset.csv validation passed")


def main():
    logger = get_logger("Validate.Dataset", level=INFO)

    logger.info("Starting dataset validation")

    all_sites = NON_GAMBLING_SITES + GAMBLING_SITES

    check_duplicates(all_sites, logger)
    check_domain_collision(all_sites, logger)

    check_file_existence(GAMBLING_SITES, GAMBLING_IMAGE_PATH, GAMBLING_TEXT_PATH, logger)
    check_file_existence(NON_GAMBLING_SITES, NON_GAMBLING_IMAGE_PATH, NON_GAMBLING_TEXT_PATH, logger)

    validate_master_dataset_csv(logger)

    logger.info("Dataset validation completed successfully")


if __name__ == "__main__":
    main()
