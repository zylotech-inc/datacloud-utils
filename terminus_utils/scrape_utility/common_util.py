"""
This module performs various operations related to web scraping, data processing, and logging.
It integrates with external services like AWS (boto3), databases (psycopg2), and uses libraries
for parsing HTML (BeautifulSoup), URL manipulation (urllib), and more.

Imports are organized into:
1. Standard library imports.
2. Third-party library imports.
3. Local application-specific imports.
"""
from dotenv import load_dotenv  # noqa
load_dotenv('.env')
import json
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

import random
import time
import csv
import re
import traceback
from io import StringIO

import boto3
import psycopg2
import requests
import tldextract
from botocore.exceptions import BotoCoreError, ClientError
from bs4 import BeautifulSoup
from terminus_utils.logger import logger

AWS_BUCKET = 'terminus-raw-scraped-result'     # s3 bucket name
AWS_SOURCE_BUCKET = 'source-scraper-bucket'
# Zyte API Key or Zyte Proxy
ZYTE_API_KEY = os.environ.get('ZYTE_API_KEY', "API_KEY NOT SET")
SMARTPROXY_ZYTE_API_KEY = ""
MAX_RETRY = 10
AWS_ACCESS_KEY = os.environ.get('AWS_ACCESS_KEY', "ACCESS_KEY NOT SET")
AWS_SECRET_KEY = os.environ.get('AWS_SECRET_KEY', "SECRET_KEY NOT SET")
MAX_NUMBER_OF_SQS_MESSAGES = int(os.environ.get('MAX_NUMBER_OF_SQS_MESSAGES', 10))
# Create S3 client
s3 = boto3.client('s3',
                  aws_access_key_id=AWS_ACCESS_KEY,
                  aws_secret_access_key=AWS_SECRET_KEY,
                  region_name='us-east-1')
blank_html = "<span></span>"
BEAUTIFULLSOUP_PARSER = "html.parser"
GLOBAL_CROSSWALK_FILE = 'global_crosswalk.csv'
TERMINUS_INDUSTRY_CROSSWALK_FILE = 'terminus_industry_label.csv'
SQS_QUEUE_URL = os.environ.get('SQS_QUEUE_URL', "SQS_QUEUE_URL NOT SET")
headers = {"user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
           "(KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"}


def website_clean(text):
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







def create_post_request(end_point_url: str, pay_load: str):
    """
    Hit the API based on the url and the json data passed
    :param end_point_url: API url
    :param pay_load: list of json input data
    :return: list of json output
    """
    try:
        request_output = requests.post(url=end_point_url, data=pay_load, timeout=120)
        if request_output.status_code == 200:
            response = request_output.json()
            return response
        else:
            logger.info(f"status code is {request_output.status_code} with the message \
                        {request_output.text}")
    except Exception as e:
        logger.error(f"Exception while creating the post request: {str(e)}")

#TODO: #need to remove
# def get_api_response_df(api_url: str, pay_load: str) -> pd.DataFrame:
#     """
#     Fetches data from a given API URL using a POST request with the specified
#     payload and returns the response as a DataFrame.

#     Args:
#         api_url (str): The URL of the API endpoint to send the POST request to.
#         pay_load (str): The payload to be sent with the POST request.

#     Returns:
#         pd.DataFrame: A DataFrame containing the standardized JSON response from the API.

#     Raises:
#         Exception: If the API request fails or the response cannot be normalized into a DataFrame.

#     """
#     api_response = create_post_request(api_url, pay_load=pay_load)
#     standardised_df = pd.json_normalize(api_response)
#     return standardised_df


def soup_find_all(soup, **kwargs):
    """
    Finds all matching elements in a BeautifulSoup object based on criteria.

    Parameters:
    - soup (BeautifulSoup): A BeautifulSoup object.
    - **kwargs: Criteria for `find_all`.

    Returns:
    - list: Matching elements or an empty list. If an error occurs, returns a
        BeautifulSoup object with blank HTML.
    """
    try:
        selector = soup.find_all(**kwargs)
        if selector:
            return selector
        else:
            return []
    except AttributeError:
        logger.error("Exception Occured", exc_info=1)
        return BeautifulSoup(blank_html, BEAUTIFULLSOUP_PARSER)


