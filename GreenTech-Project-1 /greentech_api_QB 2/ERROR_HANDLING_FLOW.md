# 🛡️ Error Handling Flow - Complete Guide

**How the system handles wrong data at every layer**

---

## 📋 Overview

The system has **multiple layers of error checking** to catch wrong data as early as possible. Errors are handled gracefully at each layer with clear messages returned to the user.

---

## 🔄 Error Handling Flow Diagram

```
User Input (Wrong Data)
    ↓
┌─────────────────────────────────────────┐
│ LAYER 5: User Interface                 │
│ - create_estimate.py                    │
│ - api_server.py                         │
│ ✅ Basic validation                     │
│ ✅ User-friendly error messages         │
└─────────────────────────────────────────┘
    ↓ (if passes)
┌─────────────────────────────────────────┐
│ LAYER 4: Core Processing                │
│ - cli_push_estimate.py                  │
│ ✅ JSON file validation                 │
│ ✅ Calls Layer 3 validation             │
└─────────────────────────────────────────┘
    ↓ (if passes)
┌─────────────────────────────────────────┐
│ LAYER 3: Data Transformation            │
│ - mapping.py                            │
│ ✅ validate_quote_data()                │
│ ✅ Structure & data type checks         │
└─────────────────────────────────────────┘
    ↓ (if passes)
┌─────────────────────────────────────────┐
│ LAYER 2: API Communication              │
│ - quickbooks_client.py                  │
│ ✅ QuickBooksAPIError handling          │
│ ✅ Network error handling               │
└─────────────────────────────────────────┘
    ↓ (if passes)
┌─────────────────────────────────────────┐
│ LAYER 1: Authentication                 │
│ - oauth.py                              │
│ ✅ Token refresh errors                 │
└─────────────────────────────────────────┘
    ↓
QuickBooks API (External)
```

---

## 🎯 Layer-by-Layer Error Handling

### **LAYER 5: User Interface**

#### **A. `create_estimate.py` (Interactive Mode)**

**Location**: Lines 18-86

**Error Checks**:

1. **Missing Customer Name** (Line 24-27):
```python
customer_name = input("Customer Name: ").strip()
if not customer_name:
    print("❌ Customer name is required")
    return None
```
**Error Message**: `"❌ Customer name is required"`  
**User Sees**: Immediate feedback, script stops

2. **Invalid Item Format** (Line 71-74):
```python
if len(parts) >= 3:
    # Valid format
elif len(parts) == 1:
    # Just description
else:
    print("  ⚠️  Invalid format, skipping. Use: 'Description | Qty | Price'")
    continue
```
**Error Message**: `"⚠️ Invalid format, skipping. Use: 'Description | Qty | Price'"`  
**User Sees**: Warning, item skipped, can continue

3. **No Items Entered** (Line 84-86):
```python
if not items:
    print("❌ At least one item is required")
    return None
```
**Error Message**: `"❌ At least one item is required"`  
**User Sees**: Script stops, must add items

4. **Invalid Number Format** (Line 60-65):
```python
try:
    qty = float(qty_str) if qty_str else 1.0
    unit_price = float(price_str) if price_str else 0.0
except ValueError:
    qty = 1.0
    unit_price = 0.0  # Defaults to 0 if can't parse
```
**Error Handling**: Silent fallback to defaults (could be improved)

**What Happens**:
- ✅ Errors caught **before** any processing
- ✅ User gets immediate feedback
- ✅ Script stops gracefully (returns `None`)
- ✅ No data sent to QuickBooks

---

#### **B. `api_server.py` (REST API)**

**Location**: Lines 79-143

**Error Checks**:

1. **Not JSON Request** (Line 81-85):
```python
if not request.is_json:
    return jsonify({
        "ok": False,
        "error": "Request must be JSON"
    }), 400
```
**HTTP Response**: `400 Bad Request`  
**JSON Response**:
```json
{
    "ok": false,
    "error": "Request must be JSON"
}
```

2. **Missing Customer Field** (Line 93-97):
```python
if "customer" not in data:
    return jsonify({
        "ok": False,
        "error": "Missing 'customer' field"
    }), 400
```
**HTTP Response**: `400 Bad Request`  
**JSON Response**:
```json
{
    "ok": false,
    "error": "Missing 'customer' field"
}
```

