import re
import sys
from bs4 import BeautifulSoup
from terminus_utils.logger import logger
from terminus_utils.scraper_parser.scraper_utils import (
    get_valid_url, log_exception, map_raw_industry_with_croswalk_industry,
    return_longest_code, soup_find, soup_find_all, upload_html_to_s3, ZYTE_API_KEY)
from terminus_utils.api_utils import transform_employee_revenue_value

BLANK_HTML = "<span></span>"
error_list = []  # TODO: need to ask


def contact_info_parser_executive_team(soup):
    """
    Parses contact information of the executive team from the provided BeautifulSoup object.

    Args:
        soup (BeautifulSoup): A BeautifulSoup object containing the HTML of the page to be parsed.

    Returns:
        tuple: A tuple containing:
            - all_contacts (dict): A dictionary with contact details where each key is 'contact' 
              followed by a number, and the value is another dictionary containing 'name', 'title',
              and 'profile_url' of the person.
            - iter (int): The number of contacts parsed.
    """
    all_contacts = {}
    iter = 1
    find_person = soup_find(soup, class_="pic-table")
    if find_person:
        person_list = soup_find_all(find_person, class_="person-row")
        for each in person_list:
            contact = {}
            name_elm = soup_find(each, class_="person-name")
            title_elm = soup_find(each, class_="job-title")
            profile_url_tag = soup_find(each, class_="social-links-container").find("a")
            contact["name"] = name_elm.text if name_elm else None
            contact["title"] = title_elm.text if title_elm else None
            contact["profile_url"] = profile_url_tag['href'] if profile_url_tag else None
            all_contacts["contact" + str(iter)] = contact
            iter += 1
    return all_contacts, iter


def contact_info_parser_recently_updated(soup, iter):
    """
    Parses contact information of recently updated team members from the provided 
        BeautifulSoup object.

    Args:
        soup (BeautifulSoup): A BeautifulSoup object containing the HTML of the page to be parsed.
        iter (int): An integer representing the starting count for contacts.

    Returns:
        dict: A dictionary with contact details where each key is 'contact' followed by a number, 
            and the value is another dictionary containing 'name', 'title', and 'profile_url'
            of the person.
    """
    all_contacts = {}
    person_list = soup_find_all(soup, class_="pic-table")
    if len(person_list) > 1:
        person_list = soup_find_all(person_list[1], class_="person-row")
    else:
        person_list = []
    for each in person_list:
        contact = {}
        name_elm = soup_find(each, class_="person-name")
        title_elm = soup_find(each, class_="job-title")
        profile_url_tag = soup_find(
            each, class_="social-links-container").find("a") if soup_find(each, class_="social-links-container") else None
        contact["name"] = name_elm.text if name_elm else None
        contact["title"] = title_elm.text if title_elm else None
        contact["profile_url"] = profile_url_tag['href'] if profile_url_tag else None
        all_contacts["contact" + str(iter)] = contact
        iter += 1
    return all_contacts


def parse_contact_information(soup):
    """
    Combines executive and recently updated contact information from the given BeautifulSoup object.

    Args:
        soup (BeautifulSoup): A BeautifulSoup object containing the HTML of the page to be parsed.

    Returns:
        Optional[Dict[str, Dict[str, str]]]: A dictionary of contact details, or None if no contacts are found.
    """
    contacts = []
    contacts_executives, iter = contact_info_parser_executive_team(soup)
    contacts_recent = contact_info_parser_recently_updated(soup, iter)
    contacts_dict = {**contacts_executives, **contacts_recent}
    for key, contact_info in contacts_dict.items():
        contact = {
            'name': contact_info.get('name'),
            'title': contact_info.get('title'),
            'profile_url': contact_info.get('profile_url')
        }
        contacts.append(contact)
    if not contacts:
        return contacts
    return contacts


