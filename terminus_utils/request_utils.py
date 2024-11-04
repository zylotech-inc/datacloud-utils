import requests
import time
import random
import logging
from bs4 import BeautifulSoup
from base64 import b64decode
from .environment_utils import get_zyte_secret

# Constants
MAX_RETRY = 5
ADDITIONAL_JS_RETRY = 3


# Logger setup
logger = logging.getLogger(__name__)

# Add more proxy configurations here as needed
PROXY_PROVIDERS = {
    'zyte': 'ZyteProxyHandler',
}

headers = {'X-Crawlera-Profile': 'desktop', 
'X-Crawlera-Cookies': 'discard', 
'cache-control': 'max-age=0', 
'sec-gpc': '1'}


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


def ZyteProxyHandler(url: str, render_js: bool = False):
    """
    Proxy handler for Zyte.
    
    Args:
        url (str): The URL to fetch.
        render_js (bool): Whether to enable JavaScript rendering. Default is False.
    
    Returns:
        tuple: (html, status_code, api_response)
    """
    
    auth = get_zyte_secret().get('ZYTE_API_KEY', 'None')
    if not auth:
        logger.error("No API key provided.")
        return None, None, None
    def attempt_request(url, render_js):
        try:
            data = {
                "url": url,
                "browserHtml": render_js,
                "httpResponseBody": not render_js,
                "javascript": render_js,
            }
            api_response = requests.post(
                'https://api.zyte.com/v1/extract', 
                json=data, 
                auth=(auth, ""), 
                headers=headers,
                timeout=60
            )
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
def send_request(url: str, proxy_vendor: str = 'zyte', request_type: str = 'http', render_js: bool = False):
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

    logger.error(f"Failed to fetch URL: {url} with status code: {status_code}")
    return [status_code, html, None]
