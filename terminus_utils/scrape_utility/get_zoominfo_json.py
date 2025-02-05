from terminus_utils.api_utils import transform_employee_revenue_value
from terminus_utils.request_utils import send_request


def extract_codes(soup: BeautifulSoup):
    """
    Extracts SIC and NAICS codes from the provided BeautifulSoup object.

    Args:
        soup (BeautifulSoup): A BeautifulSoup object containing the HTML of the page to be parsed.

    Returns:
        tuple: A tuple containing the SIC code and the NAICS code as strings. 
               Returns empty strings for both codes if they cannot be found.

    Note:
        If an AttributeError occurs during parsing, it logs the error and returns
          empty strings for both codes.
    """
    sic_code = None
    naics_code = None
    try:
        codes_data = {
            code.split(' ')[0]: code.split(' ')[-1]
            for code in (element.get_text(strip=True) for element in soup_find_all(
                soup, class_='codes-content'))}
        sic_code = codes_data.get('SIC')
        naics_code = codes_data.get('NAICS')
        if not sic_code or not naics_code:
            sic_code_element = soup_find(soup, id='SIC')
            naics_code_element = soup_find(soup, id='NAICS')
            if sic_code_element:
                sic_code = sic_code_element.get_text(strip=True)
            if naics_code_element:
                naics_code = naics_code_element.get_text(strip=True)
        return sic_code, naics_code
    except AttributeError as e:
        log_exception("Exception Occurred: ", e, '')
        return sic_code, naics_code


def clean_address(address):
    """
    Cleans an address string by removing leading special characters such as '-', '/', '_', and '&'.

    Args:
        address (str): The address string to be cleaned.

    Returns:
        str: The cleaned address string.
    """
    characters_to_replace = ['-', '/', '_', '&', '@']
    for char in characters_to_replace:
        if address.startswith(char):
            address = address.replace(char, '')
    return address

def get_topic_intent_score(soup):
    """
    Extracts topic intent scores from the provided BeautifulSoup object.

    Args:
        soup (BeautifulSoup): A BeautifulSoup object containing the HTML of the page to be parsed.

    Returns:
        dict: A dictionary where the keys are strings in the format 'topic_X'
        (with X being an integer starting from 1)
              and the values are dictionaries with the keys 'topic_name' and 'topic_score'.

    Note:
        If an AttributeError occurs during parsing, it logs the error and
        returns an empty dictionary.
    """
    intent_rows = soup_find_all(soup, class_="intent-row")[1:]
    topic_dict = {}
    try:
        for i, row in enumerate(intent_rows, start=1):
            topic_data = {}
            topic_elm = soup_find(row, class_="topic-name")
            topic = topic_elm.text if topic_elm else None
            score_elm = soup_find(row, class_="signal-score")
            score = score_elm.text if topic_elm else None
            topic_data["topic_name"] = topic
            topic_data["topic_score"] = score
            topic_dict[f"topic_{i}"] = topic_data
        return topic_dict
    except AttributeError as e:
        log_exception("Exception Occurred: ", e, '')
        return topic_dict

def get_competitor_emp_revenue(soup):
    """
    Extracts the names, employee counts, and revenue information of competitors from the 
    provided BeautifulSoup object.

    Args:
        soup (BeautifulSoup): A BeautifulSoup object containing the HTML of the page to be parsed.

    Returns:
        dict: A dictionary where the keys are strings in the format 'competitor_X' (with X 
        being an integer starting from 1)
              and the values are dictionaries with the keys 'name', 'employee', and 'revenue'.

    Note:
        If an AttributeError occurs during parsing, it logs the error and returns 
        an empty dictionary.
    """
    top_competitor_list = []
    try:
        competitor_card_elm = soup.find(class_="clear-list competitors-content-wrapper")
        if competitor_card_elm:
            competitor_cards = competitor_card_elm.find_all("li")

            for _, card in enumerate(competitor_cards, start=1):
                comp_card = {}
                name_element = card.find(class_="company-name link")
                name = name_element.text if name_element else None
                bottom_wrapper = card.find(class_="bottom-wrapper")
                comp_list = bottom_wrapper.find_all(class_="icon-text-content") if bottom_wrapper else []
                if len(comp_list) >= 2:
                    competitor_emp = comp_list[0].text.strip()
                    competitor_revenue = comp_list[1].text.strip()
                else:
                    competitor_emp = None
                    competitor_revenue = None
                comp_card["name"] = name
                employee_size, inferred_employee = transform_employee_revenue_value(competitor_emp)
                comp_card["employees"] = employee_size
                comp_card["inferred_employees"] = inferred_employee
                revenue, inferred_revenue = transform_employee_revenue_value(competitor_revenue)
                comp_card["revenue"] = revenue
                comp_card["inferred_revenue"] = inferred_revenue
                top_competitor_list.append(comp_card)
        return top_competitor_list
    except AttributeError as e:
        log_exception("Exception Occurred: ", e, '')
        return top_competitor_list


