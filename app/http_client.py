import requests

def fetch_url(url: str) -> str:
    """
    Fetch the given URL and return its text content.
    Raises:
      requests.RequestException   if the request fails (network error, invalid URL).
      ValueError                  if the response status is not 200.
    """
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()   # HTTP errors -> RequestException
    except requests.RequestException as e:
        # Re-raise with a clearer message
        raise ValueError(f"Failed to fetch {url!r}: {e}") from e

    return response.text
