import asyncio
from logging import DEBUG

from tqdm import tqdm

from utils.logger import get_logger

from .constant import GAMBLING_SITES, NON_GAMBLING_SITES
from .instance import Scraper


async def main() -> None:
    logger = get_logger("Scraper.Main", level=DEBUG)

    logger.info("Initializing async scraper")
    scraper = await Scraper.create(log_level=DEBUG)

    # --------------------------------------------------
    # Validate input, check for duplicates (throw error if any)
    # --------------------------------------------------
    all_list = NON_GAMBLING_SITES + GAMBLING_SITES
    for site in all_list:
        count = all_list.count(site)
        if count > 1:
            logger.error("Duplicate URLs found: %s site", site)
            await scraper.close()
            raise ValueError(f"Duplicate site found: {site} (count={count})")

    async def scrape_group(extra_path: str, sites: list[str], desc: str, concurrency: int = 3) -> None:
        logger.info(
            "Starting %s (%d sites)",
            desc.lower(),
            len(sites),
        )
        sem = asyncio.Semaphore(concurrency)

        async def run_one(u: str):
            async with sem:
                await scraper.scrape_into_dataset(extra_path, u)

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
        await scrape_group("non_gambling", NON_GAMBLING_SITES, "Scraping non-gambling sites")
        await scrape_group("gambling", GAMBLING_SITES, "Scraping gambling sites")
        logger.info("Scraping job completed successfully")
    finally:
        await scraper.close()


if __name__ == "__main__":
    asyncio.run(main())
