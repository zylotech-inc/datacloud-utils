# terminus_utils

A common utility library for Python.

## Description

terminus_utils is a Python library that provides a collection of common utilities for various purposes. It is designed to be easy to use and to help developers save time and effort when working on their projects.

## Installation

To install terminus_utils, run the following command:
```bash
pip install git+https://github.com/zylotech-inc/datacloud-utils.git@dev
```

## Usage

Here's an example of how to use terminus_utils:

```python
from terminus_utils.logger import logger

logger.info("Hello World")

```
```python
from terminus_utils.api_utils import get_clean_website
website = get_clean_website("https://www.google.com")
print(website)
```

```python
from terminus_utils.api_utils import transform_employee_revenue_value

employee_revenue_value = transform_employee_revenue_value("10k")
print(employee_revenue_value) # (10000,'False)
```

```python
from terminus_utils.api_utils import revenue_range_taxonomy_mapper
revenue_range = revenue_range_taxonomy_mapper("$23M")
print(revenue_range) # "$10M-$50M"
```
## Description  
    This document outlines a method for handling API requests using proxies with a retry mechanism. The process is split into three parts, managing specific status codes and providing appropriate responses. Exception traceback handling has been improved, and the is_httpresponse flag is passed selectively based on the data source.

## Usage

Here's an example of how to use terminus_utils:

```python
from terminus_utils.utils import send_request_with_proxy

send_request_with_proxy("https://www.test.com")
```

## Method
    -proxy_api_response(url: str, is_httpresponse=True)
    -Fetches API response via proxy using SMARTPROXY_ZYTE_API_KEY or ZYTE_API_KEY.
        -Handles status codes:
        -200: Success.
        -429, 503, 520: Retries implemented.
    -Returns None if no API key is provided.
        -retry_request(url: str, is_httpresponse=True, max_retry=5)
        -Retries on 429, 503, 520 status codes.
    -After max retries, switches is_httpresponse=False for 520 errors.
        -send_request_with_proxy(url: str, is_httpresponse=True, max_retry=5)
        -Processes the API response based on the content type (JSON or HTML).
        -Returns the status code and a BeautifulSoup object.
    -Source-Specific Configuration
        -is_httpresponse=False: Only for Aeroleads.
        -is_httpresponse=True: Default for ZoomInfo, Datanyze, CBinsight, VisualVisitor, Rocketreach.
