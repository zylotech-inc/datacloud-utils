from api_utils import extract_domain
import boto3


def upload_html_to_s3(html_content, aws_access_key, aws_secret_key, website: str, source: str):
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
                      aws_access_key_id=aws_access_key,
                      aws_secret_access_key=aws_secret_key,
                      region_name='us-east-1')
    domain = extract_domain(website)
    bucket_name = 'terminus-raw-html'
    file_key = f'{domain}/{source}/raw.html'
    s3.put_object(Bucket=bucket_name, Key=file_key, Body=html_content)
    s3_uri = f's3://{bucket_name}/{domain}/{source}/raw.html'
    return s3_uri