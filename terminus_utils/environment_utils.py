import json
import os

import boto3
from botocore.exceptions import ClientError


def get_env_variable(var_name: str, default_value=None):
    """Get the environment variable or return exception."""
    value = os.getenv(var_name, default_value)
    if value is None:
        raise ValueError(f"Environment variable {var_name} not set.")
    return value


def load_env_variables_from_file(file_path):
    """Loads environment variables from a .env file."""
    from dotenv import load_dotenv  # pylint: disable=import-outside-toplevel
    load_dotenv(dotenv_path=file_path)


def get_zyte_secret(secret_name: str):

    # secret_name = "Zyte_Api_key"
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
