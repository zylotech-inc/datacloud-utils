import re
from ast import literal_eval
from datetime import date
from typing import List, Literal, Optional
from pydantic import (BaseModel, EmailStr, Field, HttpUrl, ValidationError,
                      field_validator, model_validator)


class CompanyData(BaseModel):
    """"Company data model"""
    PRIMARY_DOMAIN: str = Field(..., description="The primary domain associated with the entity")
    COMPANY_ID: Optional[str] = Field(None, description="Terminus Unique Account ID -(TAID) eg. TAID1124539292")
    NAME: str = Field(..., description="Name of the company")
    DBA_NAME: Optional[str] = Field(None, description="Doing business as name of the company")
    COMPANY_TYPE: Optional[str] = Field(None, description="Type of the company HQ/BR")
    PRIMARY_INDUSTRY: Optional[str] = Field(
        None, description="Primary industry of the company eg Professional Services")
    REVENUE: Optional[int] = Field(default=None, description="Total revenue of the company")
    INFERRED_REVENUE_FLAG: Optional[Literal['Y', 'N']] = Field(default='N')
    EMPLOYEES: Optional[int] = Field(None, description="Number of employees of the company")
    INFERRED_EMPLOYEES_FLAG: Optional[Literal['Y', 'N']] = Field(default='N')
    # SPECIALITIES_ARRAY: Optional[str] = Field(None, description="Company specialty or its area of expertise")
    SPECIALITIES_ARRAY: Optional[List[str]] = Field(None, description="Company specialty or its area of expertise")
    COMPANY_MANUAL_CURATION: Optional[Literal['Y', 'N']] = Field(default='N')
    COMPANY_DESCRIPTION: Optional[str] = Field(None, description="Description of the company")
    LOCATION_ID: Optional[str] = Field(None, description="Location ID of Company")
    COUNTRY_CD: str = Field(None, description="Company Country Code", min_length=2, max_length=2)
    ADDRESS_LINE1: Optional[str] = Field(None, description="Company HQ Street Details")
    ADDRESS_LINE2: Optional[str] = Field(None, description="Company HQ Street Details")
    CITY: Optional[str] = Field(None, description="Company HQ City")
    COUNTY: Optional[str] = Field(None, description="Company HQ County")
    STATE_PROVINCE: Optional[str] = Field(None, description="Company HQ State")
    POSTAL_CD: Optional[str] = Field(None, description="Company HQ Zip Code")
    PHONE: Optional[str] = Field(None, description="Company HQ Phone Number")
    LOCATION_MANUAL_CURATION: Optional[Literal['Y', 'N']] = Field(default='N')
    ALTERNATE_DOMAIN: Optional[str] = Field(None, description="Alternate Domain of Primary")
    LINKEDIN_URL: Optional[str] = Field(None, description="Linkedin url of Company")
    FACEBOOK_URL: Optional[str] = Field(None, description="Facebook url of Company")
    TWITTER_URL: Optional[str] = Field(None, description="Twitter url of Company")
    GICS: Optional[str] = Field(None, description="GICS Industry Classification Code")
    NAICS: Optional[str] = Field(None, description="NAICS Industry Classification Code")
    SIC: Optional[str] = Field(None, description="SIC Industry Classification Code")
    DELETE_FLAG: bool = Field(default=False)
    DELIVERY_DATE: date = Field(..., description="Date when the data was delivered")
    SOURCE_CD: str = Field(default='MANUAL', description="Source Code")
    SOURCE_ID: str = Field(..., description="SOURCE_ID with primary_domain and file_name")

    @field_validator("REVENUE", "EMPLOYEES", mode="before")
    def parse_int_field(cls, value):
        if isinstance(value, float):
            # Directly convert float to int
            return int(value)
        elif isinstance(value, str):
            # Check if it's a string representation of a float or int
            try:
                float_value = float(value)  # Convert to float first
                return int(float_value)    # Then convert to int
            except ValueError:
                raise ValueError(f"Value '{value}' is not a valid integer.")
        return value
    
    @field_validator("GICS", "NAICS","SIC", mode="before")
    def parse_gics_naics_sic_field(cls, value):
        if value in ['', None]:
            return None
        if isinstance(value, int) or isinstance(value, str):
            try:
                return str(value)
            except ValueError:
                raise ValueError(f"Value '{value}' is not a valid integer.")
        return value

    @field_validator('INFERRED_REVENUE_FLAG', 'INFERRED_EMPLOYEES_FLAG', 'COMPANY_MANUAL_CURATION',
                     'LOCATION_MANUAL_CURATION', mode='before')
    def convert_bool_to_text(cls, value):  # pylint: disable=no-self-argument
        # Convert True/False strings to Y/N
        if isinstance(value, bool):
            return 'Y' if value else 'N'
        if isinstance(value, str):
            if value.strip().upper() in {'Y', 'TRUE', 'YES'}:
                return 'Y'
            elif value.strip().upper() in {'N', 'FALSE', 'NO'}:
                return 'N'
        if value in (None, ''):
            return 'N'
        return value

    @field_validator('PRIMARY_DOMAIN')
    @classmethod
    def validate_primary_domain(cls, v):  # pylint: disable=no-self-argument
        global domain_pattern
        domain_pattern = r"^(?:[a-zA-Z0-9-]{1,63}\.)+[a-zA-Z]{2,}$"
        if not re.match(domain_pattern, v):
            raise ValueError(f'Invalid PRIMARY_DOMAIN:"{v}" format')
        return v

    @model_validator(mode="before")
    @classmethod
    def validate_country_code(cls, values):
        country_code = values.get('COUNTRY_CD')
        valid_country_codes = values.get('valid_country_codes', [])
        if country_code and country_code.upper() not in valid_country_codes:
            raise ValueError(f"Invalid COUNTRY_CD: {country_code}. Must be a valid 2-character country code.")
        return values

    @field_validator('LINKEDIN_URL', 'FACEBOOK_URL', 'TWITTER_URL', check_fields=False)
    def validate_url(cls, v):  # pylint: disable=no-self-argument
        if v and not re.match(r'https?://', v):
            raise ValueError(f"Invalid URL: {v}")
        return v

    @field_validator('ALTERNATE_DOMAIN', mode="before")
    @classmethod
    def validate_alternate_domains(cls, v):  # pylint: disable=no-self-argument
        if v.strip('"') in (None, ''):
            return None
        if not isinstance(v, str):
            raise ValueError(f"Invalid ALTERNATE_DOMAIN: {v}")
        if v:
            domains = v.strip('"').split(',')
            for domain in domains:
                if not re.match(domain_pattern, domain.strip()):
                    raise ValueError(f"Invalid domain in ALTERNATE_DOMAIN: {domain}")
        return v

    @field_validator('DELIVERY_DATE', mode='after')
    def parse_date(cls, value):  # pylint: disable=no-self-argument
        if isinstance(value, str):
            value = date.fromisoformat(value)
        if isinstance(value, date):
            return value.strftime('%Y-%m-%d')
        return value

    @field_validator('SPECIALITIES_ARRAY', mode="before")
    @classmethod
    def parse_specialities(cls, v):  # pylint: disable=no-self-argument
        # Parse string to list if it's in string format
        if isinstance(v, str):
            try:
                v = literal_eval(v)  # Safely parse the list string to a list
            except (ValueError, SyntaxError):
                raise ValueError("SPECIALITIES_ARRAY must be a list in string format, e.g., ['a', 'b', 'c']")
        return v
    # Validator to enforce None is converted to False
    @field_validator("DELETE_FLAG", mode="before")
    def set_default_delete_flag(cls, v):
        return v if v not in [None,''] else False


