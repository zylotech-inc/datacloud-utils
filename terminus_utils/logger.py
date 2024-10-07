import logging

# prod_env = get_env_variable("IS_PROD_ENV")
PROD_ENV = 'False'  # Change as per your requirement

if PROD_ENV.lower() == "true":
    logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.ERROR)
else:
    logging.basicConfig(format='%(asctime)s - {%(name)s:%(lineno)d} - %(levelname)s -%(message)s', level=logging.INFO)

logger = logging.getLogger(__name__)
