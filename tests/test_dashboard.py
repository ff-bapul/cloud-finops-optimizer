import pytest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest

@pytest.fixture
def mock_requests(mocker):
    mock_get = mocker.patch("requests.get")
    mock_post = mocker.patch("requests.post")
    return mock_get, mock_post

def test_dashboard_renders_empty_state(mock_requests):
    import streamlit as st
    st.cache_data.clear()
    
    mock_get, mock_post = mock_requests
    
    # Setup mock responses for empty state
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = []

    at = AppTest.from_file("dashboard/app.py").run()
    
    assert not at.exception
    assert at.title[0].value == "☁️ Cloud Cost Optimizer & Remediation"
    
    # Check metrics
    metrics = at.metric
    assert metrics[0].value == "0"  # Total Findings
    assert metrics[1].value == "$0.00"  # Potential Savings
    assert metrics[2].value == "0"  # High Severity
    assert metrics[3].value == "0"  # Active Rules

def test_dashboard_renders_with_data(mock_requests):
    import streamlit as st
    st.cache_data.clear()
    
    mock_get, mock_post = mock_requests
    
    # Setup mock responses with data
    def side_effect_get(url, **kwargs):
        class MockResponse:
            def __init__(self, json_data, status_code=200):
                self.json_data = json_data
                self.status_code = status_code
            def json(self):
                return self.json_data

        if "/findings" in url:
            return MockResponse([{"id": 1, "status": "Open", "potential_savings": 100.5, "rule_id": 1, "provider": "AWS"}])
        elif "/rules" in url:
            return MockResponse([{"id": 1, "severity": "High", "resource_type": "EC2", "enabled": True, "provider": "AWS"}])
        elif "/remediation" in url:
            return MockResponse([{"finding_id": 1, "status": "Open", "command": "echo test"}])
        return MockResponse([])
        
    mock_get.side_effect = side_effect_get

    at = AppTest.from_file("dashboard/app.py").run()
    assert not at.exception
    
    # Metrics
    metrics = at.metric
    assert metrics[0].value == "1"  # Total Findings
    assert metrics[1].value == "$100.50"  # Potential Savings
    assert metrics[2].value == "1"  # High Severity

def test_dashboard_ingest_data(mock_requests):
    import streamlit as st
    st.cache_data.clear()
    mock_get, mock_post = mock_requests
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = []
    
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"message": "Success"}

    at = AppTest.from_file("dashboard/app.py").run()
    
    # Simulate Analyze button click
    if len(at.button) > 0:
        for b in at.button:
            if "Analyze" in b.label:
                b.click().run()
                break

    assert not at.exception
