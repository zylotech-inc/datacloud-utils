import logger
import logging
from datetime import datetime
import psycopg2
from datetime import datetime
from datetime import datetime, timedelta


def get_days_since_last_update(updated_at):
    """
    Calculate the number of days since the last update.

    Args:
        updated_at (datetime or str): The date when the entry was last updated.
        last_used (datetime or str): The date when the entry was last used.

    Returns:
        int: Number of days since the most recent date (updated_at or last_used).
    """
    # Ensure updated_at and last_used are datetime objects
    if isinstance(updated_at, str):
        updated_at = datetime.strptime(updated_at, "%Y-%m-%d")
    
    # Calculate the number of days since the most recent date
    days_since_update = (datetime.now() - updated_at).days
    return days_since_update

# Thresholds
CREATED_THRESHOLD_MINUTES = 5
UPDATED_THRESHOLD_DAYS = 180


def is_recent(datetime_obj, minutes=3):
    """
    Check if a datetime object is within a recent time window.
    Args:
        datetime_obj (datetime): The datetime object to check.
        minutes (int): The threshold in minutes.
    Returns:
        bool: True if within the recent window, False otherwise.
    """
    if not datetime_obj:
        return False
    return (datetime.now() - datetime_obj) < timedelta(minutes=minutes)


def is_older_than(datetime_obj, days=180):
    """
    Check if a datetime object is older than a certain number of days.
    Args:
        datetime_obj (datetime): The datetime object to check.
        days (int): The threshold in days.
    Returns:
        bool: True if older than the threshold, False otherwise.
    """
    if not datetime_obj:
        return False
    return (datetime.now() - datetime_obj).days > days


def check_domain_and_update_url(domain_name, data_source_id, conn):
    """
    Check if the domain exists in domain_data_sources table for google search and update the URL if necessary.
    Args:
        domain_name (str): The domain name to check.
        data_source_id (int): The data source ID to check.
        cursor (object): The database cursor to execute queries.
    Returns:
        dict: A dictionary containing either the source URL or the domain name, and the data_source_id (if applicable).
    """
    cur = conn.cursor()
    try:
        # Query the database for domain info from domain_data_sources
        cur.execute("""
            SELECT data_source_id, source_url, created_at, updated_at, all_data_found, not_found
            FROM domain_data_sources 
            WHERE domain_name = %s
        """, (domain_name,))
        
        results = cur.fetchall()

        # Step 0: Handle case where no records exist for the domain
        if not results:
            logger.info(f"No entries found for domain '{domain_name}' in the database.")
            return {'domain_name': domain_name}

        logger.info(f"Query results for domain '{domain_name}': {results}")

        # Separate entries with and without source URLs
        url_entries = [row for row in results if row[1]]  # Rows with source_url
        no_url_entries = [row for row in results if not row[1]]  # Rows without source_url

        # Step 1: Prioritize entries with `all_data_found = True`
        for row in url_entries:
            data_source_id, source_url, created_at, updated_at, all_data_found, not_found = row
            # Step 1: Check if `all_data_found` is True
            if all_data_found:
                logger.info(f"URL found with all_data_found=True for domain '{domain_name}'.")
                return {'source_url': source_url, 'data_source_id': data_source_id}
            
            # Step 2: Check if `all_data_found` is None and if `created_at` is recent
            if all_data_found is None:
                logger.info(f"all_data_found is NULL for domain '{domain_name}', checking created_at.")
                
                # Check `created_at` if available
                if created_at:
                    # Convert `created_at` to datetime if it's a string
                    if isinstance(created_at, str):
                        created_at = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")  # Adjust format as needed
                    
                    # Check if `created_at` is recent
                    if is_recent(created_at, minutes=CREATED_THRESHOLD_MINUTES):
                        logger.info(f"Domain '{domain_name}' was created within the last {CREATED_THRESHOLD_MINUTES} minutes and has no source_url.")
                        return {'domain_name': domain_name}
                
                    else:
                        return {'source_url': source_url, 'data_source_id': data_source_id}
            
                elif all_data_found is None and not_found is False:
                    logger.info(f"Domain '{domain_name}' has no source_url but has not_found=False.")
                    return {'source_url': source_url, 'data_source_id': data_source_id}  
            
        # Step 2: Handle entries without source URLs
        for row in no_url_entries:
            data_source_id, source_url, created_at, updated_at, all_data_found = row
            # Handle `created_at` logic
            if created_at:
                if isinstance(created_at, str):
                    created_at = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")  # Adjust format as needed
                if is_recent(created_at, minutes=CREATED_THRESHOLD_MINUTES):
                    logger.info(f"Domain '{domain_name}' was created within the last {CREATED_THRESHOLD_MINUTES} minutes and has no source_url.")
                    return {'domain_name': domain_name}

            # Handle `updated_at` logic
            if updated_at:
                if isinstance(updated_at, str):
                    updated_at = datetime.strptime(updated_at, "%Y-%m-%d %H:%M:%S")  # Adjust format as needed
                if is_older_than(updated_at, days=UPDATED_THRESHOLD_DAYS):
                    logger.info(f"All entries for domain '{domain_name}' have empty source_url, and {UPDATED_THRESHOLD_DAYS} days have passed since last update.")
                    return {'domain_name': domain_name}

        # Default case: Entries without URLs, updated within the threshold
        logger.info(f"All entries for domain '{domain_name}' have empty source_url, but updated within {UPDATED_THRESHOLD_DAYS} days. Skipping.")
        return None

    except Exception as e:
        logger.error(f"Error while checking domain '{domain_name}': {e}")
        return {'domain_name': domain_name}


