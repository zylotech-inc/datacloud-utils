import os


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
