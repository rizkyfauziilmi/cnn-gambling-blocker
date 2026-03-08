import asyncio
import os
from logging import INFO

from tqdm import tqdm

from constant.link import GAMBLING_SITES, NON_GAMBLING_SITES
from constant.path import IMAGE_PATH, TEXT_PATH
from lib.crawler import Crawler
from lib.ocr import OCR
from utils.logger import get_logger
from utils.url import get_domain


async def main() -> None:
    logger = get_logger("Scrape.Main", level=INFO)

    crawler = await Crawler.create(log_level=INFO)
    ocr = OCR(log_level=INFO)

    # --------------------------------------------------
    # Validate input, check for duplicates (throw error if any)
    # --------------------------------------------------
    all_list = NON_GAMBLING_SITES + GAMBLING_SITES
    for site in all_list:
        count = all_list.count(site)
        if count > 1:
            logger.error("Duplicate URLs found: %s site", site)
            await crawler.close()
            raise ValueError(f"Duplicate site found: {site} (count={count})")

    async def scrape_group(extra_path: str, sites: list[str], desc: str, ocr: OCR, concurrency: int = 3, isGambling: bool = False) -> None:
        logger.info(
            "Starting %s (%d sites)",
            desc.lower(),
            len(sites),
        )
        sem = asyncio.Semaphore(concurrency)

        async def run_one(u: str):
            async with sem:
                domain = get_domain(u)[1]
                save_dir = f"{IMAGE_PATH}/{extra_path}"
                mobile_path = f"{save_dir}/{domain}_mobile.png"
                desktop_path = f"{save_dir}/{domain}_desktop.png"

                text_save_dir = f"{TEXT_PATH}/{extra_path}"
                os.makedirs(text_save_dir, exist_ok=True)
                mobile_text_path = f"{text_save_dir}/{domain}_mobile.txt"
                desktop_text_path = f"{text_save_dir}/{domain}_desktop.txt"

                images_exist = os.path.exists(mobile_path) and os.path.exists(desktop_path)
                texts_exist = os.path.exists(mobile_text_path) and os.path.exists(desktop_text_path)

                if images_exist and texts_exist:
                    logger.info("Skipping %s (already exists)", u)
                    return

                if not images_exist:
                    await crawler.scrape_into_dataset(extra_path, u)

                if not texts_exist:
                    logger.debug("Performing OCR on %s mobile", u)
                    mobile_text = ocr.read_text(image_path=mobile_path, label=extra_path, min_conf=0.5 if isGambling else 0.75)
                    with open(mobile_text_path, "w", encoding="utf-8") as f:
                        f.write(mobile_text)

                    logger.debug("Performing OCR on %s desktop", u)
                    desktop_text = ocr.read_text(image_path=desktop_path, label=extra_path, min_conf=0.5 if isGambling else 0.75)
                    with open(desktop_text_path, "w", encoding="utf-8") as f:
                        f.write(desktop_text)

                    logger.info("Texts saved for %s", u)

        tasks = [asyncio.create_task(run_one(u)) for u in sites]
        with tqdm(total=len(sites), desc=desc, unit="site") as pbar:
            for fut in asyncio.as_completed(tasks):
                try:
                    await fut
                except Exception as e:
                    logger.warning("Failed to scrape site: %s", e)
                finally:
                    pbar.update(1)

        logger.info("Finished %s", desc.lower())

    try:
        await scrape_group(extra_path="non_gambling", sites=NON_GAMBLING_SITES, desc="Scraping non-gambling sites", ocr=ocr, isGambling=False)
        await scrape_group(extra_path="gambling", sites=GAMBLING_SITES, desc="Scraping gambling sites", ocr=ocr, isGambling=True)
        logger.info("Scraping job completed successfully")
    finally:
        await crawler.close()


if __name__ == "__main__":
    asyncio.run(main())
