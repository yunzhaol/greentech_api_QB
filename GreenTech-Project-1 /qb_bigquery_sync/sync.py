#!/usr/bin/env python3
"""
QuickBooks to BigQuery Synchronizer

Fetches all QuickBooks estimates and invoices, uploading them to BigQuery in normalized format:
- quotes: Quote/estimate header information
- invoices: Invoice header information
- lines: Line items for each quote/invoice
- customers: Customer information (deduplicated)
"""
import argparse
import json
import sys
import re
from typing import List, Dict, Optional, Set, Tuple
from datetime import datetime

from quickbooks_client import (
    get_company_info,
    list_all_estimates,
    list_all_invoices,
    get_customer,
    QuickBooksAPIError,
)


def extract_quote_data(estimate: Dict) -> Dict:
    """
    Extracts quote-level data from QuickBooks estimate.
    
    Args:
        estimate: Full QuickBooks estimate object
        
    Returns:
        Dict with quote fields
    """
    customer_ref = estimate.get("CustomerRef", {})
    
    return {
        "quote_id": estimate.get("Id"),
        "doc_number": estimate.get("DocNumber"),
        "txn_date": estimate.get("TxnDate"),
        "total_amt": float(estimate.get("TotalAmt", 0)) if estimate.get("TotalAmt") else None,
        "subtotal": float(estimate.get("SubTotalAmt", 0)) if estimate.get("SubTotalAmt") else None,
        "txn_status": estimate.get("TxnStatus"),
        "customer_id": customer_ref.get("value"),
        "customer_name": customer_ref.get("name"),
        "currency": estimate.get("CurrencyRef", {}).get("value"),
        "sync_token": estimate.get("SyncToken"),
        "meta_data_create_time": estimate.get("MetaData", {}).get("CreateTime"),
        "meta_data_last_updated_time": estimate.get("MetaData", {}).get("LastUpdatedTime"),
        "customer_memo": estimate.get("CustomerMemo", {}).get("value"),
        "private_note": estimate.get("PrivateNote"),
        "email_status": estimate.get("EmailStatus"),
        "apply_tax_after_discount": estimate.get("ApplyTaxAfterDiscount", False),
        "print_status": estimate.get("PrintStatus"),
        "expiration_date": estimate.get("ExpirationDate"),
        "accepted_date": estimate.get("AcceptedDate"),
        "declined_date": estimate.get("DeclinedDate"),
        "revision_date": estimate.get("RevisionDate"),
        "revision_number": estimate.get("RevisionNumber"),
        "exchange_rate": float(estimate.get("ExchangeRate", 1)) if estimate.get("ExchangeRate") else 1.0,
    }


def extract_line_data(estimate: Dict) -> List[Dict]:
    """
    Extracts line items from QuickBooks estimate.
    
    Args:
        estimate: Full QuickBooks estimate object
        
    Returns:
        List of line item dicts
    """
    quote_id = estimate.get("Id")
    lines = estimate.get("Line", [])
    line_items = []
    
    # Track line number for cases where LineNum is missing
    line_counter = 1
    
    for line in lines:
        # Skip subtotal lines (DetailType == "SubTotalLineDetail")
        if line.get("DetailType") == "SubTotalLineDetail":
            continue
        
        # Use provided LineNum, or assign sequential number if missing
        line_num = line.get("LineNum")
        if line_num is None:
            line_num = line_counter
            line_counter += 1
        else:
            # If we have a valid line_num, increment counter to be higher than it
            # to avoid conflicts if we encounter NULL later
            line_counter = max(line_counter, int(line_num) + 1)
            
        line_data = {
            "quote_id": quote_id,
            "line_num": line_num,
            "description": line.get("Description"),
            "amount": float(line.get("Amount", 0)) if line.get("Amount") else None,
            "detail_type": line.get("DetailType"),
        }
        
        # Extract SalesItemLineDetail if present
        sales_detail = line.get("SalesItemLineDetail", {})
        if sales_detail:
            line_data["item_ref_value"] = sales_detail.get("ItemRef", {}).get("value")
            line_data["item_ref_name"] = sales_detail.get("ItemRef", {}).get("name")
            line_data["qty"] = float(sales_detail.get("Qty", 0)) if sales_detail.get("Qty") else None
            line_data["unit_price"] = float(sales_detail.get("UnitPrice", 0)) if sales_detail.get("UnitPrice") else None
            line_data["tax_code_ref_value"] = sales_detail.get("TaxCodeRef", {}).get("value")
        
        # Extract GroupLineDetail if present
        group_detail = line.get("GroupLineDetail", {})
        if group_detail:
            line_data["group_item_ref_value"] = group_detail.get("GroupItemRef", {}).get("value")
            line_data["group_item_ref_name"] = group_detail.get("GroupItemRef", {}).get("name")
        
        # Extract DiscountLineDetail if present
        discount_detail = line.get("DiscountLineDetail", {})
        if discount_detail:
            line_data["discount_percent"] = float(discount_detail.get("DiscountPercent", 0)) if discount_detail.get("DiscountPercent") else None
            line_data["discount_account_ref_value"] = discount_detail.get("DiscountAccountRef", {}).get("value")
            line_data["discount_class_ref_value"] = discount_detail.get("ClassRef", {}).get("value")
        
        line_items.append(line_data)
    
    return line_items


