
import time
import logging
import random
import requests
from base64 import b64decode
from bs4 import BeautifulSoup


SMARTPROXY_ZYTE_API_KEY = ""
ZYTE_API_KEY = "c9f7efe9060d453c9ea23ccc6d006698"
MAX_RETRY = 2



logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def proxy_api_response(url: str, is_httpresponse=True):
    """Fetch API response using proxies."""
    try:
        logger.info("Fetching URL: %s", url)
        if SMARTPROXY_ZYTE_API_KEY:
            api_response = requests.get(
                url,
                proxies={
                    "http": f"http://{SMARTPROXY_ZYTE_API_KEY}:@proxy.crawlera.com:8011/",
                    "https": f"http://{SMARTPROXY_ZYTE_API_KEY}:@proxy.crawlera.com:8011/",
                },
                timeout=60,
                verify='zyte-proxy-ca.crt'
            )
        elif ZYTE_API_KEY:
            api_response = requests.post(
                "https://api.zyte.com/v1/extract",
                auth=(ZYTE_API_KEY, ""),
                json={"url": url, "browserHtml": not is_httpresponse, "httpResponseBody": is_httpresponse},
                timeout=120
            )
        else:
            logger.error("No API key provided.")
            return None, None

        logger.info("Successfully fetched the URL: %s", url)
        return api_response.status_code, api_response

    except Exception as e:
        logger.error("Error fetching URL: %s. Exception: %s", url, str(e))

        return None, None


def retry_request(url: str, is_httpresponse= True, max_retry=5):
    """Retry logic for API requests with a specified max retry limit."""
    retries = 0
    while retries < max_retry:
        logger.info(f"Attempt {retries + 1} for URL: {url}")
        status_code, api_response = proxy_api_response(url, is_httpresponse)
        if status_code == 200:
            return status_code, api_response
        elif status_code in [429, 503, 520]:
            logger.warning(f"Rate-limiting or server issue: {status_code}")
            time.sleep(random.randint(60, 90))
            retries += 1
            if retries == max_retry and status_code == 520:
                logger.info(f"Retrying with browserHtml request after {max_retry} attempts")
                return retry_request(url, is_httpresponse= False)
        else:
            retries += 1
            if retries == max_retry:
                logger.error(f"Max retries reached for URL: {url}")
                break
    return None, None


def send_request_with_proxy(url: str, is_httpresponse=True, max_retry=5):
    """Fetch and process the API response with retries."""
    status_code, api_response = retry_request(url, is_httpresponse, max_retry)
    if status_code == 200:
        content_type = api_response.headers.get("Content-Type", "")
        html = ""

        if "application/json" in content_type:
            json_response = api_response.json()
            if json_response.get("httpResponseBody"):
                http_response_body = b64decode(json_response["httpResponseBody"]).decode('utf-8')
                html = http_response_body
            elif json_response.get("browserHtml"):
                html = json_response["browserHtml"]
        else:
            html = api_response.text

        soup = BeautifulSoup(html, features='html.parser')
        logger.info(f"Successfully processed URL: {url}")
        return [status_code, soup]

    logger.error(f"Failed to fetch URL: {url}")
    return ["error", ""]