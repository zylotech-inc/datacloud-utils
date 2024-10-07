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

