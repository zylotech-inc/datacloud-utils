import unittest
from unittest.mock import patch
from terminus_utils.api_utils import (
    get_clean_website,
    prepare_search_url,
    transform_employee_revenue_value
)


class TestGetCleanWebsite(unittest.TestCase):

    def test_remove_www(self):
        self.assertEqual(get_clean_website("www.example.com"), "example.com")

    def test_remove_https(self):
        self.assertEqual(get_clean_website("https://example.com"), "example.com")

    def test_remove_http(self):
        self.assertEqual(get_clean_website("http://example.com"), "example.com")

    def test_remove_all_prefixes(self):
        self.assertEqual(get_clean_website("https://www.example.com"), "example.com")

    def test_no_change_needed(self):
        self.assertEqual(get_clean_website("example.com"), "example.com")

    def test_empty_string(self):
        self.assertEqual(get_clean_website(""), "")

    def test_multiple_www(self):
        self.assertEqual(get_clean_website("www.www.example.com"), "example.com")

    def test_subdomain(self):
        self.assertEqual(get_clean_website("https://subdomain.example.com"), "subdomain.example.com")

    def test_trailing_slash(self):
        self.assertEqual(get_clean_website("https://www.example.com/"), "example.com/")


class TestPrepareSearchUrl(unittest.TestCase):

    @patch('utils.api_utils.get_clean_website')
    def test_prepare_search_url_owler(self, mock_get_clean_website):
        mock_get_clean_website.return_value = "example.com"
        result = prepare_search_url("example.com", "owler.com")
        expected = "https://www.google.com/search?q=owler.com+%2B+%22example.com%22"
        self.assertEqual(result, expected)

    @patch('utils.api_utils.get_clean_website')
    def test_prepare_search_url_cbinsights(self, mock_get_clean_website):
        mock_get_clean_website.return_value = "example.com"
        result = prepare_search_url("example.com", "cbinsights.com")
        expected = "https://www.google.com/search?q=site%3Acbinsights.com+AND+%22example.com%22"
        self.assertEqual(result, expected)

    @patch('utils.api_utils.get_clean_website')
    def test_prepare_search_url_rocketreach(self, mock_get_clean_website):
        mock_get_clean_website.return_value = "example.com"
        result = prepare_search_url("example.com", "rocketreach.co")
        expected = "https://www.google.com/search?q=site%3A+rocketreach.co+%2B+%22example.com%22+%22+%2B+revenue%22"
        self.assertEqual(result, expected)

    @patch('utils.api_utils.get_clean_website')
    def test_prepare_search_url_other_source(self, mock_get_clean_website):
        mock_get_clean_website.return_value = "example.com"
        result = prepare_search_url("example.com", "othersource.com")
        expected = "https://www.google.com/search?q=+%22example.com%22+othersource.com"
        self.assertEqual(result, expected)

    @patch('utils.api_utils.get_clean_website')
    def test_prepare_search_url_empty_domain(self, mock_get_clean_website):
        mock_get_clean_website.return_value = ""
        result = prepare_search_url("", "owler.com")
        expected = "https://www.google.com/search?q=owler.com+%2B+%22%22"
        self.assertEqual(result, expected)

    @patch('utils.api_utils.get_clean_website')
    def test_prepare_search_url_special_characters(self, mock_get_clean_website):
        mock_get_clean_website.return_value = "example!@#$%^&*.com"
        result = prepare_search_url("example!@#$%^&*.com", "aeroleads.com")
        expected = "https://www.google.com/search?q=aeroleads.com+%2B+%22example%21%40%23%24%25%5E%26%2A.com%22"
        self.assertEqual(result, expected)


class TestTransformEmployeeRevenueValue(unittest.TestCase):

    def test_million_abbreviation(self):
        self.assertEqual(transform_employee_revenue_value("$5M"), (5000000, False))

    def test_billion_abbreviation(self):
        self.assertEqual(transform_employee_revenue_value("2.5B"), (2500000000, False))

    def test_trillion_abbreviation(self):
        self.assertEqual(transform_employee_revenue_value("1.2T"), (1200000000000, False))

    def test_thousand_full_word(self):
        self.assertEqual(transform_employee_revenue_value("500 k"), (500000, False))

    def test_mixed_case(self):
        self.assertEqual(transform_employee_revenue_value("10K"), (10000, False))

    def test_range_with_different_units(self):
        self.assertEqual(transform_employee_revenue_value("500M-1.5B"), (1000000000, True))

    def test_less_than_symbol(self):
        self.assertEqual(transform_employee_revenue_value("<100M"), (50000000, True))

    def test_greater_than_symbol(self):
        self.assertEqual(transform_employee_revenue_value(">1B"), (1000000000, True))

    def test_decimal_values(self):
        self.assertEqual(transform_employee_revenue_value("3.14M"), (3140000, False))

    def test_whitespace_handling(self):
        self.assertEqual(transform_employee_revenue_value("  5  million  "), (5000000, False))

    def test_invalid_input(self):
        self.assertEqual(transform_employee_revenue_value("invalid"), (None, False))

    def test_empty_string(self):
        self.assertEqual(transform_employee_revenue_value(""), (None, None))

    def test_none_input(self):
        self.assertEqual(transform_employee_revenue_value(None), (None, None))

    def test_complex_range(self):
        self.assertEqual(transform_employee_revenue_value("50k-100M"), (50025000, True))

    def test_mixed_symbols_and_words(self):
        self.assertEqual(transform_employee_revenue_value(">500 million"), (500000000, True))
