import os
from botocore.exceptions import ClientError
import boto3
import json

def get_env_variable(key, default=None):
    """Fetches an environment variable, returning a default value if not found."""
    return os.getenv(key, default)


def load_env_variables_from_file(file_path):
    """Loads environment variables from a .env file."""
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=file_path)


def get_zyte_secret(secret_name: str):

    secret_name = "Zyte_Api_key"
    region_name = "us-east-2"

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        raise e

    # Decrypts secret using the associated KMS key.
    secret = get_secret_value_response['SecretString']
    return json.loads(secret)
