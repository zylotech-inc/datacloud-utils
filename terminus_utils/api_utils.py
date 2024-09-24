from urllib.parse import urlencode, urlparse, urlunparse


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


def transform_employee_revenue_value(input_str):
    """
    Transforms a string into an absolute number.
    Handles cases with '<', '>', 'k', 'b', 't', 'M', and ranges like '100K-5.0M'.

    Args:
        input_str (str): The revenue string (e.g., "$5 M", "<5 million", ">5 million", "10k", "5b", "20-50t", "100K-5.0M").

    Returns:
        tuple: A tuple containing the absolute number and a boolean inferred flag.
    """
    try:
        if input_str:
            inferred_value = False
            input_str = input_str.lower().replace(',', '').strip()

            def convert_value(value_str):
                """Helper function to convert individual string values to absolute numbers."""
                if 'million' in value_str or 'm' in value_str:
                    return float(value_str.replace('million', '').replace('m', '')
                                 .replace('$', '').strip()) * 1_000_000
                elif 'billion' in value_str or 'b' in value_str:
                    return float(value_str.replace('billion', '').replace('b', '')
                                 .replace('$', '').strip()) * 1_000_000_000
                elif 'trillion' in value_str or 't' in value_str:
                    return float(
                        value_str.replace(
                            'trillion',
                            '').replace(
                            't',
                            '').replace(
                            '$',
                            '').strip()) * 1_000_000_000_000
                elif 'k' in value_str or 'thousand' in value_str:
                    return float(value_str.replace('k', '').replace('thousand', '').replace('$', '').strip()) * 1_000
                else:
                    return float(value_str.replace('$', '').strip())
            if '-' in input_str:
                lower, upper = input_str.replace('$', '').split('-')
                lower_value = convert_value(lower.strip())
                upper_value = convert_value(upper.strip())
                output_str = (lower_value + upper_value) / 2
                inferred_value = True
            elif '<' in input_str or '>' in input_str:
                value = convert_value(input_str.replace('<', '').replace('>', '').strip())
                if '<' in input_str:
                    value /= 2
                output_str = value
                inferred_value = True
            else:
                output_str = convert_value(input_str)
            return int(output_str), inferred_value
        return None, None
    except (ValueError, TypeError):
        return None, False