def soup_find(soup, **kwargs):
    """
    Finds a single element in a BeautifulSoup object based on the given criteria.

    Parameters:
    - soup (BeautifulSoup): A BeautifulSoup object representing the parsed HTML.
    - **kwargs: Criteria for the `find` method.

    Returns:
    - BeautifulSoup element or a BeautifulSoup object with blank HTML if no element
      is found or an error occurs.
    """
    try:
        selector = soup.find(**kwargs)
        if selector:
            return selector
        else:
            return BeautifulSoup(blank_html, BEAUTIFULLSOUP_PARSER)
    except AttributeError:
        logger.error("Exception Occured", exc_info=1)
        return BeautifulSoup(blank_html, BEAUTIFULLSOUP_PARSER)


def extract_domain(url):
    """
    Extracts the domain from a URL.

    Parameters:
    - url: The URL to extract the domain from.

    Returns:
    - str: The domain of the URL.
    """
    ext = tldextract.extract(url)
    domain = ext.domain + '.' + ext.suffix
    return domain


def upload_html_to_s3(html_content, website: str, source: str):
    """
    Uploads HTML content to an S3 bucket and returns the S3 URI.

    Parameters:
    - html_content: The HTML content to upload.
    - website: The website URL for domain extraction.
    - source: The source identifier for the file key.

    Returns:
    - str: The S3 URI of the uploaded HTML file.
    """
    if html_content is None:
        return ''
    s3 = boto3.client('s3',
                      aws_access_key_id=AWS_ACCESS_KEY,
                      aws_secret_access_key=AWS_SECRET_KEY,
                      region_name='us-east-1')
    domain = extract_domain(website)
    bucket_name = 'terminus-raw-html'
    file_key = f'{domain}/{source}/raw.html'
    s3.put_object(Bucket=bucket_name, Key=file_key, Body=html_content)
    s3_uri = f's3://{bucket_name}/{domain}/{source}/raw.html'
    return s3_uri


def conn_to_pg(dbname, user, password, host='localhost', port=5432):
    """
    Connects to a PostgreSQL database and returns the connection object.

    Parameters:
    - dbname: Database name.
    - user: Username.
    - password: Password.
    - host: Database host (default: 'localhost').
    - port: Port number (default: 5432).

    Returns:
    - psycopg2.connection: Database connection object.
    """
    try:
        logger.info(f"Connecting to database: {dbname} at {host}:{port} with user: {user}")
        conn = psycopg2.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password
        )
        logger.info(f"Connected to database: {dbname} at {host}:{port} with user: {user}")
        return conn
    except (Exception, psycopg2.Error):
        logger.error("Unable to connect to db:", exc_info=1)



def ingest_into_pg(conn, data: dict, table_name: str = 'scrape_results'):
    """
    Simulates inserting scrape results into PostgreSQL.

    Parameters:
    - conn: Database connection object
    - table_name: Name of the table to insert into.
    - data: Dictionary containing the necessary values for the insert operation
    """
    try:
        # Define the ordered tuple of columns
        ordered_columns = (
            'work_queue',
            'domain',
            'data_source',
            'error',
            'result_url',
            'raw_html',
            'raw_json',
            'scraped_status',
            'result_status_code',
            'is_validated',
            'created_at',
            'updated_at',
            'human_intervention'
        )
        columns = ', '.join(ordered_columns)
        placeholders = ', '.join(['%s'] * len(ordered_columns))
        insert_scrape_results_query = f"""
            INSERT INTO {table_name} ({columns})
            VALUES ({placeholders})
            """
        cur = conn.cursor()

        values = tuple(data[column] for column in ordered_columns)
        cur.execute(insert_scrape_results_query, values)
        conn.commit()
        logger.info("Saved to DB")
    except Exception as e:
        logger.error(f"Error while data insertion: {e}", exc_info=True)


def read_csv_file_as_list_from_s3(s3_file_loc: str) -> list:
    """
    Reads a CSV file from an S3 bucket and returns its contents as a list of dictionaries.

    Args:
        s3_file_loc (str): The location of the CSV file in the S3 bucket.

    Returns:
        list: The contents of the CSV file as a list of dictionaries.
    """
    csv_obj = s3.get_object(Bucket=AWS_SOURCE_BUCKET, Key=s3_file_loc)
    body = csv_obj['Body']
    csv_string = body.read().decode('utf-8')
    
    # Use csv.DictReader to read the CSV into a list of dictionaries
    csv_reader = csv.DictReader(StringIO(csv_string))
    data = [row for row in csv_reader]
    
    return data

