import psycopg2
from datetime import datetime
# from source_util import connect_to_db__for_caching
from logger import logger
def get_days_since_last_update(updated_at):
    """Calculate the number of days since last update."""
    return (datetime.now() - updated_at).days

def check_domain_and_update_url(domain_name, data_source_id, cursor):
    """
    Check if the domain exists in domain_data_sources table and update the URL if necessary.
    
    Args:
        domain_name (str): The domain name to check.
        data_source_id (int): The datasource id to check.
        cursor (object): The database cursor to execute queries.

    Returns:
        dict: A dictionary containing either the source URL or the domain name, and the data_source_id.
    """
    try:
        # Query the database for domain info from domain_data_sources
        cursor.execute("""
            SELECT data_source_id, source_url, updated_at, not_found 
            FROM domain_data_sources 
            WHERE domain_name = %s
        """, (domain_name,))
        
        results = cursor.fetchall()

        # Step 1: If no records are found, return the domain name indicating it does not exist
        if not results:
            # Domain doesn't exist, return domain_name and the provided data_source_id
            return {'source_url': domain_name}
        
        # Separate entries with URLs from those without
        url_entries = [row for row in results if row[1] and not row[3]]
        no_url_entries = [row for row in results if not row[1] and row[3]]

        # Step 2: Return the first found entry with a URL if any exist
        if url_entries:
            for data_source_id, source_url, updated_at, not_found in url_entries:
                return {
                    'source_url': source_url,
                    'data_source_id': data_source_id
                }
        
        # Step 3: Check if all entries without URLs are older than 180 days
        if no_url_entries:
            for data_source_id, source_url, updated_at, not_found in no_url_entries:
                days_since_update = get_days_since_last_update(updated_at)
                
                # If the last update was older than 180 days, return the domain name
                if days_since_update > 180:
                    return {'source_url': domain_name, 'data_source_id': data_source_id}
                else:
                    # If not updated within 180 days, we do not return the domain
                    continue
        
        # Step 4: No valid URLs or records found; return None
        return None

    except psycopg2.DatabaseError as e:
        print(f"Database error: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None


def update_table_with_url(domain, url, not_found, data_source_id, cursor, connection):
    """
    Update the table with domain and URL information, or insert if the domain and data_source_id do not exist.
    If the URL exists, update only the `last_used` timestamp without overwriting the URL.

    Args:
        domain (str): Domain to be added or updated.
        url (str or None): The URL found, or None if not found.
        not_found (bool): Whether the domain was found in the search.
        data_source_id (int): ID of the data source.
        cursor (object): The database cursor to execute queries.
        connection (object): The database connection to handle transactions.
    """
    current_timestamp = datetime.now()

    try:
        # Check if the domain and data_source_id combination exists
        cursor.execute("""
            SELECT source_url, last_used, not_found 
            FROM domain_data_sources 
            WHERE domain_name = %s AND data_source_id = %s
        """, (domain, data_source_id))
        result = cursor.fetchone()

        if result:
            # If the combination exists, unpack the result
            existing_url, last_used_timestamp, existing_not_found = result
            
            if not_found:
                if existing_url:
                    # If the URL exists, update `last_used`
                    print(f"Domain {domain} exists with URL {existing_url}. Updating last_used timestamp.")
                    query = """
                    UPDATE domain_data_sources 
                    SET last_used = %s 
                    WHERE domain_name = %s AND data_source_id = %s
                    """
                    cursor.execute(query, (current_timestamp, domain, data_source_id))
                else:
                    # If the domain exists but no URL is found, update with the new URL
                    print(f"Domain {domain} exists but no URL found. Updating with new URL: {url}.")
                    query = """
                    UPDATE domain_data_sources 
                    SET source_url = %s, not_found = %s, updated_at = %s, last_used = %s
                    WHERE domain_name = %s AND data_source_id = %s
                    """
                    cursor.execute(query, (url, not_found, current_timestamp, current_timestamp, domain, data_source_id))
            else:
                # If URL is not found, update only the not_found status and last_used
                print(f"Domain {domain} exists but URL not found. Updating not_found status and timestamps.")
                query = """
                UPDATE domain_data_sources 
                SET not_found = %s, last_used = %s 
                WHERE domain_name = %s AND data_source_id = %s
                """
                cursor.execute(query, (False, current_timestamp, domain, data_source_id))
        else:
            # If the domain and data_source_id do not exist, insert a new record
            print(f"Domain {domain} and data_source_id {data_source_id} do not exist. Inserting new record.")
            query = """
            INSERT INTO domain_data_sources (domain_name, source_url, not_found, data_source_id, created_at, updated_at, last_used)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (
                domain, 
                url, 
                not_found, 
                data_source_id, 
                current_timestamp, 
                current_timestamp, 
                current_timestamp
            ))

        connection.commit()  # Commit the transaction if everything goes well
        print(f"Transaction committed for domain {domain} with URL: {url} and found status: {not_found}")

    except psycopg2.DatabaseError as e:
        print(f"Database error: {e}")
        connection.rollback()  # Roll back the transaction on error
    except Exception as e:
        print(f"Unexpected error: {e}")
        connection.rollback()  # Roll back for any other error

# def search_google_for_all_services(*, website: str, soup):
#     """
#     Searches Google results to find links that match the input website for specific services
#     (ZoomInfo, Owler, Datanyze, and VisualVisitor).

#     Args:
#         website (str): The website to search for in the Google results.
#         soup (BeautifulSoup): BeautifulSoup object containing the parsed HTML of the Google search results.

#     Returns:
#         dict: Contains search status, the matching links, and the services found (ZoomInfo, Owler, Datanyze, VisualVisitor).
#     """
#     clean_website = website.replace('www.', '')
#     result_dict = {
#         'domain': website,
#         'services': {
#             'ZoomInfo': {'link': None, 'scraped_status': 'not_found'},
#             'Owler': {'link': None, 'scraped_status': 'not_found'},
#             'Datanyze': {'link': None, 'scraped_status': 'not_found'},
#             'VisualVisitor': {'link': None, 'scraped_status': 'not_found'}
#         }
#     }

#     if soup is None:
#         logger.warning(f"No soup found for {website}")
#         return result_dict

#     result_divs = soup.find_all('div', attrs={'class': 'g'}) if isinstance(soup, BeautifulSoup) else []

#     for r in result_divs:
#         try:
#             link = r.find('a', href=True)
#             description = r.find(class_='VwiC3b yXK7lf lVm3ye r025kc hJNv6b Hdw6tb')

#             if description is None or link is None:
#                 continue

#             if isinstance(link, Tag):
#                 link = link["href"]
#             if isinstance(description, Tag):
#                 description = description.text.lower()

#             # Check for ZoomInfo
#             if clean_website in description and "zoominfo.com/c/" in link:
#                 result_dict['services']['ZoomInfo'].update({'link': link, 'scraped_status': 'found'})

#             # Check for Owler
#             elif clean_website in description and "owler.com/company/" in link:
#                 result_dict['services']['Owler'].update({'link': link, 'scraped_status': 'found'})

#             # Check for Datanyze
#             elif clean_website in description and "datanyze.com/" in str(link):
#                 result_dict['services']['Datanyze'].update({'link': link, 'scraped_status': 'found'})

#             # Check for VisualVisitor
#             elif clean_website in description and "visualvisitor.com/companies/" in str(link):
#                 result_dict['services']['VisualVisitor'].update({'link': link, 'scraped_status': 'found'})

#         except Exception as e:
#             logger.exception(f"Exception occurred while parsing Google results: {e}")

#     return result_dict


def fetch_source_url_and_data_source_id(domain, cursor):
    """
    Fetch source_url and data_source_id from the domain_data_sources table by matching the domain_name.
    """
    query = """
    SELECT source_url, data_source_id 
    FROM domain_data_sources 
    WHERE domain_name = %s AND not_found = FALSE
    """
    cursor.execute(query, (domain,))
    result = cursor.fetchone()
    if result:
        source_url, data_source_id = result
        return source_url, data_source_id
    return None, None