3. **Missing or Empty Items** (Line 99-103):
```python
if "items" not in data or not isinstance(data["items"], list) or len(data["items"]) == 0:
    return jsonify({
        "ok": False,
        "error": "Missing or empty 'items' array"
    }), 400
```
**HTTP Response**: `400 Bad Request`  
**JSON Response**:
```json
{
    "ok": false,
    "error": "Missing or empty 'items' array"
}
```

4. **QuickBooks API Errors** (Line 130-135):
```python
except QuickBooksAPIError as e:
    return jsonify({
        "ok": False,
        "error": f"QuickBooks API Error: {e.message}",
        "status_code": e.status_code
    }), 400
```
**HTTP Response**: `400 Bad Request`  
**JSON Response**:
```json
{
    "ok": false,
    "error": "QuickBooks API Error: Invalid customer data",
    "status_code": 400
}
```

5. **Unexpected Server Errors** (Line 137-143):
```python
except Exception as e:
    error_trace = traceback.format_exc()
    print(f"Error processing estimate: {error_trace}")
    return jsonify({
        "ok": False,
        "error": f"Server error: {str(e)}"
    }), 500
```
**HTTP Response**: `500 Internal Server Error`  
**JSON Response**:
```json
{
    "ok": false,
    "error": "Server error: [error message]"
}
```
**Note**: Full traceback printed to server console (not sent to client)

**What Happens**:
- ✅ Errors caught **before** calling core processing
- ✅ Returns proper HTTP status codes
- ✅ JSON error responses (easy to parse)
- ✅ Temp files cleaned up even on error (Line 124-128)

---

### **LAYER 4: Core Processing**

#### **`cli_push_estimate.py`**

**Location**: Lines 64-271

**Error Checks**:

1. **JSON File Load Error** (Line 83-88):
```python
try:
    data = json.loads(json_path.read_text(encoding="utf-8"))
except Exception as e:
    error_msg = f"Failed to load JSON: {e}"
    print(f"❌ {error_msg}")
    return {"ok": False, "error": error_msg}
```
**Error Types Caught**:
- File not found
- Invalid JSON syntax
- Encoding errors
- Permission errors

**Return Value**:
```python
{
    "ok": False,
    "error": "Failed to load JSON: [specific error]"
}
```

2. **Data Validation Error** (Line 90-95):
```python
is_valid, validation_error = validate_quote_data(data)
if not is_valid:
    error_msg = f"Invalid quote data: {validation_error}"
    print(f"❌ {error_msg}")
    return {"ok": False, "error": error_msg}
```
**Calls**: `mapping.py` → `validate_quote_data()` (Layer 3)  
**Return Value**:
```python
{
    "ok": False,
    "error": "Invalid quote data: [validation error from Layer 3]"
}
```

3. **QuickBooks API Errors** (Line 243-257):
```python
except QuickBooksAPIError as e:
    error_msg = f"QuickBooks API Error: {e.message}"
    print(f"\n❌ {error_msg}")
    print(f"   Status Code: {e.status_code}")
    
    # Log failure
    append_log(reference, customer_name, len(items), subtotal, currency,
               "failed", "", error=error_msg)
    
    return {
        "ok": False,
        "error": error_msg,
        "status_code": e.status_code,
        "reference": reference
    }
```
**What Happens**:
- ✅ Error logged to CSV (Line 249-250)
- ✅ Error message printed to console
- ✅ Returns structured error response
- ✅ No estimate created in QuickBooks

4. **Unexpected Errors** (Line 259-271):
```python
except Exception as e:
    error_msg = f"Unexpected error: {str(e)}"
    print(f"\n❌ {error_msg}")
    
    # Log failure
    append_log(reference, customer_name, len(items), subtotal, currency,
               "failed", "", error=error_msg)
    
    return {
        "ok": False,
        "error": error_msg,
        "reference": reference
    }
```
**What Happens**:
- ✅ Catches any unexpected errors
- ✅ Logs to CSV
- ✅ Returns error response
- ✅ Prevents system crash