def extract_invoice_data(invoice: Dict) -> Dict:
    """
    Extracts invoice-level data from QuickBooks invoice.
    
    Args:
        invoice: Full QuickBooks invoice object
        
    Returns:
        Dict with invoice fields
    """
    customer_ref = invoice.get("CustomerRef", {})
    
    return {
        "invoice_id": invoice.get("Id"),
        "doc_number": invoice.get("DocNumber"),
        "txn_date": invoice.get("TxnDate"),
        "due_date": invoice.get("DueDate"),
        "total_amt": float(invoice.get("TotalAmt", 0)) if invoice.get("TotalAmt") else None,
        "subtotal": float(invoice.get("SubTotalAmt", 0)) if invoice.get("SubTotalAmt") else None,
        "balance": float(invoice.get("Balance", 0)) if invoice.get("Balance") else None,
        "txn_status": invoice.get("TxnStatus"),
        "customer_id": customer_ref.get("value"),
        "customer_name": customer_ref.get("name"),
        "currency": invoice.get("CurrencyRef", {}).get("value"),
        "sync_token": invoice.get("SyncToken"),
        "meta_data_create_time": invoice.get("MetaData", {}).get("CreateTime"),
        "meta_data_last_updated_time": invoice.get("MetaData", {}).get("LastUpdatedTime"),
        "customer_memo": invoice.get("CustomerMemo", {}).get("value"),
        "private_note": invoice.get("PrivateNote"),
        "email_status": invoice.get("EmailStatus"),
        "apply_tax_after_discount": invoice.get("ApplyTaxAfterDiscount", False),
        "print_status": invoice.get("PrintStatus"),
        "exchange_rate": float(invoice.get("ExchangeRate", 1)) if invoice.get("ExchangeRate") else 1.0,
        "sales_rep_ref_value": invoice.get("SalesRepRef", {}).get("value"),
        "sales_rep_ref_name": invoice.get("SalesRepRef", {}).get("name"),
        "ship_date": invoice.get("ShipDate"),
        "tracking_num": invoice.get("TrackingNum"),
        "ar_account_ref_value": invoice.get("ARAccountRef", {}).get("value"),
        "ar_account_ref_name": invoice.get("ARAccountRef", {}).get("name"),
    }


def extract_invoice_line_data(invoice: Dict) -> List[Dict]:
    """
    Extracts line items from QuickBooks invoice.
    
    Args:
        invoice: Full QuickBooks invoice object
        
    Returns:
        List of line item dicts
    """
    invoice_id = invoice.get("Id")
    lines = invoice.get("Line", [])
    line_items = []
    
    # Track line number for cases where LineNum is missing
    line_counter = 1
    
    for line in lines:
        # Skip subtotal lines
        if line.get("DetailType") == "SubTotalLineDetail":
            continue
        
        # Use provided LineNum, or assign sequential number if missing
        line_num = line.get("LineNum")
        if line_num is None:
            line_num = line_counter
            line_counter += 1
        else:
            # If we have a valid line_num, increment counter to be higher than it
            # to avoid conflicts if we encounter NULL later
            line_counter = max(line_counter, int(line_num) + 1)
            
        line_data = {
            "invoice_id": invoice_id,
            "line_num": line_num,
            "description": line.get("Description"),
            "amount": float(line.get("Amount", 0)) if line.get("Amount") else None,
            "detail_type": line.get("DetailType"),
        }
        
        # Extract SalesItemLineDetail if present
        sales_detail = line.get("SalesItemLineDetail", {})
        if sales_detail:
            line_data["item_ref_value"] = sales_detail.get("ItemRef", {}).get("value")
            line_data["item_ref_name"] = sales_detail.get("ItemRef", {}).get("name")
            line_data["qty"] = float(sales_detail.get("Qty", 0)) if sales_detail.get("Qty") else None
            line_data["unit_price"] = float(sales_detail.get("UnitPrice", 0)) if sales_detail.get("UnitPrice") else None
            line_data["tax_code_ref_value"] = sales_detail.get("TaxCodeRef", {}).get("value")
        
        # Extract GroupLineDetail if present
        group_detail = line.get("GroupLineDetail", {})
        if group_detail:
            line_data["group_item_ref_value"] = group_detail.get("GroupItemRef", {}).get("value")
            line_data["group_item_ref_name"] = group_detail.get("GroupItemRef", {}).get("name")
        
        # Extract DiscountLineDetail if present
        discount_detail = line.get("DiscountLineDetail", {})
        if discount_detail:
            line_data["discount_percent"] = float(discount_detail.get("DiscountPercent", 0)) if discount_detail.get("DiscountPercent") else None
            line_data["discount_account_ref_value"] = discount_detail.get("DiscountAccountRef", {}).get("value")
            line_data["discount_class_ref_value"] = discount_detail.get("ClassRef", {}).get("value")
        
        line_items.append(line_data)
    
    return line_items


def extract_environmental_impact(customer_memo: Optional[str]) -> Optional[Dict]:
    """
    Extracts environmental impact data from customer_memo field.
    
    Expected format: "Reference: GT-TEST-001 | Environmental impact: 2 tree(s), 0.25 tons CO₂, 35L water saved."
    
    Args:
        customer_memo: Customer memo string from quote
        
    Returns:
        Dict with quote_id, trees, tons_c02, water_saved, or None if no environmental impact found
    """
    if not customer_memo:
        return None
    
    # Look for "Environmental impact:" pattern
    env_pattern = r"Environmental impact:\s*([^|]+)"
    match = re.search(env_pattern, customer_memo, re.IGNORECASE)
    if not match:
        return None
    
    env_text = match.group(1).strip()
    
    # Extract trees: number before "tree(s)" or "tree"
    trees_match = re.search(r"(\d+(?:\.\d+)?)\s*tree(?:s)?", env_text, re.IGNORECASE)
    trees = float(trees_match.group(1)) if trees_match else None
    
    # Extract CO2: number before "tons CO₂" or "tons CO2" (handle both regular and subscript ₂)
    co2_match = re.search(r"(\d+(?:\.\d+)?)\s*tons?\s*CO[₂2]", env_text, re.IGNORECASE)
    tons_c02 = float(co2_match.group(1)) if co2_match else None
    
    # Extract water saved: number before "L water saved" or "L water"
    water_match = re.search(r"(\d+(?:\.\d+)?)\s*L\s*water", env_text, re.IGNORECASE)
    water_saved = float(water_match.group(1)) if water_match else None
    
    # Only return if at least one value was found
    if trees is not None or tons_c02 is not None or water_saved is not None:
        return {
            "trees": trees,
            "tons_c02": tons_c02,
            "water_saved": water_saved,
        }
    
    return None


def extract_environmental_impact_from_quote(quote: Dict) -> Optional[Dict]:
    """
    Extracts environmental impact data from a quote's customer_memo.
    
    Args:
        quote: Quote dict with quote_id and customer_memo
        
    Returns:
        Dict with quote_id, trees, tons_c02, water_saved, or None if no environmental impact
    """
    quote_id = quote.get("quote_id")
    customer_memo = quote.get("customer_memo")
    
    if not quote_id or not customer_memo:
        return None
    
    env_data = extract_environmental_impact(customer_memo)
    if not env_data:
        return None
    
    return {
        "quote_id": str(quote_id),
        "trees": env_data.get("trees"),
        "tons_c02": env_data.get("tons_c02"),
        "water_saved": env_data.get("water_saved"),
    }


