import pytest
import unittest
from unittest.mock import patch, Mock
from requests.exceptions import Timeout
from bs4 import BeautifulSoup
from terminus_utils.utils import *



@patch('terminus_utils.utils.requests.get')
@patch('terminus_utils.utils.requests.post')
def test_proxy_api_response_success(mock_post, mock_get):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html></html>"
    mock_post.return_value = mock_response
    mock_get.return_value = mock_response
    status_code, response = proxy_api_response("http://test.com", is_httpresponse=True)
    
    assert status_code == 200
    assert response == mock_response


@patch('terminus_utils.utils.requests.get')
@patch('terminus_utils.utils.requests.post')
def test_proxy_api_response_failure(mock_post, mock_get):
    mock_post.side_effect = Timeout("Request timed out")
    mock_get.side_effect = Timeout("Request timed out")    
    status_code, response = proxy_api_response("http://test.com", is_httpresponse=True)    
    assert status_code is None
    assert response is None


@patch('terminus_utils.utils.requests.get')
@patch('terminus_utils.utils.requests.post')
def test_proxy_api_response_no_api_key(mock_post, mock_get):
    with patch('terminus_utils.utils.SMARTPROXY_ZYTE_API_KEY', None):
        with patch('terminus_utils.utils.ZYTE_API_KEY', None):
            status_code, response = proxy_api_response("http://test.com")    
    assert status_code is None
    assert response is None


@patch('terminus_utils.utils.proxy_api_response')
def test_retry_request_success(mock_proxy_api_response):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_proxy_api_response.return_value = (200, mock_response)
    status_code, response = retry_request("http://test.com", is_httpresponse=False, max_retry=3)
    assert status_code == 200
    assert response == mock_response


@patch('terminus_utils.utils.proxy_api_response')
def test_retry_request_with_retries(mock_proxy_api_response):
    mock_proxy_api_response.side_effect = [(429, None), (503, None), (520, None), (200, Mock())]
    status_code, response = retry_request("http://test.com", is_httpresponse=False, max_retry=3)
    assert status_code == 200
    assert response is not None


@patch('terminus_utils.utils.proxy_api_response')
def test_retry_request_exceed_max_retries(mock_proxy_api_response):
    mock_proxy_api_response.return_value = (503, None)
    status_code, response = retry_request("http://test.com", is_httpresponse=False, max_retry=3)
    assert status_code is None
    assert response is None


@patch('terminus_utils.utils.retry_request')
def test_send_request_with_proxy_success(mock_retry_request):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Type": "text/html"}
    mock_response.text = "<html></html>"
    mock_retry_request.return_value = (200, mock_response)
    status_code, soup = send_request_with_proxy("http://test.com", is_httpresponse=False)
    assert status_code == 200
    assert isinstance(soup, BeautifulSoup)


@patch('terminus_utils.utils.retry_request')
def test_send_request_with_proxy_json_response(mock_retry_request):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Type": "application/json"}
    mock_response.json.return_value = {"httpResponseBody": "PGh0bWw+PC9odG1sPg=="}
    mock_retry_request.return_value = (200, mock_response)
    status_code, soup = send_request_with_proxy("http://test.com", is_httpresponse=True)
    assert status_code == 200
    assert isinstance(soup, BeautifulSoup)


@patch('terminus_utils.utils.retry_request')
def test_send_request_with_proxy_failure(mock_retry_request):
    mock_retry_request.return_value = (503, None)
    status_code, soup = send_request_with_proxy("http://test.com", is_httpresponse=False)
    assert status_code == "error"
    assert soup == ""


@patch('terminus_utils.utils.retry_request')
def test_send_request_with_proxy_520_failure(mock_retry_request):
    mock_retry_request.return_value = (520, None)
    status_code, soup = send_request_with_proxy("http://test.com", is_httpresponse=False)
    assert status_code == "error"
    assert soup == ""