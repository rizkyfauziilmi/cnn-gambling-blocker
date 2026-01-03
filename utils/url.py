def get_domain(url: str) -> tuple[str, str]:
    """
    Extract the domain from a given URL.

    Args:
        url (str): The URL to extract the domain from.

    Returns:
        str: The extracted domain.
    """
    from urllib.parse import urlparse

    parsed_url = urlparse(url)

    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
    return base_url, parsed_url.netloc


def is_accessible_html(url: str) -> bool:
    """
    Check if a URL is accessible and returns HTML content.
    Args:
        url (str): The URL to check.
        timeout (int): The timeout for the request in seconds.
    Returns:
        bool: True if the URL is accessible and returns HTML content, False otherwise.
    """
    import requests

    try:
        response = requests.get(url=url)
        response.raise_for_status()

        content_type = response.headers.get("Content-Type", "").lower()

        return "text/html" in content_type

    except requests.RequestException:
        return False
