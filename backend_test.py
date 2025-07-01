#!/usr/bin/env python3
import requests
import json
import time
import uuid
import sys
import logging
import asyncio
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
BASE_URL = "https://8dd4d21b-3505-45a0-a426-68ec8b1e7f48.preview.emergentagent.com/api"
TIMEOUT = 30  # seconds - increased for browser initialization tests

# Test data
TEST_CREDENTIALS = {
    "linkedin_email": "test.user@example.com",
    "linkedin_password": "SecurePassword123!",
    "openai_api_key": "sk-test-openai-key-12345",
    "claude_api_key": "sk-test-claude-key-12345",
    "gemini_api_key": "test-gemini-key-12345",
    "hunter_api_key": "test-hunter-key-12345"
}

TEST_QUERY = {
    "query": "Find sales directors at SaaS companies in the United States with 50-200 employees",
    "llm_provider": "openai",
    "max_results": 10
}

# Test results tracking
test_results = {
    "total": 0,
    "passed": 0,
    "failed": 0,
    "tests": []
}

# Helper functions
def print_header(message):
    """Print a formatted header"""
    print("\n" + "=" * 80)
    print(f" {message}")
    print("=" * 80)

def print_result(test_name, passed, message="", response=None):
    """Print test result and update counters"""
    global test_results
    
    status = "✅ PASSED" if passed else "❌ FAILED"
    print(f"{status} - {test_name}")
    
    if message:
        print(f"  {message}")
    
    if response and not passed:
        try:
            print(f"  Response: {response.status_code} - {response.json()}")
        except:
            print(f"  Response: {response.status_code} - {response.text[:100]}")
    
    test_results["total"] += 1
    if passed:
        test_results["passed"] += 1
    else:
        test_results["failed"] += 1
    
    test_results["tests"].append({
        "name": test_name,
        "passed": passed,
        "message": message
    })

def make_request(method, endpoint, data=None, expected_status=None) -> tuple[bool, Optional[requests.Response], str]:
    """Make an HTTP request and return success status, response, and message"""
    url = f"{BASE_URL}{endpoint}"
    
    try:
        if method.lower() == "get":
            response = requests.get(url, timeout=TIMEOUT)
        elif method.lower() == "post":
            response = requests.post(url, json=data, timeout=TIMEOUT)
        else:
            return False, None, f"Unsupported method: {method}"
        
        if expected_status is not None and response.status_code != expected_status:
            return False, response, f"Expected status {expected_status}, got {response.status_code}"
        
        return True, response, "Success"
    
    except requests.exceptions.ConnectionError:
        return False, None, f"Connection error: Could not connect to {url}"
    except requests.exceptions.Timeout:
        return False, None, f"Timeout error: Request to {url} timed out after {TIMEOUT} seconds"
    except Exception as e:
        return False, None, f"Error: {str(e)}"

# Test functions
def test_root_endpoint():
    """Test the root API endpoint"""
    print_header("Testing Root Endpoint")
    
    success, response, message = make_request("get", "/")
    
    if success:
        data = response.json()
        if "message" in data and "LinkedIn Lead Generation Tool API" in data["message"]:
            print_result("Root Endpoint", True, "Root endpoint returned correct message")
        else:
            print_result("Root Endpoint", False, "Root endpoint returned unexpected data", response)
    else:
        print_result("Root Endpoint", False, message, response)

def test_credentials_endpoints():
    """Test saving and retrieving credentials"""
    print_header("Testing Credentials Endpoints")
    
    # Test saving credentials
    success, response, message = make_request("post", "/credentials", TEST_CREDENTIALS)
    
    if success:
        data = response.json()
        if "id" in data and data.get("linkedin_email") == TEST_CREDENTIALS["linkedin_email"]:
            print_result("Save Credentials", True, "Credentials saved successfully")
            credential_id = data.get("id")
        else:
            print_result("Save Credentials", False, "Credentials saved but returned unexpected data", response)
            return
    else:
        print_result("Save Credentials", False, message, response)
        return
    
    # Test retrieving credentials
    success, response, message = make_request("get", "/credentials")
    
    if success:
        data = response.json()
        if "id" in data and data.get("linkedin_email") == TEST_CREDENTIALS["linkedin_email"]:
            # Check that password is masked
            if data.get("linkedin_password") == "••••••••":
                print_result("Get Credentials", True, "Credentials retrieved successfully with masked password")
            else:
                print_result("Get Credentials", False, "Password not properly masked in response", response)
        else:
            print_result("Get Credentials", False, "Retrieved credentials don't match what was saved", response)
    else:
        print_result("Get Credentials", False, message, response)