def scrape_company_info(soup: BeautifulSoup):
    """
    Scrapes detailed company information from the provided BeautifulSoup object.

    Args:
        soup (BeautifulSoup): A BeautifulSoup object containing the HTML of the page to be parsed.

    Returns:
        tuple: A tuple containing:
            - dict: A dictionary with the scraped company details.
            - str or None: An error message if an exception occurs, otherwise None.
    """
    result = {}
    if not soup:
        return result, "No soup object provided"
    
    try:
        company_name_elm = soup_find(soup, class_="company-name")
        company_name = company_name_elm.text if company_name_elm else None

        company_desc_el = soup_find(soup, id="company-description-text-content")
        company_desc = company_desc_el.text if company_desc_el else ""

        company_prod = [tech_owned.text for tech_owned in soup_find_all(soup, class_="tech-owned")]

        acquisition_elements = soup.find_all(class_="name-acquisition-card")
        acquisition_subs = [acq_sub.text for acq_sub in acquisition_elements] if acquisition_elements else []

        company_business_industry = ",".join([i.text.strip() for i in soup.find_all('zi-directories-chips') if i])
        industry, terminus_industry_label, industry_status_tag = map_raw_industry_with_croswalk_industry(company_business_industry)

        company_employee_business_soup = soup_find(soup, class_='company-header-subtitle')
        raw_employee_size = company_employee_business_soup.text.split('·')[-1][1:-1].replace(' Employees', '').replace(' Employee', '') if company_employee_business_soup else None
        company_employee_size, inferred_employee_size = transform_employee_revenue_value(raw_employee_size)

        address_phone_ticker_list = soup_find_all(soup, class_='icon-text-container')
        company_address = ' '.join([each.text for each in address_phone_ticker_list if "Headquarters" in each.text]).replace('Headquarters', '').strip()
        company_phone = ' '.join([each.text for each in address_phone_ticker_list if "Phone Number" in each.text]).replace('Phone Number', '').strip()
        ticker = ' '.join([each.text for each in address_phone_ticker_list if "Stock Symbol" in each.text]).replace('Stock Symbol', '').strip() if address_phone_ticker_list else None

        if "..." in company_address:
            address_elm = soup.find(class_="answer is-open")
            company_address = address_elm.text.strip().split('located at')[-1] if address_elm else ""

        company_address = clean_address(company_address)

        funding = None
        funding_total = soup_find(soup, class_="funding-total")
        if funding_total:
            total_item_content = funding_total.find(class_="total-item-content")
            funding = total_item_content.text if total_item_content else None
        if not funding:
            funding_element = soup.find('span', string="Amount")
            funding = funding_element.find_next("span").text if funding_element else None

        tech_stack = [tech.find(class_="name-text link").text for tech in soup_find_all(soup, class_="tech-name-wrapper") if tech]

        website_revenue_list = soup_find_all(soup, class_='icon-text-container')
        company_website = ' '.join([each.text for each in website_revenue_list if "Website" in each.text]).replace('Website', '').strip()
        raw_company_revenue = ' '.join([each.text for each in website_revenue_list if "Revenue" in each.text]).replace('Revenue', '').strip()
        company_revenue, inferred_company_revenue = transform_employee_revenue_value(raw_company_revenue)

        company_sic, company_naics = extract_codes(soup)
        company_sic = return_longest_code(company_sic)
        company_naics = return_longest_code(company_naics)

        social_links = soup_find_all(soup, class_="social-media-icon")
        linkedin_link = get_valid_url(social_links, "linkedin.com")
        facebook_link = get_valid_url(social_links, "facebook.com")
        twitter_link = get_valid_url(social_links, "twitter.com")

        topic_data = get_topic_intent_score(soup)
        topic_score = topic_data.get('topic_score', {})

        competitors = get_competitor_emp_revenue(soup)

        contact_list = soup_find_all(soup, class_="person-card-container person-card-banner")
        contacts = [{'name': contact.find('a', class_="link person-name").text.strip() if contact.find('a', class_="link person-name") else None, 
                     'title': contact.find('p', class_="job-title").text.strip() if contact.find('p', class_="job-title") else None} for contact in contact_list]

        result = {
            'name': company_name,
            'industry': industry,
            'terminus_industry_label': terminus_industry_label,
            'industry_status': industry_status_tag,
            'employee_size': company_employee_size,
            'inferred_employee_size': inferred_employee_size,
            'address': company_address,
            'phone': company_phone,
            'website': company_website,
            'revenue': company_revenue,
            'inferred_company_revenue': inferred_company_revenue,
            'sic': company_sic,
            'naics': company_naics,
            'description': company_desc,
            'funding': funding,
            'links': {
                'linkedin_url': linkedin_link,
                'facebook_url': facebook_link,
                'twitter_url': twitter_link,
                'crunchbase_url': None
            },
            'ticker': ticker,
            'topic_score': topic_score,
            'tech_stack': tech_stack,
            'products': company_prod,
            'competitor': competitors,
            'acquisition': acquisition_subs,
            'contacts': contacts
        }
        return result, None  # No error

    except Exception as e:
        logger.error("Unexpected exception occurred:", exc_info=True)
        return {}, str(e)  # Return empty dict and error message

zoominfo_data,error_text = scrape_company_info(soup)
print(zoominfo_data,error_text)