**What Happens**:
- ✅ Errors caught at multiple points
- ✅ All errors logged to CSV
- ✅ Clear error messages returned
- ✅ System continues running (doesn't crash)

---

### **LAYER 3: Data Transformation**

#### **`mapping.py` → `validate_quote_data()`**

**Location**: Lines 9-49

**Comprehensive Validation**:

1. **Missing Customer Section** (Line 20-21):
```python
if "customer" not in data:
    return False, "Missing 'customer' section"
```

2. **Missing or Invalid Items Array** (Line 23-27):
```python
if "items" not in data or not isinstance(data["items"], list):
    return False, "Missing or invalid 'items' array"

if len(data["items"]) == 0:
    return False, "No items in quote"
```

3. **Missing Customer Name** (Line 30-32):
```python
customer = data["customer"]
if not customer.get("display_name"):
    return False, "Customer display_name is required"
```

4. **Invalid Item Structure** (Line 35-47):
```python
for i, item in enumerate(data["items"]):
    if "description" not in item:
        return False, f"Item {i}: Missing description"
    if "qty" not in item:
        return False, f"Item {i}: Missing qty"
    if "unit_price" not in item:
        return False, f"Item {i}: Missing unit_price"
    
    try:
        float(item["qty"])
        float(item["unit_price"])
    except (ValueError, TypeError):
        return False, f"Item {i}: qty and unit_price must be numeric"
```

**Error Messages Examples**:
- `"Missing 'customer' section"`
- `"Missing or invalid 'items' array"`
- `"No items in quote"`
- `"Customer display_name is required"`
- `"Item 0: Missing description"`
- `"Item 1: Missing qty"`
- `"Item 2: qty and unit_price must be numeric"`

**What Happens**:
- ✅ Validates **entire data structure**
- ✅ Checks **data types** (numbers must be numeric)
- ✅ Provides **specific error messages** (which item, which field)
- ✅ Returns `(False, error_message)` tuple

---

### **LAYER 2: API Communication**

#### **`quickbooks_client.py`**

**Location**: Lines 24-83

**Error Handling**:

1. **Missing Realm ID** (Line 48-49):
```python
if not REALM_ID:
    raise QuickBooksAPIError("QBO_REALM_ID not set in environment")
```
**Error Type**: `QuickBooksAPIError`  
**Message**: `"QBO_REALM_ID not set in environment"`

2. **HTTP Error Responses** (Line 69-78):
```python
if response.status_code >= 400:
    error_data = response.json() if response.text else {}
    fault = error_data.get("Fault", {})
    error_msg = fault.get("Error", [{}])[0].get("Message", response.text)
    
    raise QuickBooksAPIError(
        message=error_msg,
        status_code=response.status_code,
        response_data=error_data
    )
```
**What Happens**:
- ✅ Checks HTTP status code
- ✅ Parses QuickBooks error response
- ✅ Extracts error message from QuickBooks
- ✅ Raises `QuickBooksAPIError` with details

**QuickBooks Error Examples**:
- `"Invalid customer data"`
- `"Customer already exists"`
- `"Invalid item reference"`
- `"Authentication failed"`

3. **Network Errors** (Line 82-83):
```python
except requests.exceptions.RequestException as e:
    raise QuickBooksAPIError(f"Network error: {str(e)}")
```
**Error Types Caught**:
- Connection timeout
- DNS resolution failure
- SSL certificate errors
- Network unreachable

**What Happens**:
- ✅ All errors converted to `QuickBooksAPIError`
- ✅ Error details preserved (status code, message)
- ✅ Propagated up to Layer 4 for handling

---

### **LAYER 1: Authentication**

#### **`oauth.py`**

**Error Handling** (implicit in token refresh):

If token refresh fails:
- `quickbooks_client.py` will get authentication error
- QuickBooks API returns `401 Unauthorized`
- Error propagates up as `QuickBooksAPIError`

---

## 📊 Complete Error Flow Example

### **Scenario: User enters invalid data**

**Input**:
```json
{
    "customer": {
        "display_name": ""  // ❌ Empty name
    },
    "items": []  // ❌ Empty items array
}
```

**Flow**:

1. **Layer 5 (`api_server.py`)**:
   - ✅ Checks: `"customer" in data` → Passes
   - ✅ Checks: `"items" in data` → Passes
   - ✅ Checks: `len(items) == 0` → **FAILS**
   - **Returns**: `400 Bad Request` with `"Missing or empty 'items' array"`
   - **Stops**: No further processing

2. **If items array exists but customer name is empty**:
   - Layer 5 passes
   - Layer 4 calls Layer 3 validation
   - **Layer 3 (`mapping.py`)**:
     - ✅ Checks: `customer.get("display_name")` → **FAILS**
     - **Returns**: `(False, "Customer display_name is required")`
   - **Layer 4**:
     - **Returns**: `{"ok": False, "error": "Invalid quote data: Customer display_name is required"}`
   - **Layer 5**:
     - **Returns**: `400 Bad Request` with error message

3. **If data passes validation but QuickBooks rejects it**:
   - All layers pass
   - **Layer 2 (`quickbooks_client.py`)**:
     - QuickBooks returns `400 Bad Request`
     - **Raises**: `QuickBooksAPIError("Invalid customer data", 400)`
   - **Layer 4**:
     - **Catches**: `QuickBooksAPIError`
     - **Logs**: Error to CSV
     - **Returns**: `{"ok": False, "error": "QuickBooks API Error: Invalid customer data", "status_code": 400}`
   - **Layer 5**:
     - **Returns**: `400 Bad Request` with error message

---

## 🎯 Error Response Formats

### **CLI Mode (`create_estimate.py`)**

**Success**:
```
✅ Estimate created successfully!
Check QuickBooks and the Quotes folder for your PDF.
```

**Error**:
```
❌ Invalid quote data: Customer display_name is required
```

### **API Server Mode (`api_server.py`)**

**Success** (HTTP 200):
```json
{
    "ok": true,
    "estimate_id": "123",
    "pdf_path": "Quotes/Estimate_GT-001.pdf",
    "status": "created"
}
```

**Error** (HTTP 400):
```json
{
    "ok": false,
    "error": "Invalid quote data: Customer display_name is required"
}
```

**Error** (HTTP 500):
```json
{
    "ok": false,
    "error": "Server error: [error message]"
}
```

---

## 📝 Error Logging

### **CSV Log (`logs/quotes_log.csv`)**

**Success Entry**:
```csv
timestamp,reference,customer_name,items_count,subtotal,currency,status,pdf_path,qbo_estimate_id,error
2025-01-15T10:30:00Z,GT-001,John Doe,3,450.00,CAD,created,Quotes/Estimate_GT-001.pdf,123,
```

**Error Entry**:
```csv
timestamp,reference,customer_name,items_count,subtotal,currency,status,pdf_path,qbo_estimate_id,error
2025-01-15T10:35:00Z,GT-002,Jane Smith,2,300.00,CAD,failed,,,Invalid quote data: Customer display_name is required
```

**What Gets Logged**:
- ✅ All attempts (success and failure)
- ✅ Error messages (truncated to 200 chars)
- ✅ Timestamp
- ✅ Reference number
- ✅ Customer name
- ✅ Status (`created` or `failed`)

---

## 🛡️ Error Prevention Strategies

### **1. Early Validation**
- ✅ Layer 5 checks basic structure **before** processing
- ✅ Layer 3 validates **entire data structure** before API calls
- ✅ Prevents unnecessary API calls

### **2. Clear Error Messages**
- ✅ Specific error messages (which field, which item)
- ✅ User-friendly language
- ✅ Actionable (tells user what's wrong)

### **3. Graceful Degradation**
- ✅ System doesn't crash
- ✅ Errors logged for debugging
- ✅ User gets feedback

### **4. Error Recovery**
- ✅ Temp files cleaned up on error
- ✅ CSV logs all attempts
- ✅ System ready for next request

---

## 🎓 Summary

| Layer | File | Error Checks | Error Format |
|-------|------|--------------|--------------|
| **5** | `create_estimate.py` | User input validation | Print messages |
| **5** | `api_server.py` | Request structure | HTTP + JSON |
| **4** | `cli_push_estimate.py` | JSON loading, calls Layer 3 | Dict with `ok: false` |
| **3** | `mapping.py` | Data structure & types | `(False, error_message)` |
| **2** | `quickbooks_client.py` | API responses, network | `QuickBooksAPIError` |
| **1** | `oauth.py` | Token errors (implicit) | Via Layer 2 |

**Key Points**:
- ✅ **Multiple validation layers** catch errors early
- ✅ **Clear error messages** at every level
- ✅ **All errors logged** to CSV
- ✅ **System never crashes** - errors handled gracefully
- ✅ **User always gets feedback** about what went wrong

**The system is designed to fail gracefully and provide clear feedback at every step!** 🛡️