class LocationData(BaseModel):
    """Location data model"""
    PRIMARY_DOMAIN: str = Field(..., description="The primary domain associated with the entity")
    LOCATION_ID: Optional[str] = Field(None, description="Unique identifier for the location")
    COUNTRY_CD: str = Field(None, description="Company Branch Country Code")
    LOCATION_TYPE: str = Field(None, description="Branch eg.(BR,HQ)")
    ADDRESS_LINE1: Optional[str] = Field(None, description="Company Branch Street Details")
    ADDRESS_LINE2: Optional[str] = Field(None, description="Company Branch Street Details")
    CITY: Optional[str] = Field(None, description="Company Branch City")
    COUNTY: Optional[str] = Field(None, description="Company Branch County")
    STATE_PROVINCE: Optional[str] = Field(None, description="Company Branch State")
    POSTAL_CD: Optional[str] = Field(None, description="Company Branch Zip Code")
    PHONE: Optional[str] = Field(None, description="Company Branch Phone Number")
    REVENUE: Optional[int] = Field(None, description="Revenue of Branch in numeric format")
    INFERRED_REVENUE: Optional[Literal['Y', 'N']] = Field(
        default='N', description="INFERRED_REVNEUE_FLAG: Y for Yes, N for No")
    EMPLOYEES: Optional[int] = Field(None, description="Employee of Branch")
    INFERRED_EMPLOYEES: Optional[Literal['Y', 'N']] = Field(
        default='N',
        description="INFERRED_EMPLOYEES_FLAG: Y for Yes, N for No")
    MANUAL_CURATION: Optional[Literal['Y', 'N']] = Field(default='N')
    DELETE_FLAG: Optional[bool] = Field(default=False)
    DELIVERY_DATE: date = Field(..., description="Date when the data was delivered")
    SOURCE_CD: str = Field(default='MANUAL', description="Source Code")
    SOURCE_ID: str = Field(..., description="Stage ID with primary_domain and file_name")

    @field_validator("REVENUE", "EMPLOYEES", mode="before")
    def parse_int_field(cls, value):
        if isinstance(value, float) and value.is_integer():
            return int(value)
        return value

    @field_validator('INFERRED_REVENUE', 'INFERRED_EMPLOYEES', 'MANUAL_CURATION', mode='before')
    def convert_bool_to_text(cls, value):  # pylint: disable=no-self-argument
        if isinstance(value, bool):
            return 'Y' if value else 'N'
        # Convert True/False strings to Y/N
        if isinstance(value, str):
            if value.strip().upper() in {'Y', 'TRUE', 'YES'}:
                return 'Y'
            elif value.strip().upper() in {'N', 'FALSE', 'NO'}:
                return 'N'
        if value in (None, ''):
            return 'N'
        return value

    @field_validator('DELIVERY_DATE', mode='after')
    def parse_date(cls, value):  # pylint: disable=no-self-argument
        if isinstance(value, str):
            value = date.fromisoformat(value)
        if isinstance(value, date):
            return value.strftime('%Y-%m-%d')
        return value
    # Validator to enforce None is converted to False
    @field_validator("DELETE_FLAG", mode="before")
    def set_default_delete_flag(cls, v):
        return v if v not in [None,''] else False


