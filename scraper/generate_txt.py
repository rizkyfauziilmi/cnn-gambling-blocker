from utils.logger import get_logger

from .constant import GAMBLING_SITES, NON_GAMBLING_SITES

logger = get_logger("Create.TXT.Files", level="INFO")


logger.info("Creating TXT files for gambling and non-gambling sites...")
# Create gambling_sites.txt
with open("gambling_sites.txt", "w") as f:
    for site in GAMBLING_SITES:
        f.write(f"{site}\n")

# Create non_gambling_sites.txt
with open("non_gambling_sites.txt", "w") as f:
    for site in NON_GAMBLING_SITES:
        f.write(f"{site}\n")

logger.info("TXT files created successfully!")
logger.info(f"Total gambling sites: {len(GAMBLING_SITES)}")
logger.info(f"Total non-gambling sites: {len(NON_GAMBLING_SITES)}")
