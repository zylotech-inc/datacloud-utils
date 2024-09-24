import os


def get_env_variable(key, default=None):
    """Fetches an environment variable, returning a default value if not found."""
    return os.getenv(key, default)


def load_env_variables_from_file(file_path):
    """Loads environment variables from a .env file."""
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=file_path)