def get_competitors(soup):
    """
    Parses competitor information from the provided BeautifulSoup object.

    Args:
        soup (BeautifulSoup): A BeautifulSoup object containing the HTML of the page to be parsed.

    Returns:
        dict: A dictionary containing competitor details. Each key is 'competitor_' 
        followed by a number, and the value is another dictionary containing 'competitor_name',
        'competitor_employee', 'competitor_revenue', and 'competitor_products'.

    Note:
        If an AttributeError occurs during parsing, it logs the error and returns
        the dictionary with parsed data up to that point.
    """
    competitor_list = []
    try:
        competitors = soup.find_all(class_="competitor-row")
        if competitors:
            for i, row in enumerate(competitors, start=1):
                temp_dict = dict()
                competitor_name = row.find("p").text if row.find("p") else None
                competitor_employee_elm = soup_find(soup, class_="competitor-cell employees-\
                                                size")
                competitor_employee = competitor_employee_elm.text if competitor_employee_elm else None
                competitor_revenue_elm = soup_find(soup, class_="competitor-cell competitor-\
                                               revenue")
                competitor_revenue = competitor_revenue_elm.text if competitor_revenue_elm else None
                competitor_products = ",".join([comp_prod.text.strip() for comp_prod in soup_find(
                    soup, class_="competitor-cell competitor-products").find_all("a")])
                temp_dict["competitor_name"] = competitor_name
                competitor_employee_size, inferred_competitor_employee = transform_employee_revenue_value(
                    competitor_employee)
                temp_dict["competitor_employee"] = competitor_employee_size
                temp_dict["competitor_inferred_employee"] = inferred_competitor_employee
                competitor_revenuee, competitor_inferred_revenue = transform_employee_revenue_value(competitor_revenue)
                temp_dict["competitor_revenue"] = competitor_revenuee
                temp_dict["competitor_inferred_revenue"] = competitor_inferred_revenue
                temp_dict["competitor_products"] = competitor_products if competitor_products else None
                competitor_list.append(temp_dict)
        return competitor_list
    except AttributeError as e:
        log_exception("Error while parsing competitor information", e, "class='competitor-row'")
        return competitor_list

