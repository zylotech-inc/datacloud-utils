import os
import random
import time
from base64 import b64decode
from uuid import uuid4
import requests
from bs4 import BeautifulSoup

from terminus_utils.environment_utils import with_env_vars
from terminus_utils.logger import logger

# Constants
MAX_RETRY = 5
ADDITIONAL_JS_RETRY = 3
API_URL = 'https://api.zyte.com/v1/extract'
API_KEY = os.getenv("ZYTE_API_KEY")
# Global variable to store session ID
session_id = None

# Add more proxy configurations here as needed
PROXY_PROVIDERS = {
    'zyte': 'ZyteProxyHandler',
}

# headers = {'X-Crawlera-Profile': 'desktop',
#            'X-Crawlera-Cookies': 'discard',
#            'cache-control': 'max-age=0',
#            'sec-gpc': '1'}


def retry_request(attempt_request, url: str, render_js: bool = False, max_retry: int = MAX_RETRY):
    """Retry logic for API requests with a specified max retry limit."""
    retries = 0
    html = ""

    while retries < max_retry:
        logger.info(f"Attempt {retries + 1} for URL: {url}")
        html, status_code, api_response = attempt_request(url, render_js)

        if status_code == 200:
            return html, status_code, api_response

        elif status_code in [429, 503, 520]:
            logger.warning(f"Rate-limiting or server issue: {status_code}. Retrying after a delay.")
            time.sleep(random.randint(60, 90))

        elif status_code in [400, 401, 422]:
            logger.info(
                "[-] Invalid parameters or an issue with your API key.\n"
                "[-] Incompatible parameters or invalid JSON.\n"
            )
            return html, status_code, api_response

        elif status_code == 403:
            logger.info("[-] API account is suspended.")
            return html, status_code, api_response

        retries += 1
        # After max_retry attempts, retry with render_js=True for additional attempts
    if not render_js and retries >= max_retry:
        logger.info(f"Switching to render_js=True after {max_retry} attempts without success.")
        return retry_request(attempt_request, url, render_js=True, max_retry=ADDITIONAL_JS_RETRY)

    logger.error(f"Max retries reached for URL: {url} with render_js={render_js}")
    return html, status_code, api_response

def initial_request():
    """Sends the initial request to get a session ID."""
    global session_id
    session_id = str(uuid4())  # Generate a new session ID
    # print(f"Generated new session ID: {session_id}")

    _ = requests.post(API_URL, auth=(API_KEY, ""), json={
        "url": "https://www.zoominfo.com",
        "browserHtml": True,
        "session": {
            "id": session_id
        }
    }, timeout=60)
        
    return session_id
def ZyteProxyHandler(url: str, render_js: bool = False):
    """
    Proxy handler for Zyte.

    Args:
        url (str): The URL to fetch.
        render_js (bool): Whether to enable JavaScript rendering. Default is False.

    Returns:
        tuple: (html, status_code, api_response)
    """

    if not API_KEY:
        logger.error("No API key provided.")
        return None, None, None

    def attempt_request(url, render_js):
        try:
            if 'zoominfo.com' in url:
                zoom_session_id = initial_request()  # Ensure session ID is created only once
                # print(f"Generated new session ID: {session_id}")
                if not zoom_session_id:
                    logger.error("Unable to retrieve session ID.")
                    return "", None, None
                payload = {
                    "url": url,
                    "httpResponseBody": True,
                    "session": {
                        "id": zoom_session_id
                    }
                }
                api_response = requests.post(API_URL, auth=(API_KEY, ""), json=payload, timeout=60)
            else:
                payload = {
                    "url": url,
                    "browserHtml": render_js,
                    "httpResponseBody": not render_js,
                    "javascript": render_js,
                }
                api_response = requests.post(
                    API_URL,
                    json=payload,
                    auth=(API_KEY, ""),
                    timeout=120
                )
            print("PAYLOAD:",payload)
            status_code = api_response.status_code
            html = ""

            # Check if the response is JSON and extract HTML
            if status_code == 200:
                content_type = api_response.headers.get("Content-Type", "")
                if "application/json" in content_type:
                    json_response = api_response.json()
                    if json_response.get("httpResponseBody"):
                        http_response_body = b64decode(json_response["httpResponseBody"]).decode('utf-8')
                        html = http_response_body
                    elif json_response.get("browserHtml"):
                        html = json_response["browserHtml"]
                else:
                    html = api_response.text
            return html, status_code, api_response
        except Exception as e:
            logger.error(f"Error in ZyteProxyHandler attempt: {e}", exc_info=True)
            return "", None, None
    # First request attempt
    html, status_code, api_response = attempt_request(url, render_js)

    # If the first attempt fails, invoke retry_request
    if status_code != 200:
        html, status_code, api_response = retry_request(attempt_request, url, render_js, MAX_RETRY)

    return html, status_code, api_response

# Centralized Request Handler
@with_env_vars
def send_request(url: str, proxy_vendor: str = 'zyte', 
                 request_type: str = 'http', render_js: bool = False):
    """
    Centralized Request Handler to streamline web requests for different scrapers.

    Args:
        url (str): The URL to fetch.
        proxy_vendor (str): Proxy vendor (e.g., 'zyte', 'future_proxy'). Default is 'zyte'.
        request_type (str): Type of request ('http', 'render_js'). Default is 'http'.
        render_js (bool): Whether to render JavaScript. Default is False.

    Returns:
        tuple: (status_code, html, soup)
    """
    if proxy_vendor not in PROXY_PROVIDERS:
        raise ValueError(f"Proxy vendor '{proxy_vendor}' is not supported.")

    # Dynamically resolve the proxy handler
    proxy_handler = globals()[PROXY_PROVIDERS[proxy_vendor]]

    # Call ZyteProxyHandler, which includes retry handling
    html, status_code, api_response = proxy_handler(url, render_js)

    if status_code == 200:
        soup = BeautifulSoup(html, features='html.parser')
        logger.info(f"Successfully processed URL: {url}")
        return [html, status_code, soup]
    else:
        logger.error(f"Failed to fetch URL: {url} with status code: {status_code}")
        return [html, status_code, None]