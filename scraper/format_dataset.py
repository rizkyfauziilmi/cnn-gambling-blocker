import os
import re
from logging import INFO, Logger

from scraper.constant import KNOWN_SLDS
from utils.logger import get_logger


def format_filename(filename: str, logger: Logger, remove_subdomains: bool = True) -> str:
    """
    Format filename by removing parentheses and cleaning up the format.
    remove_subdomains: when False, keeps leading subdomains instead of trimming to the main domain.
    Examples:
    - "www.ovo.id_(desktop).png" -> "ovo.id_desktop.png"
    - "ovo.id_mobile.png" -> "ovo.id_mobile.png"
    - "www.tiket.com_en-id(mobile).png" -> "tiket.com_mobile.png"
    - "king.ayo788-pit.com_mobile.png" -> "ayo788_pit.com_mobile.png"
    complex example:
    # mail.ru__solution429=57w5tQLY0Fi1v-wBMb_D-BFSC4rXZUCx1J-EGYqqCMxZjh-awBb2pu33N5nNCb4T6gFbZ3yfUHBwWtowwF777uhYNXONPlBHGiAW_V3vPeQLHbsO_7C363KgITM0KtxblTrEqbvFTN6p6PFC&autologin=no(desktop).png
    # -> mail.ru_desktop.png
    """
    logger.debug(f"Processing: {filename}")
    # Split filename and extension
    name, ext = os.path.splitext(filename)

    # Extract device type (desktop or mobile)
    device_type = None

    # Check for device type in parentheses like (desktop) or (mobile)
    paren_match = re.search(r"\((\w+)\)", name)
    if paren_match:
        device_type = paren_match.group(1)
        logger.debug(f"Found device type in parentheses: {device_type}")
        # Remove the parentheses part
        name = re.sub(r"_?\([^)]+\)_?", "", name)

    # Check for device type as suffix like _desktop or _mobile
    if not device_type:
        if name.endswith("_desktop"):
            device_type = "desktop"
            logger.debug(f"Found device type as suffix: {device_type}")
            name = name[:-8]  # Remove _desktop
        elif name.endswith("_mobile"):
            device_type = "mobile"
            logger.debug(f"Found device type as suffix: {device_type}")
            name = name[:-7]  # Remove _mobile

    # Clean up the domain part
    # Remove query parameters and everything after double underscore
    if "__" in name:
        logger.debug("Removing query parameters")
        name = name.split("__")[0]

    # Remove language/locale codes like _en-id
    if re.search(r"_[a-z]{2}-[a-z]{2}", name):
        logger.debug("Removing language/locale codes")
        name = re.sub(r"_[a-z]{2}-[a-z]{2}", "", name)

    # Remove trailing underscores
    name = name.rstrip("_")

    # Remove www. prefix
    if name.startswith("www."):
        logger.debug("Removing www. prefix")
        name = name[4:]

    # Remove m. prefix
    if name.startswith("m."):
        logger.debug("Removing m. prefix")
        name = name[2:]

    # Trim anything after the first underscore (usually path or extra tokens)
    underscore_idx = name.find("_")
    if underscore_idx != -1:
        logger.debug(f"Trimming content after underscore: {name[underscore_idx:]}")
        name = name[:underscore_idx]

    # Extract just the domain part (remove trailing paths like _questions, _ext_en_home, etc.)
    # Keep only up to the TLD
    # First, identify potential domain part by finding dots
    last_dot_idx = name.rfind(".")
    if last_dot_idx != -1:
        # Get everything up to and including the last dot + TLD
        # TLD is typically 2-6 characters after the last dot, but may have underscores before it
        tld_part = name[last_dot_idx + 1 :]
        # Extract only the TLD (alphabetic part before any underscore)
        tld_match = re.match(r"([a-z]+)", tld_part)
        if tld_match:
            tld = tld_match.group(1)
            # Find the position of this TLD in the original name
            domain_end = last_dot_idx + 1 + len(tld)
            if domain_end < len(name):
                logger.debug(f"Removing trailing path: {name[domain_end:]}")
            name = name[:domain_end]

    # Remove any trailing suffix that duplicates TLD (e.g., prodia.co.id_id -> prodia.co.id)
    # Only check in the TLD part (last part after the last dot)
    last_dot_idx = name.rfind(".")
    if last_dot_idx != -1:
        tld_part = name[last_dot_idx + 1 :]
        if "_" in tld_part:
            # Split by underscore and check if suffix matches TLD
            tld_parts = tld_part.split("_")
            if len(tld_parts) >= 2 and tld_parts[0] == tld_parts[1]:
                logger.debug(f"Removing duplicate TLD suffix: {tld_part} -> {tld_parts[0]}")
                # Remove the duplicate suffix (e.g., "id_id" -> "id")
                name = name[: last_dot_idx + 1] + tld_parts[0]

    # Extract main domain by removing subdomains (optional)
    # Split by dots and keep the last three parts for multi-level TLDs (e.g., .or.id, .co.uk)
    # or last two parts for regular TLDs
    parts = name.split(".")
    if remove_subdomains:
        if len(parts) >= 3:
            # Check if it's a known multi-level TLD (e.g., .or.id, .co.id, .ac.id)
            second_level = parts[-2]
            if second_level in KNOWN_SLDS:
                # Keep last three parts (e.g., "nu.or.id")
                domain = ".".join(parts[-3:])
                logger.debug(f"Multi-level TLD detected (.{second_level}.{parts[-1]}): keeping {domain}")
            else:
                # Keep last two parts (e.g., "ayo788-pit.com")
                domain = ".".join(parts[-2:])
                logger.debug(f"Regular TLD: keeping {domain}")
        elif len(parts) >= 2:
            # Keep last two parts
            domain = ".".join(parts[-2:])
            logger.debug(f"Standard domain: {domain}")
        else:
            domain = name
    else:
        domain = name

    # Construct the new filename
    if device_type:
        new_filename = f"{domain}_{device_type}{ext}"
    else:
        new_filename = f"{domain}{ext}"

    logger.debug(f"Result: {filename} -> {new_filename}")
    return new_filename