global_crosswalk_file = 'global_crosswalk.csv'
terminus_industry_crosswalk_file = 'terminus_industry_label.csv'
terminus_industry_data = read_csv_file_as_list_from_s3(terminus_industry_crosswalk_file)
global_crosswalk_data = read_csv_file_as_list_from_s3(global_crosswalk_file)



def read_crosswalk_industry() -> tuple[list, dict]:
    """
    Read industry crosswalk files from S3 and return lists and dictionaries.

    Returns:
        tuple[list, dict]: Lists and dictionaries of industry labels.
    """
    # Process terminus_industry_data to get a list of capitalized industry labels
    terminus_industry_list = [str.title(row['TERMINUS_INDUSTRY_LABEL_1']) for row in terminus_industry_data]

    # Create a dictionary from global_crosswalk_data, mapping 'Industry_Label' to 'Terminus_Industry_Label'
    global_crosswalk_dict = {}
    for row in global_crosswalk_data:
        industry_label = str.title(row["Industry_Label"])
        terminus_label = str.title(row["Terminus_Industry_Label"])
        global_crosswalk_dict[industry_label] = terminus_label
    
    return terminus_industry_list, global_crosswalk_dict

def convert_str_to_list(string, is_raw_industry=False):
    """
    Normalizes the industry string by replacing 'and' with '&', stripping whitespace, and handling None input.

    Args:
        industry (Optional[str]): The raw industry string.

    Returns:
        list: A list of normalized industry substrings or an empty list if input is None.
    """
    if not string:
        return []
    if is_raw_industry:
        return [elem.strip() for elem in string.lower().split(",") if elem]
    if not is_raw_industry:
        return [elem.replace(" and ", " & ").strip() for elem in string.lower().split(",") if elem]


def map_raw_industry_with_croswalk_industry(raw_industry):
    """
    Map raw industry string or list to known industry labels.

    Args:
        raw_industry (list/str): Raw industry string to map.

    Returns:
        str, str, str: raw_industry_list, terminus_industry_label, industry_status_tag
    """
    terminus_industry_label = None
    industry_status_tag = 'Human Intervention Required'
    terminus_industry, global_crosswalks = read_crosswalk_industry()
    if isinstance(raw_industry, str):
        raw_industry_list = convert_str_to_list(raw_industry, is_raw_industry=True)
    elif isinstance(raw_industry, list):
        raw_industry_list = raw_industry
    else:
        raw_industry_list = None
        terminus_industry_label = None
        industry_status_tag = 'Industry Not Found'
        return raw_industry_list, terminus_industry_label, industry_status_tag
    raw_industry_list = [industry.title() for industry in raw_industry_list if industry]
    for industry in raw_industry_list:
        if industry:
            industry = industry.title()
            if industry in terminus_industry:
                industry_status_tag = 'Found in Terminus Industry'
                terminus_industry_label = industry
                return raw_industry_list, terminus_industry_label.title(), industry_status_tag
            elif industry in global_crosswalks:
                industry_status_tag = 'Found in global crosswalk'
                terminus_industry_label = global_crosswalks[industry]
                return raw_industry_list, terminus_industry_label.title(), industry_status_tag
    return raw_industry_list, terminus_industry_label, industry_status_tag


def log_exception(error_message, exception, selector=None):
    """Utility function to log exceptions with detailed error information."""
    detailed_error_message = f"{error_message}\nException: {str(exception)}"
    if selector:
        detailed_error_message += f"\nSelector: {selector}"
    detailed_error_message += f"\nTraceback:\n{traceback.format_exc()}"
    logger.error(detailed_error_message)


def get_text_with_default(soup, selector, attribute=None, default=""):
    """Attempt to get text or attribute value from a BeautifulSoup element; 
                return default if not found."""
    try:
        element = soup.select_one(selector)
        if element:
            return element.get(attribute) if attribute else element.get_text(strip=True)
    except Exception as e:
        log_exception("Error occurred while processing element.", e, selector)
    return default


