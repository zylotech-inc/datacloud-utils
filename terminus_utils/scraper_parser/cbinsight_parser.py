import re
import sys
from bs4 import BeautifulSoup, Tag
from terminus_utils.logger import logger
from terminus_utils.scraper_parser.scraper_utils import (
    get_text_with_default, get_text_with_default_output_none, log_exception, soup_find_all,
    map_raw_industry_with_croswalk_industry, upload_html_to_s3, ZYTE_API_KEY)
from terminus_utils.api_utils import transform_employee_revenue_value

BLANK_HTML = "<span></span>"
error_list = []  # TODO: need to ask

def get_contact_details(soup):
    """Extract contact details from a BeautifulSoup object."""
    profiles = soup_find_all(soup, class_="profile-caption")
    contacts_dict = {}
    for no, profile in enumerate(profiles, start=1):
        employee = {}
        contact_name = get_text_with_default_output_none(profile, "h3")
        contact_job_title_el = get_text_with_default(profile, "h4")
        contact_job_title = contact_job_title_el.replace(
            "\n", "").strip().replace(
            "  ", "") if contact_job_title_el else None
        contact_location_el = get_text_with_default(profile, ".location")
        contact_location = contact_location_el.replace("\n", "").strip() if contact_location_el else None
        employee["contact_name"] = contact_name
        employee["contact_job_title"] = contact_job_title
        employee["contact_location"] = contact_location
        contacts_dict[f"contact_{no}"] = employee
    return contacts_dict