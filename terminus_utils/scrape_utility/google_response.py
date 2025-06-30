
from bs4 import BeautifulSoup
from bs4.element import Tag
from terminus_utils.logger import logger
def get_source_link(google_soup, website):
    """Returns the"""
    result_div = google_soup.find_all('div', attrs={'class': 'g'}) if isinstance(google_soup, BeautifulSoup) else []
    for result in result_div:
        try:
            link = result.find('a', href=True)
            title = result.find('h3')
            description = result.find(attrs = {"style": "-webkit-line-clamp:2"})
            if description is None:
                continue  
            if isinstance(link, Tag):
                link = link["href"]
            if isinstance(title, Tag):
                title = title.text
            if isinstance(description, Tag):
                description = description.text
            if (website in description.lower()) and ("zoominfo.com/c/" in str(link)):
                websites = website
                links = link
            return links, websites  # Return the first link that matches the criteria.
        except AttributeError as e:
            websites = ""
            links = ""
            print(f"An error occurred while parsing the HTML: {e}")  # Log the error for debugging purposes.
            return links, websites


def get_soup():
    # Reading the HTML from the test file
    #/Users/vivek.verma/datacloud_scraping_utilities/scraper_automation/source_automation/test_cases/rocketreach.html
    #/Users/vivek.verma/datacloud_scraping_utilities/scraper_automation/source_automation/test_cases/cbinisght.html
    #/Users/vivek.verma/datacloud_scraping_utilities/scraper_automation/source_automation/test_cases/owler.html
    #/Users/vivek.verma/datacloud_scraping_utilities/scraper_automation/source_automation/test_cases/zoominfo.html
    #/Users/vivek.verma/datacloud_scraping_utilities/scraper_automation/source_automation/test_cases/datanyze.html
    #/Users/vivek.verma/datacloud_scraping_utilities/scraper_automation/source_automation/test_cases/visual_visitor.html
    with open(r'terminus_utils/scrape_utility/temp_google.html') as f:
        html = f.read()
    return BeautifulSoup(html, 'html.parser')

# Get the BeautifulSoup object
soup_object = get_soup()


source_link, domain = get_source_link(soup_object,"mylan.com")

print(source_link, domain)



target_domains = ["zoominfo.com/c/", "rocketreach.co","datanyze.com/companies/"]

def extract_links_and_descriptions_with_option(google_soup, website, target_domains, return_type="both"):
    """Extract"""
    if not isinstance(google_soup, BeautifulSoup):
        logger.error("Invalid google_soup. Expected a BeautifulSoup object.")
        return [], []

    if not target_domains:
        logger.error("No target domains provided.")
        return [], []

    result_div = google_soup.find_all('div', attrs={'class': 'g'})
    links = []
    descriptions = []

    for r in result_div:
        try:
            link = r.find('a', href=True)
            description = r.find(attrs={"style": "-webkit-line-clamp:2"})

            link = link["href"] if isinstance(link, Tag) else None
            description = description.text.strip() if isinstance(description, Tag) else None

            if not link or not description:
                continue

            if (website.lower() in description.lower()) and any(domain in link for domain in target_domains):
                links.append(link)
                descriptions.append(description)
        except Exception as e:
            logger.error(f"Error processing result: {e}", exc_info=True)

    if return_type == "links":
        return links
    elif return_type == "descriptions":
        return descriptions
    else:
        return links, descriptions 
