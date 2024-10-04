import re
from urllib.parse import urlencode, urlparse, urlunparse
from .logger import logger


def get_clean_website(text: str) -> str:
    """
    Get the Clean Website remove "www." or "https://" or "http://

    Args:
        raw website (str): pass the raw website

    Returns:
       clean website (str): get the clean website
    """
    clean_website = str(text).replace("www.", "").strip(
    ).replace("https://", "").strip().replace("http://", "").strip()
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

            def convert_value(value_str, suffix):
                """Helper function to convert individual string values to absolute numbers."""
                if 'k' in suffix or 'thousand' in value_str:
                    return float(value_str.replace('k', '').replace('thousand', '')
                                 .replace('$', '').strip()) * 1_000
                elif 'm' in suffix or 'million' in value_str:
                    return float(value_str.replace('million', '').replace('m', '')
                                 .replace('$', '').strip()) * 1_000_000
                elif 'b' in suffix or 'billion' in value_str:
                    return float(value_str.replace('billion', '').replace('b', '')
                                 .replace('$', '').strip()) * 1_000_000_000
                elif 't' in suffix or 'trillion' in value_str:
                    return float(value_str.replace('trillion', '').replace('t', '')
                                 .replace('$', '').strip()) * 1_000_000_000_000
                else:
                    return float(value_str.replace('$', '').strip())

            def split_value_parts(input_value):
                """Helper function to split individual string values."""
                match = re.match(r"\$?(\d+(\.\d+)?)([kKmMbBtT]?)\s*-\s*\$?(\d+(\.\d+)?)([kKmMbBtT]?)", input_value)
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
                if suffix_a and suffix_b:
                    lower_value = convert_value(lower + suffix_a, suffix_a)
                    upper_value = convert_value(upper + suffix_b, suffix_b)
                else:
                    common_suffix = suffix_a if suffix_a else suffix_b
                    lower_value = convert_value(lower + (suffix_a if suffix_a else ''), common_suffix)
                    upper_value = convert_value(upper + (suffix_b if suffix_b else ''), common_suffix)
                output_value = (lower_value + upper_value) / 2
                inferred_value = True
            elif '<' in input_str:
                value = convert_value(input_str.replace('<', '').replace('>', '').strip(), input_str)

                output_value = value*0.5
                inferred_value = True
            elif '>' in input_str:
                value = convert_value(input_str.replace('<', '').replace('>', '').strip(), input_str)
                inferred_value = True
                output_value = value + value*0.5  # => (value + (value*2))/2
                return output_value, inferred_value

            else:
                output_value = convert_value(input_str, input_str)
            return int(round(output_value)), inferred_value
        return None, None
    except (ValueError, TypeError):
        logger.exception(f"{input_str} is not a valid value.")
        return None, False


# def transform_employee_revenue_value(input_str):
#     """
#     Transforms a string into an absolute number.
#     Handles cases with '<', '>', 'k', 'b', 't', 'M', 'Thousand', and ranges
#     like '100K-5.0M' or '$5-10M'.

#     Args:
#         input_str (str): The revenue string (e.g., "$5M", "<5 million", ">5 million",
#         "10k", "5b", "20-50t", "100K-5.0M", "$5-10M", "500 Thousand").

#     Returns:
#         tuple: A tuple containing the absolute number and a boolean inferred flag.
#     """
#     try:
#         if input_str:
#             inferred_value = False
#             input_str = input_str.lower().replace(',', '').strip()

#             def convert_value(value_str, suffix):
#                 """Helper function to convert individual string values to absolute numbers."""
#                 if 'k' in suffix or 'thousand' in value_str:
#                     return float(value_str.replace('k', '').replace('thousand', '')
#                                  .replace('$', '').strip()) * 1_000
#                 elif 'm' in suffix or 'million' in value_str:
#                     return float(value_str.replace('million', '').replace('m', '')
#                                  .replace('$', '').strip()) * 1_000_000
#                 elif 'b' in suffix or 'billion' in value_str:
#                     return float(value_str.replace('billion', '').replace('b', '')
#                                  .replace('$', '').strip()) * 1_000_000_000
#                 elif 't' in suffix or 'trillion' in value_str:
#                     return float(value_str.replace('trillion', '').replace('t', '')
#                                  .replace('$', '').strip()) * 1_000_000_000_000
#                 else:
#                     return float(value_str.replace('$', '').strip())

#             def split_value_parts(input_value):
#                 """Helper function to split individual string values."""
#                 pattern = r"\$?(\d+(\.\d+)?)([kKmMbBtT]?)\s*-\s*\$?(\d+(\.\d+)?)([kKmMbBtT]?)"
#                 match = re.match(pattern, input_value)
#                 if match:
#                     a = match.group(1)
#                     suffix_a = match.group(3)
#                     b = match.group(4)
#                     suffix_b = match.group(6)
#                     return a, b, suffix_a, suffix_b
#                 return None, None, None, None

#             if '-' in input_str:
#                 lower, upper, suffix_a, suffix_b = split_value_parts(input_str)
#                 if lower is None or upper is None:
#                     return None, False
#                 if suffix_a and suffix_b:
#                     lower_value = convert_value(lower + suffix_a, suffix_a)
#                     upper_value = convert_value(upper + suffix_b, suffix_b)
#                 else:
#                     common_suffix = suffix_a if suffix_a else suffix_b
#                     lower_value = convert_value(lower + (suffix_a if suffix_a else ''), common_suffix)
#                     upper_value = convert_value(upper + (suffix_b if suffix_b else ''), common_suffix)
#                 output_value = (lower_value + upper_value) / 2
#                 inferred_value = True
#             elif '<' in input_str or '>' in input_str:
#                 value = convert_value(input_str.replace('<', '').replace('>', '').strip(), input_str)
#                 if '<' in input_str:
#                     value /= 2
#                 output_value = value
#                 inferred_value = True
#             else:
#                 output_value = convert_value(input_str, input_str)
#             return int(round(output_value)), inferred_value
#         return None, None
#     except (ValueError, TypeError):
#         return None, False
