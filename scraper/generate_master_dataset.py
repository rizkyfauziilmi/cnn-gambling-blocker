import csv
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

"""
Dataset Generator for Website Classification

This script converts lists of URLs into a structured CSV dataset used for
gambling vs non-gambling website classification.

Each domain produces two records:
- desktop viewport
- mobile viewport

ID format:
    JD_001_DSK
    │  │   └── viewport code (DSK = desktop, MBL = mobile)
    │  └────── incremental domain index
    └───────── label prefix (JD = judi, NJ = non_judi)

Output CSV fields:
- data_id
- domain
- viewport
- image_path
- text_path
- label_name
- label_code
"""


def generate_rows(
    sites: list[str],
    label_name: str,
    label_code: int,
    prefix: str,
    image_directory: str,
    text_directory: str,
    logger: Logger,
    start_index: int = 1,
) -> list[dict]:
    rows = []
    index = start_index

    viewports = {"desktop": "DSK", "mobile": "MBL"}

    logger.info("Generating rows for label '%s' (%s sites)", label_name, len(sites))

    for url in sites:
        _, domain = get_domain(url)

        logger.debug("Processing domain: %s", domain)

        for viewport, vp_code in viewports.items():
            data_id = f"{prefix}_{index:03}_{vp_code}"

            rows.append(
                {
                    "data_id": data_id,
                    "domain": domain,
                    "viewport": viewport,
                    "image_path": f"{image_directory}/{domain}_{viewport}.png",
                    "text_path": f"{text_directory}/{domain}_{viewport}.txt",
                    "label_name": label_name,
                    "label_code": label_code,
                }
            )

        index += 1

    logger.info("Generated %s rows", len(rows))

    return rows


def save_to_csv(rows: list[dict], filename: str, logger: Logger) -> None:
    logger.info("Saving CSV to %s", filename)

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "data_id",
                "domain",
                "viewport",
                "image_path",
                "text_path",
                "label_name",
                "label_code",
            ],
        )

        writer.writeheader()
        writer.writerows(rows)

    logger.info("CSV saved (%s rows)", len(rows))


def main() -> None:
    logger = get_logger("Generate.Dataset", level=INFO)

    logger.info("Starting dataset generation")

    data = []

    data.extend(
        generate_rows(
            GAMBLING_SITES,
            "judi",
            1,
            "JD",
            GAMBLING_IMAGE_PATH,
            GAMBLING_TEXT_PATH,
            logger,
        )
    )

    data.extend(
        generate_rows(
            NON_GAMBLING_SITES,
            "non_judi",
            0,
            "NJ",
            NON_GAMBLING_IMAGE_PATH,
            NON_GAMBLING_TEXT_PATH,
            logger,
        )
    )

    save_to_csv(data, MASTER_DATASET_PATH, logger)

    expected_rows = (len(GAMBLING_SITES) + len(NON_GAMBLING_SITES)) * 2

    logger.info("Expected rows: %s", expected_rows)
    logger.info("Generated rows: %s", len(data))


if __name__ == "__main__":
    main()