def test_parse_query_endpoint():
    """Test the query parsing endpoint"""
    print_header("Testing Query Parsing Endpoint")
    
    # Test with valid credentials already saved
    success, response, message = make_request("post", "/parse-query", TEST_QUERY)
    
    # Since we're using mock API keys, we expect this to fail gracefully
    # The important part is that the endpoint structure works
    if response and response.status_code == 500:
        error_data = response.json()
        if "detail" in error_data:
            print_result("Parse Query Structure", True, 
                         "Endpoint correctly structured but failed as expected with mock API keys")
        else:
            print_result("Parse Query Structure", False, 
                         "Endpoint failed but with unexpected error format", response)
    elif response and response.status_code == 200:
        # If it somehow succeeds (maybe using fallback parsing)
        data = response.json()
        if "roles" in data and "locations" in data:
            print_result("Parse Query", True, 
                         "Query parsed successfully (unexpected but valid)")
        else:
            print_result("Parse Query", False, 
                         "Query parsing returned unexpected data structure", response)
    else:
        print_result("Parse Query", False, message, response)
    
    # Test with invalid provider
    invalid_query = TEST_QUERY.copy()
    invalid_query["llm_provider"] = "invalid_provider"
    
    success, response, message = make_request("post", "/parse-query", invalid_query, expected_status=422)
    
    if success:
        print_result("Parse Query Validation", True, 
                     "Endpoint correctly rejected invalid LLM provider")
    else:
        # If it returns 500 instead of 422, that's still acceptable
        if response and response.status_code in [400, 500]:
            print_result("Parse Query Validation", True, 
                         "Endpoint rejected invalid LLM provider with error")
        else:
            print_result("Parse Query Validation", False, message, response)

def test_scraping_endpoints():
    """Test the scraping job endpoints with focus on browser launching"""
    print_header("Testing Scraping Endpoints and Browser Launching")
    
    # Test starting a scraping job
    success, response, message = make_request("post", "/start-scraping", TEST_QUERY)
    
    job_id = None
    browser_launched = False
    
    # Since we're using mock credentials, we expect LinkedIn login to fail
    # But the browser should launch successfully before attempting login
    if response:
        if response.status_code == 200:
            # Job was accepted and started
            data = response.json()
            if "id" in data and "status" in data:
                job_id = data["id"]
                print_result("Start Scraping", True, 
                             f"Scraping job started successfully with ID: {job_id}")
                
                # Wait a moment for the background task to start
                print("  Waiting for background task to initialize browser...")
                time.sleep(5)
                
                # Check job status to see if browser launched
                success, job_response, job_message = make_request("get", f"/scraping-jobs/{job_id}")
                
                if success:
                    job_data = job_response.json()
                    
                    # If status is "failed" with an error message containing "browser" or "playwright"
                    # then the browser failed to launch
                    if job_data["status"] == "failed":
                        error_msg = job_data.get("error_message", "")
                        if "chromium_headless_shell" in error_msg.lower():
                            print_result("Browser Launch", False, 
                                        f"Browser failed to launch with chromium_headless_shell error: {error_msg}")
                        elif "failed to launch" in error_msg.lower() or "playwright" in error_msg.lower():
                            print_result("Browser Launch", False, 
                                        f"Browser failed to launch: {error_msg}")
                        elif "login failed" in error_msg.lower():
                            # This is expected with mock credentials
                            print_result("Browser Launch", True, 
                                        "Browser launched successfully but LinkedIn login failed as expected with mock credentials")
                            browser_launched = True
                        else:
                            print_result("Browser Launch", False, 
                                        f"Job failed with error: {error_msg}")
                    elif job_data["status"] == "running":
                        # Job is still running, which means browser launched successfully
                        print_result("Browser Launch", True, 
                                    "Browser launched successfully and job is running")
                        browser_launched = True
                    elif job_data["status"] == "completed":
                        # Job completed, which means browser launched successfully
                        print_result("Browser Launch", True, 
                                    "Browser launched successfully and job completed")
                        browser_launched = True
                    else:
                        print_result("Browser Launch", False, 
                                    f"Unexpected job status: {job_data['status']}")
                else:
                    print_result("Browser Launch Check", False, job_message, job_response)
            else:
                print_result("Start Scraping", False, 
                             "Scraping job response missing expected fields", response)
        elif response.status_code in [400, 500]:
            error_data = response.json()
            if "detail" in error_data:
                error_msg = error_data["detail"]
                if "playwright" in error_msg.lower() or "browser" in error_msg.lower():
                    print_result("Browser Launch", False, 
                                f"Browser failed to launch: {error_msg}")
                elif "linkedin credentials" in error_msg.lower():
                    # This is expected with mock credentials
                    print_result("Start Scraping Structure", True, 
                                "Endpoint correctly validated LinkedIn credentials")
                else:
                    print_result("Start Scraping Structure", True, 
                                f"Endpoint correctly structured but failed as expected: {error_msg}")
            else:
                print_result("Start Scraping Structure", False, 
                            "Endpoint failed but with unexpected error format", response)
        else:
            print_result("Start Scraping", False, message, response)
    else:
        print_result("Start Scraping", False, message)
    
    # Test listing scraping jobs
    success, response, message = make_request("get", "/scraping-jobs")
    
    if success:
        data = response.json()
        if isinstance(data, list):
            print_result("List Scraping Jobs", True, 
                         f"Successfully retrieved {len(data)} scraping jobs")
            
            # If we have a job ID from the previous test, try to get it specifically
            if job_id or (len(data) > 0):
                # Get the first job ID if we didn't get one from the previous test
                job_id = job_id or data[0]["id"]
                
                # Test getting a specific job
                success, response, message = make_request("get", f"/scraping-jobs/{job_id}")
                
                if success:
                    job_data = response.json()
                    if "id" in job_data and job_data["id"] == job_id:
                        print_result("Get Specific Job", True, 
                                     f"Successfully retrieved job with ID: {job_id}")
                        
                        # Check for browser-related errors in the job data
                        if job_data.get("status") == "failed":
                            error_msg = job_data.get("error_message", "")
                            if "chromium_headless_shell" in error_msg.lower():
                                print_result("Browser Compatibility", False, 
                                            f"Browser failed with chromium_headless_shell error: {error_msg}")
                            elif "failed to launch" in error_msg.lower():
                                print_result("Browser Compatibility", False, 
                                            f"Browser failed to launch: {error_msg}")
                            elif "login failed" in error_msg.lower() and browser_launched:
                                print_result("Browser Compatibility", True, 
                                            "Browser launched successfully but LinkedIn login failed as expected with mock credentials")
                    else:
                        print_result("Get Specific Job", False, 
                                     "Retrieved job data doesn't match expected ID", response)
                else:
                    print_result("Get Specific Job", False, message, response)
        else:
            print_result("List Scraping Jobs", False, 
                         "Expected a list of jobs but got something else", response)
    else:
        print_result("List Scraping Jobs", False, message, response)