def extract_customer_data_from_transaction(transaction: Dict, customer_cache: Optional[Dict[str, Dict]] = None) -> Optional[Dict]:
    """
    Extracts customer data from QuickBooks transaction (estimate or invoice).
    Fetches full customer details from Customer API if customer_id is found.
    
    Args:
        transaction: Full QuickBooks transaction object (estimate or invoice)
        customer_cache: Optional dict to cache customer data by ID to avoid duplicate API calls
        
    Returns:
        Customer dict with full details or None if no customer
    """
    customer_ref = transaction.get("CustomerRef", {})
    customer_id = customer_ref.get("value")
    
    if not customer_id:
        return None
    
    customer_id_str = str(customer_id)
    
    # Check cache first
    if customer_cache and customer_id_str in customer_cache:
        return customer_cache[customer_id_str]
    
    # Fetch full customer details from QuickBooks API
    customer_data = None
    try:
        customer_obj = get_customer(customer_id_str)
        if customer_obj:
            # Extract email
            primary_email = customer_obj.get("PrimaryEmailAddr", {})
            email = primary_email.get("Address") if primary_email else None
            
            # Extract phone
            primary_phone = customer_obj.get("PrimaryPhone", {})
            phone = primary_phone.get("FreeFormNumber") if primary_phone else None
            
            # Extract address (BillAddr is typically the billing address)
            bill_addr = customer_obj.get("BillAddr", {})
            if bill_addr:
                address_line1 = bill_addr.get("Line1")
                address_line2 = bill_addr.get("Line2")
                city = bill_addr.get("City")
                country = bill_addr.get("Country")
                country_sub_division_code = bill_addr.get("CountrySubDivisionCode")  # State/Province
                postal_code = bill_addr.get("PostalCode")
                
                # Combine address components
                address_parts = []
                if address_line1:
                    address_parts.append(address_line1)
                if address_line2:
                    address_parts.append(address_line2)
                if city:
                    address_parts.append(city)
                if country_sub_division_code:
                    address_parts.append(country_sub_division_code)
                if postal_code:
                    address_parts.append(postal_code)
                if country:
                    address_parts.append(country)
                
                address = ", ".join(address_parts) if address_parts else None
            else:
                address = None
            
            customer_data = {
                "customer_id": customer_id_str,
                "customer_name": customer_obj.get("DisplayName") or customer_ref.get("name"),
                "email": email,
                "phone": phone,
                "address": address,
            }
    except Exception as e:
        # If customer fetch fails, fall back to basic data from transaction
        print(f"  Warning: Could not fetch customer details for {customer_id_str}: {e}")
        customer_data = {
            "customer_id": customer_id_str,
            "customer_name": customer_ref.get("name"),
            "email": None,
            "phone": None,
            "address": None,
        }
    
    # Cache the result if cache is provided
    if customer_cache and customer_data:
        customer_cache[customer_id_str] = customer_data
    
    return customer_data


def transform_estimates(estimates: List[Dict], customer_cache: Optional[Dict[str, Dict]] = None) -> tuple[List[Dict], List[Dict], List[Dict], List[Dict]]:
    """
    Transforms QuickBooks estimates into normalized tables.
    
    Args:
        estimates: List of QuickBooks estimate objects
        customer_cache: Optional dict to cache customer data by ID
        
    Returns:
        Tuple of (quotes, lines, customers, environmental_impact) lists
    """
    quotes = []
    lines = []
    customers_dict = {}  # Use dict to deduplicate customers by ID
    seen_customer_ids: Set[str] = set()
    environmental_impact = []
    
    # Initialize cache if not provided
    if customer_cache is None:
        customer_cache = {}
    
    for estimate in estimates:
        # Extract quote data
        quote = extract_quote_data(estimate)
        quotes.append(quote)
        
        # Extract line items
        line_items = extract_line_data(estimate)
        lines.extend(line_items)
        
        # Extract customer data (deduplicate)
        customer = extract_customer_data_from_transaction(estimate, customer_cache)
        if customer and customer["customer_id"] not in seen_customer_ids:
            customers_dict[customer["customer_id"]] = customer
            seen_customer_ids.add(customer["customer_id"])
        
        # Extract environmental impact data
        env_data = extract_environmental_impact_from_quote(quote)
        if env_data:
            environmental_impact.append(env_data)
    
    customers = list(customers_dict.values())
    
    return quotes, lines, customers, environmental_impact


def transform_invoices(invoices: List[Dict], existing_customers: Set[str], customer_cache: Optional[Dict[str, Dict]] = None) -> tuple[List[Dict], List[Dict], List[Dict]]:
    """
    Transforms QuickBooks invoices into normalized tables.
    
    Args:
        invoices: List of QuickBooks invoice objects
        existing_customers: Set of customer IDs already seen (to avoid duplicates)
        customer_cache: Optional dict to cache customer data by ID
        
    Returns:
        Tuple of (invoices, invoice_lines, new_customers) lists
    """
    invoice_list = []
    invoice_lines = []
    customers_dict = {}  # Use dict to deduplicate customers by ID
    
    # Initialize cache if not provided
    if customer_cache is None:
        customer_cache = {}
    
    for invoice in invoices:
        # Extract invoice data
        invoice_data = extract_invoice_data(invoice)
        invoice_list.append(invoice_data)
        
        # Extract line items
        line_items = extract_invoice_line_data(invoice)
        invoice_lines.extend(line_items)
        
        # Extract customer data (deduplicate)
        customer = extract_customer_data_from_transaction(invoice, customer_cache)
        if customer and customer["customer_id"] not in existing_customers:
            customers_dict[customer["customer_id"]] = customer
            existing_customers.add(customer["customer_id"])
    
    new_customers = list(customers_dict.values())
    
    return invoice_list, invoice_lines, new_customers


