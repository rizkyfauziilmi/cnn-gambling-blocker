from logging import DEBUG

from tqdm import tqdm

from logger_pkg.logger import get_logger

from .constant import GAMBLING_SITES, NON_GAMBLING_SITES
from .instance import Scraper

scraper = Scraper(log_level=DEBUG)

logger = get_logger(name="Scraper-Main-Script", level=DEBUG)

logger.info("Starting scraping non-gambling sites")
for site in tqdm(NON_GAMBLING_SITES, desc="Scraping non-gambling sites", unit="site"):
    scraper.scrape_into_dataset(extra_path="non_gambling", url=site)
logger.info("Finished scraping non-gambling sites")

logger.info("Starting scraping gambling sites")
for site in tqdm(GAMBLING_SITES, desc="Scraping gambling sites", unit="site"):
    scraper.scrape_into_dataset(extra_path="gambling", url=site)
logger.info("Finished scraping gambling sites")

scraper.close()