def update_table_with_url(domain, url, not_found, data_source_id, conn):
    """
    Update the table with domain and URL information, or insert if the domain and data_source_id do not exist.
    If the URL exists, update only the `last_used` timestamp without overwriting the URL.
    Also update `last_used` if `source_url` is NULL but the record exists and is less than 180 days old.

    Args:
        domain (str): Domain to be added or updated.
        url (str or None): The URL found, or None if not found.
        not_found (bool): Whether the domain was found in the search.
        data_source_id (int): ID of the data source.
        cursor (object): The database cursor to execute queries.
        connection (object): The database connection to handle transactions.
    """
    current_timestamp = datetime.now()
    cur = conn.cursor()
    try:
        # Check if the domain and data_source_id combination exists
        cur.execute("""
            SELECT source_url, updated_at 
            FROM domain_data_sources 
            WHERE domain_name = %s AND data_source_id = %s
        """, (domain, data_source_id))
        result = cur.fetchone()

        if result:
            # Unpack the result
            existing_url, updated_at = result
            
            # Calculate days since last update
            days_since_update = (current_timestamp - updated_at).days if updated_at else float('inf')

            if existing_url:
                # If the URL exists, update `last_used`
                query = """
                UPDATE domain_data_sources 
                SET last_used = %s 
                WHERE domain_name = %s AND data_source_id = %s
                """
                cur.execute(query, (current_timestamp, domain, data_source_id))
            elif not_found or (not existing_url and days_since_update <= 180):
                # If `source_url` is NULL but the record is less than 180 days old
                query = """
                UPDATE domain_data_sources 
                SET last_used = %s 
                WHERE domain_name = %s AND data_source_id = %s
                """
                cur.execute(query, (current_timestamp, domain, data_source_id))

            elif days_since_update > 180:
                # If `updated_at` is older than 180 days, update `source_url`, `last_used`, and `updated_at`
                query = """
                UPDATE domain_data_sources 
                SET source_url = %s, last_used = %s, updated_at = %s 
                WHERE domain_name = %s AND data_source_id = %s
                """
                cur.execute(query, (url, current_timestamp, current_timestamp, domain, data_source_id))
        else:
            # If the domain and data_source_id do not exist, insert a new record
            query = """
            INSERT INTO domain_data_sources (domain_name, source_url, not_found, data_source_id, created_at, updated_at, last_used)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cur.execute(query, (
                domain, 
                url, 
                not_found, 
                data_source_id, 
                current_timestamp, 
                current_timestamp, 
                current_timestamp
            ))

        conn.commit()  # Commit the transaction if everything goes well

    except psycopg2.DatabaseError as e:
        logger.info(f"Database error: {e}")
        conn.rollback()  # Roll back the transaction on error
    except Exception as e:
        logger.info(f"Unexpected error: {e}")
        conn.rollback()  # Roll back for any other error


logger = logging.getLogger(__name__)

def update_is_found_in_database(conn, domain_name, source_url, all_data_found):
    """
    Updates the `is_found` column in the domain_data_sources table.

    Args:
        cursor (sqlite3.Cursor): Database cursor for executing the query.
        connection (sqlite3.Connection): Database connection for committing changes.
        domain_name (str): The domain being processed.
        source_url (str): The source URL associated with the domain.
        is_found (bool): The value to set for the `all_data_found` column.
    """
    cur = conn.cursor()
    try:
        # Ensure the correct column names in the query
        cur.execute("""
            UPDATE domain_data_sources
            SET all_data_found = %s
            WHERE domain_name = %s AND source_url = %s
        """, (all_data_found, domain_name, source_url))
        conn.commit()
        logger.info(f"Updated `is_found` for domain_name: {domain_name}, source_url: {source_url} to {all_data_found}.")
    except Exception as e:
        logger.error(f"Error updating `is_found` for domain_name: {domain_name}, source_url: {source_url}: {e}")