class ContactData(BaseModel):
    """Contact data model"""
    PRIMARY_DOMAIN: str = Field(..., description="The primary domain associated with the entity")
    COMPANY_ID: Optional[str] = Field(None, description="Unique Account ID (T-CID) eg. TAID1124539292")
    CONTACT_ID: Optional[str] = Field(None, description="Unique Account ID (T-AID) eg. TCID1024617626")
    FIRST_NAME: str = Field(None, description="First name of the contact")
    LAST_NAME: str = Field(None, description="Last name of the contact")
    NAME_SUFFIX: Optional[str] = Field(None, description="Suffix for the name, e.g., Jr., Sr.")
    SALUTATION: Optional[str] = Field(None, description="Salutation for the contact, e.g., Mr., Mrs., Dr.")
    TITLE: str = Field(None, description="Job title of the contact")
    SENIORITY_LEVEL: str = Field(None, description="Seniority level of the contact, e.g., Manager, Director")
    ROLE_FUNCTION: str = Field(None, description="Functional role of the contact, e.g., Marketing, Sales")
    EMAIL: EmailStr = Field(None, description="Email address of the contact")
    PHONE: Optional[str] = Field(None, description="Phone number of the contact")
    ADDRESS_LINE1: Optional[str] = Field(None, description="Contact Street Details")
    ADDRESS_LINE2: Optional[str] = Field(None, description="Contact Street Details")
    CITY: Optional[str] = Field(None, description="Contact City Details")
    STATE_PROVINCE: Optional[str] = Field(None, description="Contact State/Province Details")
    COUNTY: Optional[str] = Field(None, description="Contact County Details")
    POSTAL_CD: Optional[str] = Field(None, description="Contact Postal Code Details")
    MANUAL_CURATION: Optional[Literal['Y', 'N']] = Field(
        'N', description="Tag Y for human-curated, Tag N for automated")
    COUNTRY_CD: Optional[str] = Field(None, description="Contact Country Details")
    LINKEDIN_URL: Optional[HttpUrl] = Field(None, description="LinkedIn profile URL of the contact")
    FACEBOOK_URL: Optional[HttpUrl] = Field(None, description="Facebook profile URL of the contact")
    TWITTER_URL: Optional[HttpUrl] = Field(None, description="Twitter profile URL of the contact")
    DELETE_FLAG: Optional[bool] = Field(default=False)
    DELIVERY_DATE: date = Field(..., description="Date when the data was delivered")
    SOURCE_CD: str = Field(default='MANUAL', description="Source Code")
    SOURCE_ID: str = Field(..., description="Stage ID with primary_domain and file_name")

    @field_validator('MANUAL_CURATION', mode='after')
    def convert_bool_to_text(cls, value):  # pylint: disable=no-self-argument
        if isinstance(value, bool):
            return 'Y' if value else 'N'
        # Convert True/False strings to Y/N
        if isinstance(value, str):
            if value.strip().upper() in {'Y', 'TRUE', 'YES'}:
                return 'Y'
            elif value.strip().upper() in {'N', 'FALSE', 'NO'}:
                return 'N'
        if value in (None, ''):
            return 'N'
        return value

    @field_validator('DELIVERY_DATE', mode='after')
    def parse_date(cls, value):  # pylint: disable=no-self-argument
        if isinstance(value, str):
            value = date.fromisoformat(value)
        if isinstance(value, date):
            return value.strftime('%Y-%m-%d')
        return value
    # Validator to enforce None is converted to False
    @field_validator("DELETE_FLAG", mode="before")
    def set_default_delete_flag(cls, v):
        return v if v not in [None,''] else False