def batch_rename_files(folder_path: str, logger: Logger, remove_subdomains: bool = True) -> None:
    """
    Rename all files in the given folder using the format_filename function.
    """
    if not os.path.isdir(folder_path):
        logger.error(f"{folder_path} is not a valid directory")
        raise NotADirectoryError(f"{folder_path} is not a valid directory")

    files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]

    if not files:
        logger.info(f"No files found in {folder_path}")
        raise FileNotFoundError(f"No files found in {folder_path}")

    logger.info(f"Found {len(files)} files to process in {folder_path}")

    renamed_count = 0
    no_change_count = 0

    for filename in files:
        new_filename = format_filename(filename, logger, remove_subdomains=remove_subdomains)

        if filename != new_filename:
            old_path = os.path.join(folder_path, filename)
            new_path = os.path.join(folder_path, new_filename)

            try:
                os.rename(old_path, new_path)
                logger.info(f"Renamed: {filename} -> {new_filename}")
                renamed_count += 1
            except Exception as e:
                logger.error(f"Error renaming {filename}: {e}")
        else:
            logger.info(f"No change needed for: {filename}")
            no_change_count += 1

    logger.info(f"Batch renaming completed in {folder_path}")
    logger.info(
        f"Summary [{folder_path}]: {renamed_count} files renamed, {no_change_count} files unchanged"  # noqa: E501
    )


if __name__ == "__main__":
    logger = get_logger("Format.Dataset", level=INFO)

    logger.info("Starting dataset filename formatting...")
    batch_rename_files("datasets/gambling", logger, remove_subdomains=False)
    batch_rename_files("datasets/non_gambling", logger, remove_subdomains=False)
    logger.info("Dataset filename formatting completed.")