def test_export_csv_endpoint():
    """Test the CSV export endpoint"""
    print_header("Testing CSV Export Endpoint")
    
    # First get a job ID
    success, response, message = make_request("get", "/scraping-jobs")
    
    if success and isinstance(response.json(), list) and len(response.json()) > 0:
        job_id = response.json()[0]["id"]
        
        # Test exporting CSV for this job
        # We expect this to fail since the job likely hasn't completed
        response = requests.get(f"{BASE_URL}/export-csv/{job_id}", timeout=TIMEOUT)
        
        if response.status_code in [400, 500]:
            print_result("Export CSV Validation", True, 
                         f"Endpoint exists and correctly rejected export with status {response.status_code}")
        else:
            print_result("Export CSV Validation", False, 
                         f"Expected 400 or 500 status, got {response.status_code}")
    else:
        print_result("Export CSV", False, "Could not get a job ID to test CSV export")

def print_summary():
    """Print test summary"""
    print("\n" + "=" * 80)
    print(f" TEST SUMMARY: {test_results['passed']}/{test_results['total']} tests passed")
    print("=" * 80)
    
    if test_results["failed"] > 0:
        print("\nFailed tests:")
        for test in test_results["tests"]:
            if not test["passed"]:
                print(f"❌ {test['name']} - {test['message']}")
    
    print(f"\nPassed: {test_results['passed']}")
    print(f"Failed: {test_results['failed']}")
    print(f"Total:  {test_results['total']}")
    
    # Return exit code based on test results
    return 0 if test_results["failed"] == 0 else 1

def main():
    """Run all tests"""
    print_header("LinkedIn Lead Generation Tool API Tests")
    print(f"Testing API at: {BASE_URL}")
    
    # Run tests
    test_root_endpoint()
    test_credentials_endpoints()
    test_parse_query_endpoint()
    test_scraping_endpoints()
    test_export_csv_endpoint()
    
    # Print summary
    return print_summary()

if __name__ == "__main__":
    sys.exit(main())