def create_bigquery_schemas():
    """
    Returns BigQuery table schemas for quotes, invoices, lines, and customers.
    
    Returns:
        Tuple of (quotes_schema, invoices_schema, lines_schema, customers_schema)
    """
    from google.cloud import bigquery
    
    quotes_schema = [
        bigquery.SchemaField("quote_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("doc_number", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("txn_date", "DATE", mode="NULLABLE"),
        bigquery.SchemaField("total_amt", "FLOAT", mode="NULLABLE"),
        bigquery.SchemaField("subtotal", "FLOAT", mode="NULLABLE"),
        bigquery.SchemaField("txn_status", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("customer_id", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("customer_name", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("currency", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("sync_token", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("meta_data_create_time", "TIMESTAMP", mode="NULLABLE"),
        bigquery.SchemaField("meta_data_last_updated_time", "TIMESTAMP", mode="NULLABLE"),
        bigquery.SchemaField("customer_memo", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("private_note", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("email_status", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("apply_tax_after_discount", "BOOLEAN", mode="NULLABLE"),
        bigquery.SchemaField("print_status", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("expiration_date", "DATE", mode="NULLABLE"),
        bigquery.SchemaField("accepted_date", "DATE", mode="NULLABLE"),
        bigquery.SchemaField("declined_date", "DATE", mode="NULLABLE"),
        bigquery.SchemaField("revision_date", "DATE", mode="NULLABLE"),
        bigquery.SchemaField("revision_number", "INTEGER", mode="NULLABLE"),
        bigquery.SchemaField("exchange_rate", "FLOAT", mode="NULLABLE"),
    ]
    
    invoices_schema = [
        bigquery.SchemaField("invoice_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("doc_number", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("txn_date", "DATE", mode="NULLABLE"),
        bigquery.SchemaField("due_date", "DATE", mode="NULLABLE"),
        bigquery.SchemaField("total_amt", "FLOAT", mode="NULLABLE"),
        bigquery.SchemaField("subtotal", "FLOAT", mode="NULLABLE"),
        bigquery.SchemaField("balance", "FLOAT", mode="NULLABLE"),
        bigquery.SchemaField("txn_status", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("customer_id", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("customer_name", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("currency", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("sync_token", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("meta_data_create_time", "TIMESTAMP", mode="NULLABLE"),
        bigquery.SchemaField("meta_data_last_updated_time", "TIMESTAMP", mode="NULLABLE"),
        bigquery.SchemaField("customer_memo", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("private_note", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("email_status", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("apply_tax_after_discount", "BOOLEAN", mode="NULLABLE"),
        bigquery.SchemaField("print_status", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("exchange_rate", "FLOAT", mode="NULLABLE"),
        bigquery.SchemaField("sales_rep_ref_value", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("sales_rep_ref_name", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("ship_date", "DATE", mode="NULLABLE"),
        bigquery.SchemaField("tracking_num", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("ar_account_ref_value", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("ar_account_ref_name", "STRING", mode="NULLABLE"),
    ]
    
    quote_lines_schema = [
        bigquery.SchemaField("quote_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("line_num", "INTEGER", mode="NULLABLE"),
        bigquery.SchemaField("description", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("amount", "FLOAT", mode="NULLABLE"),
        bigquery.SchemaField("detail_type", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("item_ref_value", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("item_ref_name", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("qty", "FLOAT", mode="NULLABLE"),
        bigquery.SchemaField("unit_price", "FLOAT", mode="NULLABLE"),
        bigquery.SchemaField("tax_code_ref_value", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("group_item_ref_value", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("group_item_ref_name", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("discount_percent", "FLOAT", mode="NULLABLE"),
        bigquery.SchemaField("discount_account_ref_value", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("discount_class_ref_value", "STRING", mode="NULLABLE"),
    ]
    
    invoice_lines_schema = [
        bigquery.SchemaField("invoice_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("line_num", "INTEGER", mode="NULLABLE"),
        bigquery.SchemaField("description", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("amount", "FLOAT", mode="NULLABLE"),
        bigquery.SchemaField("detail_type", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("item_ref_value", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("item_ref_name", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("qty", "FLOAT", mode="NULLABLE"),
        bigquery.SchemaField("unit_price", "FLOAT", mode="NULLABLE"),
        bigquery.SchemaField("tax_code_ref_value", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("group_item_ref_value", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("group_item_ref_name", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("discount_percent", "FLOAT", mode="NULLABLE"),
        bigquery.SchemaField("discount_account_ref_value", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("discount_class_ref_value", "STRING", mode="NULLABLE"),
    ]
    
    customers_schema = [
        bigquery.SchemaField("customer_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("customer_name", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("email", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("phone", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("address", "STRING", mode="NULLABLE"),
    ]
    
    environmental_impact_schema = [
        bigquery.SchemaField("quote_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("trees", "FLOAT", mode="NULLABLE"),
        bigquery.SchemaField("tons_c02", "FLOAT", mode="NULLABLE"),
        bigquery.SchemaField("water_saved", "FLOAT", mode="NULLABLE"),
    ]
    
    return quotes_schema, invoices_schema, quote_lines_schema, invoice_lines_schema, customers_schema, environmental_impact_schema


def parse_timestamp(timestamp_str: Optional[str]) -> Optional[str]:
    """Converts QuickBooks timestamp to BigQuery TIMESTAMP format."""
    if not timestamp_str:
        return None
    try:
        # QuickBooks timestamps are typically ISO format
        dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        return dt.isoformat()
    except:
        return None


def parse_date(date_str: Optional[str]) -> Optional[str]:
    """Converts QuickBooks date string to BigQuery DATE format (YYYY-MM-DD)."""
    if not date_str:
        return None
    # QuickBooks dates are typically YYYY-MM-DD
    return date_str


def _upsert_customers(
    client,
    table_ref: str,
    customers: List[Dict],
    project_id: str,
    dataset_id: str,
) -> None:
    """
    Inserts only new customers (avoids duplicates by checking existing IDs first).
    This approach avoids streaming buffer issues with UPDATE/DELETE operations.
    """
    from google.cloud import bigquery
    
    if not customers:
        return
    
    # Get existing customer IDs from BigQuery (always cast to STRING for comparison)
    try:
        # Cast to STRING regardless of table schema type to handle both INTEGER and STRING tables
        query = f"SELECT DISTINCT CAST(customer_id AS STRING) as customer_id FROM `{table_ref}`"
        query_job = client.query(query)
        existing_ids = {str(row.customer_id).strip() for row in query_job.result() if row.customer_id is not None}
        print(f"  Found {len(existing_ids)} existing customer(s) in BigQuery")
    except Exception as e:
        # Table might be empty or not exist yet
        existing_ids = set()
        print(f"  No existing customers found (table may be empty): {e}")
    
    # Get the existing table schema first to determine the correct type
    try:
        table = client.get_table(table_ref)
        customer_id_field = next((f for f in table.schema if f.name == "customer_id"), None)
        customer_id_is_int = customer_id_field and customer_id_field.field_type == "INTEGER"
    except Exception:
        # Table doesn't exist, use STRING (our default)
        customer_id_is_int = False
        table = None
    
    # Filter to only new customers and deduplicate within the batch
    seen_in_batch = set()
    new_customers = []
    for c in customers:
        customer_id_str = str(c.get("customer_id", "")).strip()
        # Skip empty IDs and check both existing and batch duplicates
        if customer_id_str and customer_id_str not in existing_ids and customer_id_str not in seen_in_batch:
            new_customers.append(c)
            seen_in_batch.add(customer_id_str)
    
    if len(customers) != len(new_customers):
        print(f"  Deduplicated: {len(customers)} input -> {len(new_customers)} new (skipped {len(customers) - len(new_customers)} duplicates)")
    
    # Convert customer_id to match the existing schema type
    valid_customers = []
    for customer in new_customers:
        try:
            if customer_id_is_int:
                customer["customer_id"] = int(customer.get("customer_id", 0) or 0)
            else:
                customer["customer_id"] = str(customer.get("customer_id", ""))
            valid_customers.append(customer)
        except (ValueError, TypeError):
            # Skip if can't convert
            continue
    
    if not valid_customers:
        print(f"  All {len(customers)} customer(s) already exist or invalid, skipping insert")
        return
    
    # Insert only new customers
    # Use batch load to avoid streaming buffer issues
    if table:
        # Use the existing table's schema to ensure type compatibility
        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
            schema=table.schema,  # Use existing schema to prevent type mismatches
            schema_update_options=[],  # Don't allow schema updates
        )
    else:
        # Table doesn't exist, use our default schema (STRING)
        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
            schema=create_bigquery_schemas()[4],  # Use customers schema
        )
    
    job = client.load_table_from_json(valid_customers, table_ref, job_config=job_config)
    job.result()  # Wait for job to complete
    
    print(f"  Inserted {len(valid_customers)} new customer(s) (skipped {len(customers) - len(valid_customers)} existing)")


def _upsert_quotes(
    client,
    table_ref: str,
    quotes: List[Dict],
    project_id: str,
    dataset_id: str,
) -> None:
    """
    Inserts only new quotes (avoids duplicates by checking existing IDs first).
    This approach avoids streaming buffer issues with UPDATE/DELETE operations.
    """
    from google.cloud import bigquery
    
    if not quotes:
        return
    
    # Get existing quote IDs from BigQuery
    try:
        query = f"SELECT CAST(quote_id AS STRING) as quote_id FROM `{table_ref}`"
        query_job = client.query(query)
        existing_ids = {row.quote_id for row in query_job.result()}
        print(f"  Found {len(existing_ids)} existing quote(s) in BigQuery")
    except Exception as e:
        # Table might be empty or not exist yet
        existing_ids = set()
        print(f"  No existing quotes found (table may be empty): {e}")
    
    # Filter to only new quotes
    new_quotes = [
        q for q in quotes 
        if str(q.get("quote_id", "")) not in existing_ids
    ]
    
    if not new_quotes:
        print(f"  All {len(quotes)} quote(s) already exist, skipping insert")
        return
    
    # Check for quotes with missing or empty quote_id
    invalid_quotes = [q for q in new_quotes if not q.get("quote_id")]
    if invalid_quotes:
        print(f"  ⚠️  Warning: {len(invalid_quotes)} quote(s) have missing or empty quote_id, skipping them")
        new_quotes = [q for q in new_quotes if q.get("quote_id")]
        if not new_quotes:
            print(f"  No valid quotes to insert after filtering")
            return
    
    # Ensure IDs are strings
    for quote in new_quotes:
        quote["quote_id"] = str(quote.get("quote_id", ""))
        if quote.get("customer_id"):
            quote["customer_id"] = str(quote["customer_id"])
    
    # Insert only new quotes using batch load
    # Get the existing table schema to ensure type compatibility
    try:
        table = client.get_table(table_ref)
        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
            schema=table.schema,  # Use existing schema to prevent type mismatches
            schema_update_options=[],  # Don't allow schema updates
            ignore_unknown_values=False,
        )
    except Exception:
        # Table doesn't exist, use our default schema
        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
            schema=create_bigquery_schemas()[0],  # Use quotes schema
            ignore_unknown_values=False,
        )
    
    try:
        job = client.load_table_from_json(new_quotes, table_ref, job_config=job_config)
        job.result()  # Wait for job to complete
        if job.errors:
            print(f"⚠️  BigQuery load warnings/errors: {job.errors}")
            if len(job.errors) > 0:
                raise RuntimeError(f"BigQuery load failed with errors: {job.errors}")
    except Exception as e:
        error_msg = str(e)
        if hasattr(e, 'errors') and e.errors:
            print(f"❌ Detailed BigQuery errors:")
            for error in e.errors:
                print(f"   {error}")
        elif "errors[] collection" in error_msg:
            print(f"❌ BigQuery encountered data errors. Check schema compatibility.")
        print(f"❌ Failed to insert quotes. First quote_id: {new_quotes[0].get('quote_id') if new_quotes else 'N/A'}")
        raise
    
    print(f"  Inserted {len(new_quotes)} new quote(s) (skipped {len(quotes) - len(new_quotes)} existing)")


def _upsert_invoices(
    client,
    table_ref: str,
    invoices: List[Dict],
    project_id: str,
    dataset_id: str,
) -> None:
    """
    Inserts only new invoices (avoids duplicates by checking existing IDs first).
    This approach avoids streaming buffer issues with UPDATE/DELETE operations.
    """
    from google.cloud import bigquery
    
    if not invoices:
        return
    
    # Get existing invoice IDs from BigQuery
    try:
        query = f"SELECT CAST(invoice_id AS STRING) as invoice_id FROM `{table_ref}`"
        query_job = client.query(query)
        existing_ids = {row.invoice_id for row in query_job.result()}
    except Exception:
        # Table might be empty or not exist yet
        existing_ids = set()
    
    # Filter to only new invoices
    new_invoices = [
        i for i in invoices 
        if str(i.get("invoice_id", "")) not in existing_ids
    ]
    
    if not new_invoices:
        print(f"  All {len(invoices)} invoice(s) already exist, skipping insert")
        return
    
    # Ensure IDs are strings
    for invoice in new_invoices:
        invoice["invoice_id"] = str(invoice.get("invoice_id", ""))
        if invoice.get("customer_id"):
            invoice["customer_id"] = str(invoice["customer_id"])
    
    # Insert only new invoices using batch load
    # Get the existing table schema to ensure type compatibility
    try:
        table = client.get_table(table_ref)
        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
            schema=table.schema,  # Use existing schema to prevent type mismatches
            schema_update_options=[],  # Don't allow schema updates
        )
    except Exception:
        # Table doesn't exist, use our default schema
        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
            schema=create_bigquery_schemas()[1],  # Use invoices schema
        )
    
    job = client.load_table_from_json(new_invoices, table_ref, job_config=job_config)
    job.result()  # Wait for job to complete
    
    print(f"  Inserted {len(new_invoices)} new invoice(s) (skipped {len(invoices) - len(new_invoices)} existing)")


def _upsert_quote_lines(
    client,
    table_ref: str,
    lines: List[Dict],
    project_id: str,
    dataset_id: str,
) -> None:
    """
    Inserts only new quote lines (avoids duplicates by checking existing quote_id + line_num combinations).
    This approach avoids streaming buffer issues with DELETE operations.
    """
    from google.cloud import bigquery
    
    if not lines:
        return
    
    # Get existing line keys (quote_id + line_num) from BigQuery
    try:
        query = f"""
        SELECT 
          CAST(quote_id AS STRING) as quote_id,
          line_num
        FROM `{table_ref}`
        WHERE line_num IS NOT NULL
        """
        query_job = client.query(query)
        existing_keys = {
            (row.quote_id, row.line_num) 
            for row in query_job.result()
        }
    except Exception:
        # Table might be empty or not exist yet
        existing_keys = set()
    
    # Filter to only new lines
    new_lines = [
        l for l in lines
        if (str(l.get("quote_id", "")), l.get("line_num")) not in existing_keys
    ]
    
    if not new_lines:
        print(f"  All {len(lines)} quote line item(s) already exist, skipping insert")
        return
    
    # Ensure quote_id is string
    for line in new_lines:
        line["quote_id"] = str(line.get("quote_id", ""))
    
    # Insert only new lines using batch load
    try:
        table = client.get_table(table_ref)
        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
            schema=table.schema,
            schema_update_options=[],
            ignore_unknown_values=False,
        )
    except Exception:
        # Table doesn't exist, use our default schema
        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
            schema=create_bigquery_schemas()[2],  # Use quote_lines schema
            ignore_unknown_values=False,
        )
    
    try:
        job = client.load_table_from_json(new_lines, table_ref, job_config=job_config)
        job.result()
        if job.errors:
            print(f"⚠️  BigQuery load warnings/errors: {job.errors}")
            if len(job.errors) > 0:
                raise RuntimeError(f"BigQuery load failed with errors: {job.errors}")
    except Exception as e:
        error_msg = str(e)
        if hasattr(e, 'errors') and e.errors:
            print(f"❌ Detailed BigQuery errors:")
            for error in e.errors:
                print(f"   {error}")
        elif "errors[] collection" in error_msg:
            print(f"❌ BigQuery encountered data errors. Check schema compatibility.")
        raise
    
    print(f"  Inserted {len(new_lines)} new quote line item(s) (skipped {len(lines) - len(new_lines)} existing)")


def _upsert_invoice_lines(
    client,
    table_ref: str,
    lines: List[Dict],
    project_id: str,
    dataset_id: str,
) -> None:
    """
    Inserts only new invoice lines (avoids duplicates by checking existing invoice_id + line_num combinations).
    This approach avoids streaming buffer issues with DELETE operations.
    """
    from google.cloud import bigquery
    
    if not lines:
        return
    
    # Get existing line keys (invoice_id + line_num) from BigQuery
    try:
        query = f"""
        SELECT 
          CAST(invoice_id AS STRING) as invoice_id,
          line_num
        FROM `{table_ref}`
        WHERE line_num IS NOT NULL
        """
        query_job = client.query(query)
        existing_keys = {
            (row.invoice_id, row.line_num) 
            for row in query_job.result()
        }
    except Exception:
        # Table might be empty or not exist yet
        existing_keys = set()
    
    # Filter to only new lines
    new_lines = [
        l for l in lines
        if (str(l.get("invoice_id", "")), l.get("line_num")) not in existing_keys
    ]
    
    if not new_lines:
        print(f"  All {len(lines)} invoice line item(s) already exist, skipping insert")
        return
    
    # Ensure invoice_id is string
    for line in new_lines:
        line["invoice_id"] = str(line.get("invoice_id", ""))
    
    # Insert only new lines using batch load
    try:
        table = client.get_table(table_ref)
        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
            schema=table.schema,
            schema_update_options=[],
            ignore_unknown_values=False,
        )
    except Exception:
        # Table doesn't exist, use our default schema
        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
            schema=create_bigquery_schemas()[3],  # Use invoice_lines schema
            ignore_unknown_values=False,
        )
    
    try:
        job = client.load_table_from_json(new_lines, table_ref, job_config=job_config)
        job.result()
        if job.errors:
            print(f"⚠️  BigQuery load warnings/errors: {job.errors}")
            if len(job.errors) > 0:
                raise RuntimeError(f"BigQuery load failed with errors: {job.errors}")
    except Exception as e:
        error_msg = str(e)
        if hasattr(e, 'errors') and e.errors:
            print(f"❌ Detailed BigQuery errors:")
            for error in e.errors:
                print(f"   {error}")
        elif "errors[] collection" in error_msg:
            print(f"❌ BigQuery encountered data errors. Check schema compatibility.")
        raise
    
    print(f"  Inserted {len(new_lines)} new invoice line item(s) (skipped {len(lines) - len(new_lines)} existing)")


def _upsert_environmental_impact(
    client,
    table_ref: str,
    environmental_impact: List[Dict],
    project_id: str,
    dataset_id: str,
) -> None:
    """
    Inserts only new environmental impact records (avoids duplicates by checking existing quote_id).
    This approach avoids streaming buffer issues with DELETE operations.
    """
    from google.cloud import bigquery
    
    if not environmental_impact:
        return
    
    # Get existing quote_ids from BigQuery
    try:
        query = f"SELECT CAST(quote_id AS STRING) as quote_id FROM `{table_ref}`"
        query_job = client.query(query)
        existing_ids = {row.quote_id for row in query_job.result()}
    except Exception:
        # Table might be empty or not exist yet
        existing_ids = set()
    
    # Filter to only new records
    new_records = [
        r for r in environmental_impact
        if str(r.get("quote_id", "")) not in existing_ids
    ]
    
    if not new_records:
        print(f"  All {len(environmental_impact)} environmental impact record(s) already exist, skipping insert")
        return
    
    # Ensure quote_id is string
    for record in new_records:
        record["quote_id"] = str(record.get("quote_id", ""))
    
    # Insert only new records using batch load
    try:
        table = client.get_table(table_ref)
        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
            schema=table.schema,
            schema_update_options=[],
            ignore_unknown_values=False,
        )
    except Exception:
        # Table doesn't exist, use our default schema
        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
            schema=create_bigquery_schemas()[5],  # Use environmental_impact schema
            ignore_unknown_values=False,
        )
    
    try:
        job = client.load_table_from_json(new_records, table_ref, job_config=job_config)
        job.result()
        if job.errors:
            print(f"⚠️  BigQuery load warnings/errors: {job.errors}")
            if len(job.errors) > 0:
                raise RuntimeError(f"BigQuery load failed with errors: {job.errors}")
    except Exception as e:
        error_msg = str(e)
        if hasattr(e, 'errors') and e.errors:
            print(f"❌ Detailed BigQuery errors:")
            for error in e.errors:
                print(f"   {error}")
        elif "errors[] collection" in error_msg:
            print(f"❌ BigQuery encountered data errors. Check schema compatibility.")
        raise
    
    print(f"  Inserted {len(new_records)} new environmental impact record(s) (skipped {len(environmental_impact) - len(new_records)} existing)")


def normalize_invoice_row(invoice: Dict) -> Dict:
    """Normalizes invoice data for BigQuery insertion."""
    normalized = invoice.copy()
    
    # Convert timestamps
    if normalized.get("meta_data_create_time"):
        normalized["meta_data_create_time"] = parse_timestamp(normalized["meta_data_create_time"])
    if normalized.get("meta_data_last_updated_time"):
        normalized["meta_data_last_updated_time"] = parse_timestamp(normalized["meta_data_last_updated_time"])
    
    # Convert dates
    normalized["txn_date"] = parse_date(normalized.get("txn_date"))
    normalized["due_date"] = parse_date(normalized.get("due_date"))
    normalized["ship_date"] = parse_date(normalized.get("ship_date"))
    
    return normalized


def normalize_quote_row(quote: Dict) -> Dict:
    """Normalizes quote data for BigQuery insertion."""
    normalized = quote.copy()
    
    # Convert timestamps
    if normalized.get("meta_data_create_time"):
        normalized["meta_data_create_time"] = parse_timestamp(normalized["meta_data_create_time"])
    if normalized.get("meta_data_last_updated_time"):
        normalized["meta_data_last_updated_time"] = parse_timestamp(normalized["meta_data_last_updated_time"])
    
    # Convert dates
    normalized["txn_date"] = parse_date(normalized.get("txn_date"))
    normalized["expiration_date"] = parse_date(normalized.get("expiration_date"))
    normalized["accepted_date"] = parse_date(normalized.get("accepted_date"))
    normalized["declined_date"] = parse_date(normalized.get("declined_date"))
    normalized["revision_date"] = parse_date(normalized.get("revision_date"))
    
    return normalized


def load_into_bigquery(
    estimates: List[Dict],
    invoices: List[Dict],
    project_id: Optional[str],
    dataset_id: str,
    create_tables: bool,
) -> None:
    """
    Loads estimates and invoices into BigQuery normalized tables.
    
    Args:
        estimates: List of estimate dictionaries from QuickBooks
        invoices: List of invoice dictionaries from QuickBooks
        project_id: BigQuery project ID (optional, uses default if not provided)
        dataset_id: BigQuery dataset ID
        create_tables: If True, creates the tables if they don't exist
    """
    try:
        from google.cloud import bigquery
    except ImportError as exc:
        raise RuntimeError(
            "google-cloud-bigquery is not installed. "
            "Install with: pip install google-cloud-bigquery"
        ) from exc
    
    client = bigquery.Client(project=project_id) if project_id else bigquery.Client()
    target_project = project_id or client.project
    
    # Use a shared customer cache to avoid duplicate API calls
    customer_cache: Dict[str, Dict] = {}
    
    # Transform estimates into normalized tables
    print("Transforming estimates into normalized format...")
    quotes, quote_lines, customers, environmental_impact = transform_estimates(estimates, customer_cache)
    
    # Track customer IDs to avoid duplicates when processing invoices
    seen_customer_ids = {c["customer_id"] for c in customers}
    
    # Transform invoices into normalized tables
    print("Transforming invoices into normalized format...")
    invoice_list, invoice_lines, new_customers = transform_invoices(invoices, seen_customer_ids, customer_cache)
    
    # Combine and deduplicate customers (by customer_id)
    customers_dict = {}
    for c in customers:
        customers_dict[c["customer_id"]] = c
    for c in new_customers:
        customers_dict[c["customer_id"]] = c
    all_customers = list(customers_dict.values())
    
    print(f"  - {len(quotes)} quote(s)")
    print(f"  - {len(invoice_list)} invoice(s)")
    print(f"  - {len(quote_lines)} quote line item(s)")
    print(f"  - {len(invoice_lines)} invoice line item(s)")
    print(f"  - {len(all_customers)} unique customer(s)")
    print(f"  - {len(environmental_impact)} environmental impact record(s)")
    print()
    
    # Create tables if needed
    if create_tables:
        quotes_schema, invoices_schema, quote_lines_schema, invoice_lines_schema, customers_schema, environmental_impact_schema = create_bigquery_schemas()
        
        quotes_table_ref = f"{target_project}.{dataset_id}.quotes"
        invoices_table_ref = f"{target_project}.{dataset_id}.invoices"
        quote_lines_table_ref = f"{target_project}.{dataset_id}.quote_lines"
        invoice_lines_table_ref = f"{target_project}.{dataset_id}.invoice_lines"
        customers_table_ref = f"{target_project}.{dataset_id}.customers"
        environmental_impact_table_ref = f"{target_project}.{dataset_id}.environmental_impact"
        
        quotes_table = bigquery.Table(quotes_table_ref, schema=quotes_schema)
        invoices_table = bigquery.Table(invoices_table_ref, schema=invoices_schema)
        quote_lines_table = bigquery.Table(quote_lines_table_ref, schema=quote_lines_schema)
        invoice_lines_table = bigquery.Table(invoice_lines_table_ref, schema=invoice_lines_schema)
        customers_table = bigquery.Table(customers_table_ref, schema=customers_schema)
        environmental_impact_table = bigquery.Table(environmental_impact_table_ref, schema=environmental_impact_schema)
        
        client.create_table(quotes_table, exists_ok=True)
        client.create_table(invoices_table, exists_ok=True)
        client.create_table(quote_lines_table, exists_ok=True)
        client.create_table(invoice_lines_table, exists_ok=True)
        client.create_table(customers_table, exists_ok=True)
        client.create_table(environmental_impact_table, exists_ok=True)
        
        print(f"BigQuery tables ensured:")
        print(f"  - {quotes_table_ref}")
        print(f"  - {invoices_table_ref}")
        print(f"  - {quote_lines_table_ref}")
        print(f"  - {invoice_lines_table_ref}")
        print(f"  - {customers_table_ref}")
        print(f"  - {environmental_impact_table_ref}")
        print()
    
    # Upsert data using MERGE to avoid duplicates
    quotes_table_ref = f"{target_project}.{dataset_id}.quotes"
    invoices_table_ref = f"{target_project}.{dataset_id}.invoices"
    quote_lines_table_ref = f"{target_project}.{dataset_id}.quote_lines"
    invoice_lines_table_ref = f"{target_project}.{dataset_id}.invoice_lines"
    customers_table_ref = f"{target_project}.{dataset_id}.customers"
    environmental_impact_table_ref = f"{target_project}.{dataset_id}.environmental_impact"
    
    # Upsert customers first (they're referenced by quotes and invoices)
    if all_customers:
        _upsert_customers(client, customers_table_ref, all_customers, target_project, dataset_id)
    
    # Upsert quotes (insert only new ones)
    if quotes:
        normalized_quotes = [normalize_quote_row(q) for q in quotes]
        _upsert_quotes(client, quotes_table_ref, normalized_quotes, target_project, dataset_id)
    
    # Upsert invoices (insert only new ones)
    if invoice_list:
        normalized_invoices = [normalize_invoice_row(i) for i in invoice_list]
        _upsert_invoices(client, invoices_table_ref, normalized_invoices, target_project, dataset_id)
    
    # Upsert quote lines (insert only new ones)
    if quote_lines:
        _upsert_quote_lines(client, quote_lines_table_ref, quote_lines, target_project, dataset_id)
    
    # Upsert invoice lines (insert only new ones)
    if invoice_lines:
        _upsert_invoice_lines(client, invoice_lines_table_ref, invoice_lines, target_project, dataset_id)
    
    # Upsert environmental impact (insert only new ones)
    if environmental_impact:
        _upsert_environmental_impact(client, environmental_impact_table_ref, environmental_impact, target_project, dataset_id)


def main():
    parser = argparse.ArgumentParser(
        description="Synchronize QuickBooks estimates and invoices to BigQuery normalized tables."
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of estimates to fetch per API call (1-1000, default: 100).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional limit on number of estimates to sync (0 = all, default: 0).",
    )
    parser.add_argument(
        "--bq-project",
        help="Target BigQuery project ID (defaults to application default).",
    )
    parser.add_argument(
        "--bq-dataset",
        default="greentech",
        help="Target BigQuery dataset ID (default: greentech).",
    )
    parser.add_argument(
        "--no-create-tables",
        action="store_true",
        help="Skip table creation (tables must already exist).",
    )
    args = parser.parse_args()
    
    try:
        # Verify QuickBooks connection
        company = get_company_info()
        company_name = company.get("CompanyName", "Unknown Company")
        print(f"Connected to QuickBooks company: {company_name}")
        print()
        
        # Fetch estimates
        print(f"Fetching estimates from QuickBooks...")
        estimates = list_all_estimates(batch_size=args.batch_size)
        if args.limit > 0:
            estimates = estimates[:args.limit]
        print(f"Fetched {len(estimates)} estimate(s)")
        
        # Fetch invoices
        print(f"Fetching invoices from QuickBooks...")
        invoices = list_all_invoices(batch_size=args.batch_size)
        if args.limit > 0:
            invoices = invoices[:args.limit]
        print(f"Fetched {len(invoices)} invoice(s)")
        print()
        
        print(f"Uploading to BigQuery...")
        print()
        load_into_bigquery(
            estimates=estimates,
            invoices=invoices,
            project_id=args.bq_project,
            dataset_id=args.bq_dataset,
            create_tables=not args.no_create_tables,
        )
        print()
        print("✅ Synchronization complete.")
    
    except QuickBooksAPIError as exc:
        print(f"❌ QuickBooks API error: {exc.message}")
        if exc.status_code:
            print(f"   HTTP status code: {exc.status_code}")
        if exc.response_data:
            print(json.dumps(exc.response_data, indent=2))
        sys.exit(1)
    except Exception as exc:
        print(f"❌ Unexpected error: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