class CompanyValidator:
    """Company Validator"""

    def __init__(self) -> None:
        self.valid_country_codes = List[str]

    @property
    def get_country_code(self) -> str:
        """Validate Country"""
        return self.valid_country_codes

    @get_country_code.setter
    def get_country_code(self, country_code_list: List[str]) -> None:
        self.valid_country_codes = country_code_list

    def create_company_data(self, data: dict) -> CompanyData:
        """Creates CompanyData instance after validating country codes"""
        # Convert the country codes into a list and assign to the class
        company_data = CompanyData(valid_country_codes=self.valid_country_codes, **data)
        return company_data


if __name__ == '__main__':
    # Simulating reading valid codes from S3
    valid_country_codes_from_s3 = ['IN', 'US', 'GB', 'AU', 'CA', 'NZ', 'IE', 'DE', 'FR', 'AD']

    # Instantiate with additional parameters
    comp_validator = CompanyValidator()
    comp_validator.get_country_code = valid_country_codes_from_s3

    record = {
        'SOURCE_ID': '1234567890', 'SOURCE_CD': 'MANUAL',
        'PRIMARY_DOMAIN': 'terminus.com', 'COMPANY_ID': None, 'NAME': 'terminus', 'DBA_NAME': None,
        'COMPANY_TYPE': None, 'PRIMARY_INDUSTRY': 'Health, Wellness And Fitness', 'REVENUE': '12323.5',
        'INFERRED_REVENUE_FLAG': '', 'EMPLOYEES': '24.0', 'INFERRED_EMPLOYEES_FLAG': 'False',
        'SPECIALITIES_ARRAY': ["a", "b", "c"],
        'COMPANY_MANUAL_CURATION': 'N', 'ALTERNATE_DOMAIN': '"cisco.com,terminus.com,jio.com"', 'COMPANY_DESCRIPTION': None,
        'LOCATION_ID': None, 'COUNTRY_CD': 'AD', 'ADDRESS_LINE1': '32 10 St Ds', 'ADDRESS_LINE2': None,
        'CITY': 'Les Escaldes', 'COUNTY': None, 'STATE_PROVINCE': 'Escaldes-Engordany', 'POSTAL_CD': 'AD700',
        'PHONE': '+376 800999', 'LOCATION_MANUAL_CURATION': 'YES',
        'LINKEDIN_URL': 'https://www.linkedin.com/company/caldea', 'FACEBOOK_URL': None, 'TWITTER_URL': None,
        'GICS': "67", 'NAICS': '', 'SIC': '7011', 'DELETE_FLAG': '', 'DELIVERY_DATE': '2024-10-23 00:00:00',
    }

    try:
        validated_record = comp_validator.create_company_data(record)
        print('########## MODEL DUMP ##########')
        print(validated_record.model_dump())
        print('########## JSON DUMP ##########')
        print(validated_record.model_dump_json())
    except ValidationError as verror:
        print('Unable to validate the fields:', str(verror))
    except ValueError as e:
        print(e)