def fetch_from_sqs_standard():
    """
    Fetch one message from SQS queue with error handling.
    :param queue_url: SQS Queue URL
    :return: The message body (containing domains) or None if no messages are available.
    """
    try:
        domain_detail_list = []
        sqs = boto3.client('sqs',
                           aws_access_key_id=AWS_ACCESS_KEY,
                           aws_secret_access_key=AWS_SECRET_KEY,
                           region_name='us-east-1')
        # Fetch messages from the SQS queue
        response = sqs.receive_message(
            QueueUrl=SQS_QUEUE_URL,
            MaxNumberOfMessages=MAX_NUMBER_OF_SQS_MESSAGES,
            WaitTimeSeconds=5
        )
        logger.info("Reading from SQS")

        messages = response.get('Messages', [])
        if not messages:
            logger.info('No messages in the queue.')
            return None

            # Process each message sequentially
        for message in messages:
            message_body = json.loads(message['Body'])

            # Extract domain details from the message
            domain_list = message_body.get('domain_list')
            if domain_list:
                domain_detail_list.extend(domain_list)
            else:
                logger.info("No domain details found in this message.")

            # After processing, delete the message from the queue
            sqs.delete_message(
                QueueUrl=SQS_QUEUE_URL,
                ReceiptHandle=message['ReceiptHandle']
            )
            logger.info(f"Message {message['MessageId']} successfully processed and deleted.")
        logger.info(f"Received {len(domain_detail_list)} domains: {domain_detail_list}")
        return domain_detail_list

    except (BotoCoreError, ClientError, json.JSONDecodeError, KeyError) as error:
        # Handle all boto3 errors and log them
        logger.error(f"Failed to fetch or delete message: {error}", exc_info=True)
        return None
    except Exception as e:
        # Catch any other exceptions
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return None


def get_text_with_default_output_none(soup, selector, attribute=None, default=None):
    """Attempt to get text or attribute value from a BeautifulSoup element; 
                return default if not found."""
    try:
        element = soup.select_one(selector)
        if element:
            return element.get(attribute) if attribute else element.get_text(strip=True)
    except Exception as e:
        log_exception("Error occurred while processing element.", e, selector)
    return default

def return_longest_code(string):
    """
    returns the longest string used for sic and naics codes.
    Args:
        input_str (str): codes string 
    Returns:
        str: longest sic, naics code 
    """
    if string:
        str_list = string.split(',')
        str_list = [int(x) for x in str_list]
        str_list = sorted(str_list)
        return str(str_list[-1])
    else:
        return None


def get_valid_url(links, domain):
    for link in links:
        href = link.get("href")
        if href and domain in href:
            return href
    return None

def get_active_scrapers(conn):
    """
    Fetch scrapers with 'active' status from the database, ordered by priority.
    """
    query = "SELECT id, name FROM data_sources WHERE status = 'active' ORDER BY id"
    cur = conn.cursor()
    cur.execute(query)
    return cur.fetchall()



def connect_to_db__for_caching(dbname='source_scraper_results', user='postgres', password='Postgres#2024p', host='database-1.cqhgjpyjcue3.us-east-1.rds.amazonaws.com', port='5432'):
    """
    Connects to the PostgreSQL database using provided credentials.
    
    Args:
        dbname (str): Name of the database to connect to.
        user (str): Username for database authentication.
        password (str): Password for database authentication.
        host (str): Host where the database server is located.
        port (str): Port number where the database server is listening.

    Returns:
        conn: Database connection object if successful, None otherwise.
    """
    try:
        conn = psycopg2.connect(
            dbname=dbname,
            user=user,
            password=password,
            host=host,
            port=port
        )
        print("Connection established successfully.")
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None


def clean_newlines(data):
    """
    Recursively cleans newlines and excessive spaces from strings, lists, and dictionaries.
    
    Args:
        data (str | list | dict): The data structure to clean.
    
    Returns:
        str | list | dict: The cleaned data structure.
    """
    if isinstance(data, str):
        cleaned = re.sub(r"\s*\n\s*", " ", data)
        return re.sub(r"\s{2,}", " ", cleaned).strip()
    elif isinstance(data, list):
        return [clean_newlines(item) for item in data]
    elif isinstance(data, dict):
        return {key: clean_newlines(value) for key, value in data.items()}
    return data