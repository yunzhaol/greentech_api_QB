#!/usr/bin/env python3
"""
QuickBooks Online API Client
Handles all QuickBooks Online API interactions for the synchronizer.
"""
import os
import requests
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv
from oauth import get_auth_header

load_dotenv()

# Configuration
REALM_ID = os.getenv("QBO_REALM_ID")
QBO_MODE = os.getenv("QBO_MODE", "sandbox")

def get_base_url():
    """Returns the QuickBooks API base URL based on mode"""
    if QBO_MODE == "production":
        return "https://quickbooks.api.intuit.com"
    return "https://sandbox-quickbooks.api.intuit.com"

class QuickBooksAPIError(Exception):
    """Custom exception for QuickBooks API errors"""
    def __init__(self, message: str, status_code: int = None, response_data: dict = None):
        self.message = message
        self.status_code = status_code
        self.response_data = response_data
        super().__init__(self.message)

def _make_request(method: str, endpoint: str, data: dict = None, params: dict = None) -> dict:
    """
    Makes authenticated request to QuickBooks API.
    
    Args:
        method: HTTP method (GET, POST, etc.)
        endpoint: API endpoint path
        data: JSON payload for POST/PUT
        params: Query parameters
        
    Returns:
        Response JSON
        
    Raises:
        QuickBooksAPIError on failure
    """
    if not REALM_ID:
        raise QuickBooksAPIError("QBO_REALM_ID not set in environment")
    
    url = f"{get_base_url()}/v3/company/{REALM_ID}/{endpoint}"
    
    headers = {
        **get_auth_header(),
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            json=data,
            params=params,
            timeout=30
        )
        
        if response.status_code >= 400:
            error_data = response.json() if response.text else {}
            fault = error_data.get("Fault", {})
            error_msg = fault.get("Error", [{}])[0].get("Message", response.text)
            
            raise QuickBooksAPIError(
                message=error_msg,
                status_code=response.status_code,
                response_data=error_data
            )
        
        return response.json()
    
    except requests.exceptions.RequestException as e:
        raise QuickBooksAPIError(f"Network error: {str(e)}")

# ==================== Company Info ====================

def get_company_info() -> Dict:
    """
    Gets company information to verify connection.
    
    Returns:
        Company info dict with CompanyName, Id, etc.
    """
    response = _make_request("GET", "companyinfo/1")
    return response.get("CompanyInfo", {})

# ==================== Estimate Operations ====================

def query_estimates(start_position: int = 1, max_results: int = 100) -> Tuple[List[Dict], int]:
    """
    Queries estimates from QuickBooks with pagination support.
    
    Args:
        start_position: 1-based starting position for the result set
        max_results: Maximum number of estimates to fetch (QuickBooks caps at 1000)
        
    Returns:
        Tuple containing:
            - List of estimate dicts
            - Total count reported by QuickBooks for the query
    """
    if max_results < 1 or max_results > 1000:
        raise ValueError("max_results must be between 1 and 1000")
    
    query = (
        "SELECT * FROM Estimate "
        f"STARTPOSITION {start_position} "
        f"MAXRESULTS {max_results}"
    )
    response = _make_request("GET", "query", params={"query": query})
    query_response = response.get("QueryResponse", {})
    estimates = query_response.get("Estimate", [])
    total_count = query_response.get("totalCount", len(estimates))
    return estimates, total_count

def list_all_estimates(batch_size: int = 100) -> List[Dict]:
    """
    Retrieves all estimates by iterating through paginated query results.
    
    Args:
        batch_size: Number of records to request per API call
        
    Returns:
        List of all estimate dicts available to the authenticated company
    """
    if batch_size < 1 or batch_size > 1000:
        raise ValueError("batch_size must be between 1 and 1000")
    
    all_estimates: List[Dict] = []
    start_position = 1
    
    while True:
        batch, _ = query_estimates(start_position=start_position, max_results=batch_size)
        if not batch:
            break
        all_estimates.extend(batch)
        start_position += len(batch)
        if len(batch) < batch_size:
            break
    
    return all_estimates