def account_info_parser(soup):
    """
    Parses account information from the provided BeautifulSoup object.

    Args:
        soup (BeautifulSoup): A BeautifulSoup object containing the HTML of the page to be parsed.

    Returns:
        dict: A dictionary containing parsed account information with the following keys:
            - company (str): The name of the company.
            - website (str): The company's website URL.
            - hq_address (str): The headquarters address of the company.
            - hq_phone (str): The headquarters phone number of the company.
            - industry (str): The industry of the company.
            - terminus_industry_label (str): The mapped industry label.
            - industry_status (str): The status of the industry mapping.
            - ticker (str): The stock ticker symbol of the company.
            - funding (str): The funding information of the company.
            - linkedin_link (str): The LinkedIn profile link of the company.
            - facebook_link (str): The Facebook profile link of the company.
            - twitter_link (str): The Twitter profile link of the company.
            - technology (str): The technology products associated with the company.
            - products (str): The products offered by the company.
            - largest_customer (str): The largest customers of the company.
            - competitors (dict): A dictionary of competitors with their details.
            - revenue (str): The revenue of the company.
            - employees (str): The number of employees in the company.
            - founded (str): The year the company was founded.
            - description (str): The description of the company.
            - contacts (dict): A dictionary of contacts with their details.

    Note:
        If an exception occurs during parsing, it logs the error and returns an empty dictionary.
    """
    result = {}
    if not soup:
        return result
    try:
        website_company_tag = soup.find(class_="company-details-container")
        company = website_company_tag.find(class_="name") if website_company_tag else BeautifulSoup(
            BLANK_HTML, 'html.parser')
        company = company.text if company else None
        industry_class = soup.find(class_="details-content")
        industry_elm = industry_class.find(class_="header-line") if industry_class else BeautifulSoup(
            BLANK_HTML, 'html.parser')
        raw_industry = industry_elm.text if industry_elm else None
        industry, terminus_industry_label, industry_status_tag = map_raw_industry_with_croswalk_industry(raw_industry)
        website_tag = website_company_tag.find(class_="company-link header-line") if website_company_tag else None
        if website_tag and website_tag.get("href"):
            website = website_tag.get("href").strip()
            if not website:
                website = None
        else:
            website = None
        founded_elm = soup.find(string=" Founded ")
        founded = founded_elm.next.text if founded_elm else None
        technology = soup_find_all(soup, class_="name-vendor-wrapper")
        technology = [tech.a.text.strip() for tech in technology] if technology else None
        products = [prod.text.strip() for prod in soup_find_all(soup, class_="product-name")]
        products = products if products else None
        customers = ",".join([customers.text.strip() for customers in soup_find_all(soup,
                                                                                    class_="company-name")])
        comp_elm = soup.select_one('div.details-wrapper:not([id])')
        if comp_elm:
            social_links = comp_elm.find_all(class_="social-link-wrapper")
            linkedin_link = next((link.get("href")
                                 for link in social_links if "linkedin.com" in link.get("href", "")), None)

            facebook_link = next((link.get("href", "")
                                  for link in social_links if "facebook.com" in link.get("href", "")), None)
            twitter_link = next((link.get("href", "")
                                 for link in social_links if "twitter.com" in link.get("href", "")), None)
        else:
            linkedin_link = facebook_link = twitter_link = None
        links = {
            'linkedin_url': linkedin_link,
            'facebook_url': facebook_link,
            'twitter_url': twitter_link,
            'crunchbase_url': None
        }
        address_phone_list = soup.find_all(class_="contact-line")
        hq_address = address_phone_list[0].text if address_phone_list else ""
        hq_phone = address_phone_list[1].text if len(address_phone_list) > 1 else None
        revenue_employees_founded_list = soup.find_all(class_="record-content")
        revenue_str = revenue_employees_founded_list[0].text if revenue_employees_founded_list else None
        revenue, inferred_revenue = transform_employee_revenue_value(revenue_str)
        raw_employees = revenue_employees_founded_list[1].text if len(revenue_employees_founded_list)\
            > 1 else None
        employees, inferred_employees = transform_employee_revenue_value(raw_employees)
        founded = revenue_employees_founded_list[2].text if len(revenue_employees_founded_list)\
            > 2 else None
        desc = soup.find(class_="description-container overview-block")
        desc = desc.find_all(class_="description-content") if desc else None
        if desc and len(desc) > 0:
            desc = desc[0].text.strip() if desc[0].text else None
        else:
            desc = None

        funding_elm = soup.find(string="Funding History")
        funding = None
        if funding_elm:
            funding_text = funding_elm.next.text.replace("NASDAQ:", "").strip()
            pattern = re.compile(r"\$(\d+(\.\d+)?) [MBT]", flags=re.I)
            match = pattern.search(funding_text)
            if match:
                funding = match.group(0)
        competitors = get_competitors(soup)
        ticker_elm = soup.find(string="Stock Symbol")
        ticker = ticker_elm.next.text.replace("NASDAQ:", "").strip() if ticker_elm else None
        contacts = parse_contact_information(soup)
        result = {"company": company, "website": website, "hq_address": hq_address, "hq_phone":
                  hq_phone, "industry": industry, 'terminus_industry_label': terminus_industry_label,
                  'industry_status': industry_status_tag, "ticker": ticker, "funding": funding,
                  "links": links, "technology": technology, "products": products, "largest_customer":
                  customers, "competitors": competitors, "revenue": revenue, "inferred_revenue":
                  inferred_revenue, "employees": employees, "inferred_employees": inferred_employees,
                  "founded": founded, "description": desc, "contacts": contacts}
        return result
    except Exception:
        exc_type, value, traceback = sys.exc_info()
        error_list.append(exc_type.__name__)
        logger.error(f"Unexpected exception occured", exc_info=1)
        return result
