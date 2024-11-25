import logger
import logging
from datetime import datetime
import psycopg2
from datetime import datetime
from datetime import datetime, timedelta


def get_days_since_last_update(updated_at, last_used):
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
    if isinstance(last_used, str):
        last_used = datetime.strptime(last_used, "%Y-%m-%d")

    # Use the most recent date
    most_recent_date = max(updated_at, last_used) if last_used else updated_at

    # Calculate the number of days since the most recent date
    days_since_update = (datetime.now() - most_recent_date).days
    return days_since_update

# 

def check_domain_and_update_url(domain_name, data_source_id, cursor):
    """
    Check if the domain exists in domain_data_sources table and update the URL if necessary.

    Args:
        domain_name (str): The domain name to check.
        data_source_id (int): The data source ID to check.
        cursor (object): The database cursor to execute queries.

    Returns:
        dict: A dictionary containing either the source URL or the domain name, and the data_source_id (if applicable).
    """
    try:
        # Query the database for domain info from domain_data_sources
        cursor.execute("""
            SELECT data_source_id, source_url, created_at, updated_at, last_used, not_found, all_data_found 
            FROM domain_data_sources 
            WHERE domain_name = %s
        """, (domain_name,))
        
        results = cursor.fetchall()

        # Step 0: Handle case where no records exist for the domain
        if not results:
            logger.info(f"No entries found for domain '{domain_name}' in the database.")
            return {'source_url': domain_name}

        logger.info(f"Query results for domain '{domain_name}': {results}")

        # Separate entries with and without source URLs
        url_entries = [row for row in results if row[1]]  # Rows with source_url
        no_url_entries = [row for row in results if not row[1]]  # Rows without source_url

        # Step 1: Prioritize entries with `all_data_found = True`
        if url_entries:
            for row in url_entries:
                data_source_id, source_url, created_at, updated_at, last_used, not_found, all_data_found = row
                if all_data_found:
                    logger.info(f"URL found with all_data_found=True for domain '{domain_name}'.")
                    return {'source_url': source_url, 'data_source_id': data_source_id}

        # Step 3: Handle entries without source URLs
        elif no_url_entries:
            # Check if all entries for the domain have empty source_url
            if all(row[1] is None or row[1] == '' for row in no_url_entries):
                # Check if the `updated_at` date is more than 180 days ago
                for row in no_url_entries:
                    created_at = row[2]  # Assuming created_at is the 3rd column in the result
                    updated_at = row[3]  # Assuming updated_at is the 4th column in the result

                    # Ensure created_at is not None and is a valid datetime object
                    if created_at:
                        if isinstance(created_at, str):
                            created_at = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")  # Adjust if needed
                        
                        # Check if the `created_at` time is less than 3 minutes ago
                        if (datetime.now() - created_at) < timedelta(minutes=3): # TODO: change timing as per requirements
                            logger.info(f"Domain '{domain_name}' was created within the last 3 minutes and has no source_url.")
                            return {'source_url': domain_name}

                    # Handle `updated_at` logic
                    if updated_at:
                        if isinstance(updated_at, str):
                            updated_at = datetime.strptime(updated_at, "%Y-%m-%d %H:%M:%S")  # Adjust if needed
                        
                        # Check if the `updated_at` time is more than 180 days ago
                        if (datetime.now() - updated_at).days > 180:
                            logger.info(f"All entries for domain '{domain_name}' have empty source_url, and 180 days have passed since last update.")
                            return {'source_url': domain_name}

                # If `updated_at` is within 180 days, log and skip this entry
                logger.info(f"All entries for domain '{domain_name}' have empty source_url, but updated within 180 days. Skipping.")
                return None  # You can choose to return or handle differently here

    except Exception as e:
        logger.error(f"Error while checking domain '{domain_name}': {e}")
        return {'source_url': domain_name}

def update_table_with_url(domain, url, not_found, data_source_id, cursor, connection):
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

    try:
        # Check if the domain and data_source_id combination exists
        cursor.execute("""
            SELECT source_url, last_used, not_found, updated_at 
            FROM domain_data_sources 
            WHERE domain_name = %s AND data_source_id = %s
        """, (domain, data_source_id))
        result = cursor.fetchone()

        if result:
            # Unpack the result
            existing_url, last_used_timestamp, existing_not_found, updated_at = result
            
            # Calculate days since last update
            days_since_update = (current_timestamp - updated_at).days if updated_at else float('inf')

            if existing_url:
                # If the URL exists, update `last_used`
                print(f"Domain {domain} exists with URL {existing_url}. Updating last_used timestamp.")
                query = """
                UPDATE domain_data_sources 
                SET last_used = %s 
                WHERE domain_name = %s AND data_source_id = %s
                """
                cursor.execute(query, (current_timestamp, domain, data_source_id))
            elif not_found or (not existing_url and days_since_update <= 180):
                # If `source_url` is NULL but the record is less than 180 days old
                print(f"Domain {domain} has no URL but is active. Updating last_used timestamp.")
                query = """
                UPDATE domain_data_sources 
                SET last_used = %s 
                WHERE domain_name = %s AND data_source_id = %s
                """
                cursor.execute(query, (current_timestamp, domain, data_source_id))
            else:
                # Update the not_found status or any other relevant details
                print(f"Domain {domain} exists but conditions for update are not met.")
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


import sqlite3
import logging

logger = logging.getLogger(__name__)

def update_is_found_in_database(cursor, connection, domain_name, source_url, all_data_found):
    """
    Updates the `is_found` column in the domain_data_sources table.

    Args:
        cursor (sqlite3.Cursor): Database cursor for executing the query.
        connection (sqlite3.Connection): Database connection for committing changes.
        domain_name (str): The domain being processed.
        source_url (str): The source URL associated with the domain.
        is_found (bool): The value to set for the `all_data_found` column.
    """
    try:
        # Ensure the correct column names in the query
        cursor.execute("""
            UPDATE domain_data_sources
            SET all_data_found = %s
            WHERE domain_name = %s AND source_url = %s
        """, (all_data_found, domain_name, source_url))
        connection.commit()
        logger.info(f"Updated `is_found` for domain_name: {domain_name}, source_url: {source_url} to {all_data_found}.")
    except Exception as e:
        logger.error(f"Error updating `is_found` for domain_name: {domain_name}, source_url: {source_url}: {e}")