# ==================== Invoice Operations ====================

def query_invoices(start_position: int = 1, max_results: int = 100) -> Tuple[List[Dict], int]:
    """
    Queries invoices from QuickBooks with pagination support.
    
    Args:
        start_position: 1-based starting position for the result set
        max_results: Maximum number of invoices to fetch (QuickBooks caps at 1000)
        
    Returns:
        Tuple containing:
            - List of invoice dicts
            - Total count reported by QuickBooks for the query
    """
    if max_results < 1 or max_results > 1000:
        raise ValueError("max_results must be between 1 and 1000")
    
    query = (
        "SELECT * FROM Invoice "
        f"STARTPOSITION {start_position} "
        f"MAXRESULTS {max_results}"
    )
    response = _make_request("GET", "query", params={"query": query})
    query_response = response.get("QueryResponse", {})
    invoices = query_response.get("Invoice", [])
    total_count = query_response.get("totalCount", len(invoices))
    return invoices, total_count

def list_all_invoices(batch_size: int = 100) -> List[Dict]:
    """
    Retrieves all invoices by iterating through paginated query results.
    
    Args:
        batch_size: Number of records to request per API call
        
    Returns:
        List of all invoice dicts available to the authenticated company
    """
    if batch_size < 1 or batch_size > 1000:
        raise ValueError("batch_size must be between 1 and 1000")
    
    all_invoices: List[Dict] = []
    start_position = 1
    
    while True:
        batch, _ = query_invoices(start_position=start_position, max_results=batch_size)
        if not batch:
            break
        all_invoices.extend(batch)
        start_position += len(batch)
        if len(batch) < batch_size:
            break
    
    return all_invoices

# ==================== Customer Operations ====================

def get_customer(customer_id: str) -> Optional[Dict]:
    """
    Fetches a single customer by ID from QuickBooks.
    
    Args:
        customer_id: QuickBooks customer ID
        
    Returns:
        Customer dict or None if not found
    """
    try:
        response = _make_request("GET", f"customer/{customer_id}")
        return response.get("Customer", {})
    except QuickBooksAPIError as e:
        if e.status_code == 404:
            return None
        raise

def query_customers(start_position: int = 1, max_results: int = 100) -> Tuple[List[Dict], int]:
    """
    Queries customers from QuickBooks with pagination support.
    
    Args:
        start_position: 1-based starting position for the result set
        max_results: Maximum number of customers to fetch (QuickBooks caps at 1000)
        
    Returns:
        Tuple containing:
            - List of customer dicts
            - Total count reported by QuickBooks for the query
    """
    if max_results < 1 or max_results > 1000:
        raise ValueError("max_results must be between 1 and 1000")
    
    query = (
        "SELECT * FROM Customer "
        f"STARTPOSITION {start_position} "
        f"MAXRESULTS {max_results}"
    )
    response = _make_request("GET", "query", params={"query": query})
    query_response = response.get("QueryResponse", {})
    customers = query_response.get("Customer", [])
    total_count = query_response.get("totalCount", len(customers))
    return customers, total_count

def list_all_customers(batch_size: int = 100) -> List[Dict]:
    """
    Retrieves all customers by iterating through paginated query results.
    
    Args:
        batch_size: Number of records to request per API call
        
    Returns:
        List of all customer dicts available to the authenticated company
    """
    if batch_size < 1 or batch_size > 1000:
        raise ValueError("batch_size must be between 1 and 1000")
    
    all_customers: List[Dict] = []
    start_position = 1
    
    while True:
        batch, _ = query_customers(start_position=start_position, max_results=batch_size)
        if not batch:
            break
        all_customers.extend(batch)
        start_position += len(batch)
        if len(batch) < batch_size:
            break
    
    return all_customers