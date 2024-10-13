import re
from urllib.parse import urlencode, urlparse, urlunparse

from currency_converter import CurrencyConverter
from forex_python.converter import CurrencyRates

currency_rates = CurrencyRates()
currency_converter = CurrencyConverter()


def get_clean_website(text: str) -> str:
    """
    Remove common prefixes from a website URL.

    Args:
        text (str): The raw website URL.

    Returns:
        str: The cleaned website URL without "www.", "https://", or "http://".

    Raises:
        ValueError: If the input is not a string.
    """
    clean_website = text.replace("www.",
                                 "").replace("https://", "").replace("http://", "").strip()
    if not isinstance(text, str):
        raise ValueError("Input must be a string")
    return clean_website


def prepare_search_url(text: str, source: str):
    """
    Get the search url add with domain

    Args:
        text (domain) (str): pass the domain

    Returns:
       final url (str): get the search url
    """
    base_url = "https://www.google.com/search"
    domain = get_clean_website(text)
    if source in ['owler.com', 'aeroleads.com', 'visualvisitor.com']:
        query_params = {"q": f'{source} + "{domain}"'}
    elif source in ['cbinsights.com']:
        query_params = {"q": f'site:{source} AND "{domain}"'}
    elif source in ['rocketreach.co']:
        query_params = {"q": f'site: {source} + "{domain}" " + revenue"'}
    else:
        query_params = {"q": f' "{domain}" {source}'}
    encoded_query = urlencode(query_params)
    parsed_url = urlparse(base_url)
    updated_url = parsed_url._replace(query=encoded_query)
    final_url = urlunparse(updated_url)
    return final_url


def transform_employee_revenue_value(input_str: str):
    """
    Transforms a string into an absolute number.
    Handles cases with '<', '>', 'k', 'b', 't', 'M', 'Thousand', and ranges
    like '100K-5.0M' or '$5-10M'.

    Args:
        input_str (str): The revenue string (e.g., "$5M", "<5 million", ">5 million",
        "10k", "5b", "20-50t", "100K-5.0M", "$5-10M", "500 Thousand").

    Returns:
        tuple: A tuple containing the absolute number and a boolean inferred flag.
    """
    try:
        if input_str:
            inferred_value = False
            input_str = input_str.lower().replace(',', '').strip()

            def convert_value(value_str):
                """Helper function to convert individual string values to absolute numbers."""
                if 'k' in value_str or 'thousand' in value_str:
                    return float(value_str.replace('k', '').replace('thousand', '')
                                 .replace('$', '').strip()) * 1_000
                elif 'm' in value_str or 'million' in value_str:
                    return float(value_str.replace('million', '').replace('m', '')
                                 .replace('$', '').strip()) * 1_000_000
                elif 'b' in value_str or 'billion' in value_str:
                    return float(value_str.replace('billion', '').replace('b', '')
                                 .replace('$', '').strip()) * 1_000_000_000
                elif 't' in value_str or 'trillion' in value_str:
                    return float(value_str.replace('trillion', '').replace('t', '')
                                 .replace('$', '').strip()) * 1_000_000_000_000
                else:
                    return float(value_str.replace('$', '').strip())

            def split_value_parts(input_value):
                """Helper function to split individual string values."""
                pattern = r"\$?(\d+(\.\d+)?)([kKmMbBtT]?)\s*-\s*\$?(\d+(\.\d+)?)([kKmMbBtT]?)"
                match = re.match(pattern, input_value)
                if match:
                    a = match.group(1)
                    suffix_a = match.group(3)
                    b = match.group(4)
                    suffix_b = match.group(6)
                    return a, b, suffix_a, suffix_b
                return None, None, None, None
            
            if '-' in input_str:
                lower, upper, suffix_a, suffix_b = split_value_parts(input_str)
                if lower is None or upper is None:
                    return None, False
                if not suffix_a and suffix_b:
                    suffix_a = suffix_b
                if not suffix_b and suffix_a:
                    suffix_b = suffix_a
                if suffix_b == 'k' and 100 <= float(lower) <= 900:
                    lower_value = convert_value(lower)
                else:
                    lower_value = convert_value(lower + suffix_a)
                upper_value = convert_value(upper + suffix_b)
                output_value = (lower_value + upper_value) / 2
                inferred_value = True
            elif '<' in input_str:
                value = convert_value(input_str.replace('<', '').strip())
                output_value = value * 0.5
                inferred_value = True
            elif '>' in input_str:
                value = convert_value(input_str.replace('>', '').strip())
                inferred_value = True
                output_value = value * 1.5 #need to discuss
            else:
                output_value = convert_value(input_str)
            return int(round(output_value)), inferred_value
        return None, None
    except (ValueError, TypeError):
        return None, False


def convert_inr_to_usd(value: str):
    try:
        return float(round(currency_converter.convert(value, 'INR', 'USD'), 2))  # using currency_converter
    except Exception:
        return float(round(currency_rates.convert('INR', 'USD', value), 2))  # using forex_python currency_converter


def revenue_range_taxonomy_mapper(revenue: str) -> str:
    """
    Converts a revenue string to a standardized taxonomy label based on the revenue range.

    Args:
        revenue (str): The revenue value as a string, which may include a currency symbol,
        numeric value, and suffix (e.g. "1.2M", "$500k", "100 million").

    Returns:
        str: The taxonomy label for the revenue range (e.g. "$0-$1M", "$1M-$10M", ">$1B").
    """
    try:
        revenue = revenue.lower()
        number = revenue.replace("$", "").replace(" ", "")
        number = re.sub(r"[^0-9.-]", "", number).strip(".").strip()
        if float(number) < 0:
            return ''
        suffix_multipliers = {
            'k': 1_000,
            'thousand': 1_000,
            'm': 1_000_000,
            'million': 1_000_000,
            'b': 1_000_000_000,
            'billion': 1_000_000_000,
            't': 1_000_000_000_000,
            'trillion': 1_000_000_000_000,
            'cr': 10_000_000
        }
        if number:
            if "million" in revenue or "m" in revenue:
                number = float(number) * suffix_multipliers['m']
            elif "billion" in revenue or "b" in revenue:
                number = float(number) * suffix_multipliers['b']
            elif "trillion" in revenue or "t" in revenue:
                number = float(number) * suffix_multipliers['t']
            elif "k" in revenue:
                number = float(number) * suffix_multipliers['k']
            elif "cr" in revenue:
                number = convert_inr_to_usd(float(number) * suffix_multipliers['cr'])
            else:
                number = float(number)
        # Define revenue ranges and their corresponding taxonomy labels
        revenue_ranges = [
            (0, 999_999, '$0-$1M'),
            (1_000_000, 9_999_999, '$1M-$10M'),
            (10_000_000, 49_999_999, '$10M-$50M'),
            (50_000_000, 99_999_999, '$50M-$100M'),
            (100_000_000, 199_999_999, '$100M-$200M'),
            (200_000_000, 999_999_999, '$200M-$1B'),
            (1_000_000_000, float('inf'), '>$1B')
        ]
        # Find the appropriate range for emp_size
        for lower, upper, label in revenue_ranges:
            if lower <= number <= upper:
                return label
    except (ValueError, TypeError):
        # logger.exception(f"{revenue} is not a valid revenue.")
        return ''
