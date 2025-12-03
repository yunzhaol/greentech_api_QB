# 🏗️ 5-Layer Project Architecture - File Reference Guide

**Complete explanation of all files and their roles in the QuickBooks integration system.**

---

## 📐 Architecture Overview

This project follows a **5-layer architecture** where each layer has a specific responsibility. Data flows from user interfaces down through processing layers to the QuickBooks API.

```
┌─────────────────────────────────────────┐
│  LAYER 5: USER INTERFACES               │
│  (Entry points for users)                │
├─────────────────────────────────────────┤
│  LAYER 4: CORE PROCESSING               │
│  (Business logic orchestration)          │
├─────────────────────────────────────────┤
│  LAYER 3: DATA TRANSFORMATION           │
│  (Format conversion)                    │
├─────────────────────────────────────────┤
│  LAYER 2: API COMMUNICATION              │
│  (QuickBooks API wrapper)                │
├─────────────────────────────────────────┤
│  LAYER 1: AUTHENTICATION                │
│  (OAuth token management)                │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│  EXTERNAL: QuickBooks API                │
└─────────────────────────────────────────┘
```

---

## 🔵 LAYER 5: USER INTERFACES

**Purpose**: Entry points where users interact with the system. These files provide different ways to create estimates.

### `create_estimate.py` 🎨
**Layer**: 5 - User Interface  
**Color**: Green  
**Icon**: 👤 Person

**What It Does**:
- Provides a user-friendly interface for creating QuickBooks estimates
- Supports two modes: interactive (command-line prompts) and JSON file input
- Simplifies the estimate creation process with minimal required input

**Key Features**:
- **Interactive Mode**: Prompts user for customer name and items step-by-step
- **JSON Mode**: Reads quote data from JSON file
- **Mock Mode**: Tests without connecting to QuickBooks API
- Auto-generates quote references and dates
- Simplified input format (e.g., "Description | Qty | Price")

**How It Works**:
1. User runs script: `python3 create_estimate.py`
2. Script collects quote data (interactive or from JSON)
3. Calls `cli_push_estimate.py` (Layer 4) to process the quote
4. Displays results to user

**Functions**:
- `create_estimate_interactive()` - Interactive input mode
- `create_estimate_from_json()` - JSON file input mode
- `print_banner()` - Welcome message

**Dependencies**:
- Uses: `cli_push_estimate.py` (Layer 4)

**Example Usage**:
```bash
# Interactive mode
python3 create_estimate.py

# JSON file mode
python3 create_estimate.py --json samples/quote_sample.json

# Mock mode (testing)
python3 create_estimate.py --json samples/quote_sample.json --mock
```

---

### `api_server.py` 🌐
**Layer**: 5 - User Interface  
**Color**: Green  
**Icon**: 👤 Person

**What It Does**:
- Provides REST API endpoints for programmatic access
- Enables integration with VBA/Excel, web applications, or other systems
- Runs as a Flask web server listening on HTTP requests

**Key Features**:
- RESTful API endpoints (`/api/v1/estimate`, `/health`)
- CORS enabled for cross-origin requests (Excel/VBA integration)
- JSON request/response format
- Health check endpoint for monitoring
- Error handling with proper HTTP status codes

**Endpoints**:
- `GET /health` - Health check and QuickBooks connection status
- `POST /api/v1/estimate` - Create estimate from JSON payload

**How It Works**:
1. Server starts: `python3 start_server.py`
2. Listens on `http://localhost:5000`
3. Receives HTTP POST requests with quote JSON
4. Calls `cli_push_estimate.py` (Layer 4) to process
5. Returns JSON response with results

**Dependencies**:
- Uses: `cli_push_estimate.py` (Layer 4), `quickbooks_client.py` (Layer 2)
- Requires: Flask, flask-cors

**Example Usage**:
```bash
# Start server
python3 start_server.py

# Send request (from another application)
curl -X POST http://localhost:5000/api/v1/estimate \
  -H "Content-Type: application/json" \
  -d @samples/quote_sample.json
```

---

## 🟢 LAYER 4: CORE PROCESSING

**Purpose**: Orchestrates the business logic and coordinates between layers. This is where the main workflow happens.

### `cli_push_estimate.py` ⚙️
**Layer**: 4 - Core Processing  
**Color**: Green  
**Icon**: ⚙️ Gear

**What It Does**:
- Main processing engine that orchestrates the entire estimate creation workflow
- Coordinates data transformation, API calls, PDF generation, and logging
- Handles error management and result reporting

**Key Features**:
- Validates quote data structure
- Transforms data format (via Layer 3)
- Creates/updates customers in QuickBooks
- Creates estimates in QuickBooks
- Downloads PDF files
- Logs all operations to CSV file
- Comprehensive error handling

**How It Works**:
1. Receives quote JSON data
2. Validates data using `mapping.py` (Layer 3)
3. Transforms quote format to QuickBooks format using `mapping.py` (Layer 3)
4. Gets or creates customer using `quickbooks_client.py` (Layer 2)
5. Creates estimate using `quickbooks_client.py` (Layer 2)
6. Downloads PDF using `quickbooks_client.py` (Layer 2)
7. Saves PDF to `Quotes/` folder
8. Logs operation to `logs/quotes_log.csv`
9. Returns success/failure status

**Functions**:
- `process_quote(json_path, mock=False)` - Main processing function
- `append_log()` - Logs operations to CSV
- `utc_now()` - Timestamp helper

**Dependencies**:
- Uses: `mapping.py` (Layer 3), `quickbooks_client.py` (Layer 2)
- Creates: `logs/quotes_log.csv`, `Quotes/*.pdf`

**Data Flow**:
```
Quote JSON Input
    ↓
[Validate & Transform] → mapping.py (Layer 3)
    ↓
[Create Customer] → quickbooks_client.py (Layer 2)
    ↓
[Create Estimate] → quickbooks_client.py (Layer 2)
    ↓
[Download PDF] → quickbooks_client.py (Layer 2)
    ↓
[Save & Log] → Filesystem
    ↓
Result Output
```

---

## 🔵 LAYER 3: DATA TRANSFORMATION

**Purpose**: Converts data between different formats. Transforms quote JSON into QuickBooks API format.

### `mapping.py` 🔄
**Layer**: 3 - Data Transformation  
**Color**: Light Blue  
**Icon**: ↔️ Transform

**What It Does**:
- Transforms quote data from internal JSON format to QuickBooks API format
- Validates data structure and required fields
- Extracts and formats customer information
- Calculates totals and subtotals
- Formats sustainability data into memo fields

**Key Features**:
- Data validation (required fields, data types)
- Format conversion (quote format → QBO format)
- Customer data extraction
- Line item transformation
- Memo formatting (sustainability metrics)

**How It Works**:
1. Receives quote JSON in internal format
2. Validates structure (customer, items, etc.)
3. Extracts customer information
4. Transforms items array to QuickBooks line items
5. Calculates subtotals and totals
6. Formats sustainability data as memo
7. Returns QuickBooks API-ready JSON

**Functions**:
- `validate_quote_data(data)` - Validates quote structure
- `map_quote_to_qbo_estimate(quote_data)` - Main transformation function
- `extract_reference(data)` - Gets quote reference number
- `extract_customer_name(data)` - Gets customer display name
- `calculate_subtotal(items)` - Calculates total from items
- `format_sustainability_memo(data)` - Formats sustainability metrics

**Input Format** (Quote JSON):
```json
{
  "customer": { "display_name": "John Doe", ... },
  "items": [{ "description": "...", "qty": 2, "unit_price": 150 }],
  "sustainability": { "trees": 1, ... }
}
```

**Output Format** (QuickBooks API):
```json
{
  "CustomerRef": { "value": "123", "name": "John Doe" },
  "Line": [{ "DetailType": "SalesItemLineDetail", ... }],
  "DocNumber": "GT-001",
  ...
}
```

**Dependencies**:
- Used by: `cli_push_estimate.py` (Layer 4)
- No dependencies on other project files (pure transformation logic)

---

## 🔵 LAYER 2: API COMMUNICATION

**Purpose**: Handles all communication with QuickBooks Online API. Wraps API calls into Python functions.

### `quickbooks_client.py` 📡
**Layer**: 2 - API Communication  
**Color**: Light Blue  
**Icon**: 🌐 Network/API

**What It Does**:
- Provides Python functions for all QuickBooks Online API operations
- Handles HTTP requests, error management, and response parsing
- Manages authentication headers automatically
- Converts API responses to Python-friendly formats

**Key Features**:
- Customer management (get, create, search)
- Estimate creation and retrieval
- PDF download functionality
- Service item management
- Company information retrieval
- Automatic authentication (via Layer 1)
- Error handling with custom exceptions

**How It Works**:
1. Gets authentication header from `oauth.py` (Layer 1)
2. Constructs API request URL based on mode (sandbox/production)
3. Makes HTTP request to QuickBooks API
4. Handles errors and converts to custom exceptions
5. Parses JSON response
6. Returns formatted data to caller

**Functions**:
- `get_company_info()` - Tests connection, returns company info
- `get_or_create_customer(customer_data)` - Finds or creates customer
- `create_estimate(estimate_data)` - Creates estimate in QuickBooks
- `get_estimate_pdf(estimate_id)` - Downloads estimate PDF
- `get_or_create_service_item(name)` - Gets or creates service item
- `_make_request(method, endpoint, data)` - Internal HTTP request handler

**API Endpoints Used**:
- `GET /v3/company/{realm_id}/companyinfo/1` - Company information
- `GET /v3/company/{realm_id}/query` - Query customers/items/estimates
- `POST /v3/company/{realm_id}/customer` - Create customer
- `POST /v3/company/{realm_id}/estimate` - Create estimate
- `GET /v3/company/{realm_id}/estimate/{id}/pdf` - Download PDF

**Dependencies**:
- Uses: `oauth.py` (Layer 1) for authentication
- Requires: `requests` library, `.env` file with `QBO_REALM_ID`

**Error Handling**:
- Raises `QuickBooksAPIError` for API failures
- Includes status code and response data in exception

---

## 🟠 LAYER 1: AUTHENTICATION

**Purpose**: Manages OAuth 2.0 authentication tokens. Ensures all API calls are properly authenticated.

### `oauth.py` 🔒
**Layer**: 1 - Authentication  
**Color**: Orange  
**Icon**: 🔒 Padlock

**What It Does**:
- Manages OAuth 2.0 access tokens for QuickBooks API
- Handles token refresh automatically
- Caches tokens to avoid unnecessary API calls
- Provides authentication headers for API requests

**Key Features**:
- Automatic token refresh (when expired)
- Token caching (saves to `.token_cache.json`)
- Environment variable configuration
- Support for sandbox and production modes
- Secure token storage

**How It Works**:
1. Loads credentials from `.env` file (CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN)
2. Checks token cache file (`.token_cache.json`) for valid cached token
3. If token expired or missing:
   - Calls QuickBooks token endpoint with refresh token
   - Gets new access token
   - Saves to cache file with expiration time
4. Returns access token for API calls

**Functions**:
- `get_access_token()` - Returns valid access token (auto-refreshes if needed)
- `refresh_access_token()` - Exchanges refresh token for new access token
- `get_auth_header()` - Returns Authorization header for API requests
- `_load_token_cache()` - Loads cached tokens from file
- `_save_token_cache()` - Saves tokens to cache file

**Token Flow**:
```
Refresh Token (from .env)
    ↓
[Request New Access Token] → QuickBooks Token Endpoint
    ↓
[Access Token + Expiration] → Cache to .token_cache.json
    ↓
[Return Token] → quickbooks_client.py (Layer 2)
```

**Dependencies**:
- Requires: `.env` file with OAuth credentials
- Creates: `.token_cache.json` (token cache file)
- Used by: `quickbooks_client.py` (Layer 2)

**Configuration** (`.env` file):
```bash
QBO_CLIENT_ID=your_client_id
QBO_CLIENT_SECRET=your_client_secret
QBO_REFRESH_TOKEN=your_refresh_token
QBO_MODE=sandbox  # or 'production'
```

---

## 🔧 UTILITY FILES

### `initial_oauth_setup.py`
**Purpose**: First-time OAuth setup wizard. Guides users through the OAuth flow to get initial tokens.

**What It Does**:
- Opens browser to QuickBooks authorization page
- Guides user through OAuth consent flow
- Exchanges authorization code for tokens
- Automatically saves tokens to `.env` file

**When to Use**: First time setup, or when tokens need to be refreshed manually.

---

### `setup_tokens.py`
**Purpose**: Manual token setup tool. Allows pasting tokens from OAuth Playground.

**What It Does**:
- Prompts user to paste tokens from Intuit OAuth Playground
- Validates token format
- Saves tokens to `.env` file automatically

**When to Use**: When `initial_oauth_setup.py` fails, or when using OAuth Playground tokens.

---

### `find_estimate.py`
**Purpose**: Utility script to search and find estimates in QuickBooks.

**What It Does**:
- Lists all estimates
- Searches by document number
- Displays estimate details

**Usage**:
```bash
python3 find_estimate.py --list
python3 find_estimate.py --doc-number GT-TEST-001
```

---

### `test_system.py`
**Purpose**: System testing script. Validates all components are working.

**What It Does**:
- Tests OAuth authentication
- Tests QuickBooks connection
- Tests estimate creation (mock mode)
- Validates all dependencies

**Usage**:
```bash
python3 test_system.py
```

---

### `start_server.py`
**Purpose**: Starts the Flask API server.

**What It Does**:
- Launches Flask application
- Configures CORS
- Starts server on port 5000
- Provides startup messages

**Usage**:
```bash
python3 start_server.py
```

---

## 📁 CONFIGURATION FILES

### `.env`
**Purpose**: Environment variables configuration file. Contains sensitive credentials.

**Contents**:
- `QBO_CLIENT_ID` - QuickBooks app client ID
- `QBO_CLIENT_SECRET` - QuickBooks app secret
- `QBO_REFRESH_TOKEN` - OAuth refresh token
- `QBO_REALM_ID` - QuickBooks company ID
- `QBO_MODE` - "sandbox" or "production"

**Security**: ⚠️ Never commit this file to version control!

---

### `.token_cache.json`
**Purpose**: Cached OAuth access tokens. Created automatically by `oauth.py`.

**Contents**:
- `access_token` - Current access token
- `expires_at` - Token expiration timestamp

**Security**: ⚠️ Contains sensitive tokens - do not share!

---

### `requirements_txt.txt`
**Purpose**: Python package dependencies list.

**Key Packages**:
- `requests` - HTTP library
- `flask` - Web server framework
- `flask-cors` - CORS support
- `python-dotenv` - Environment variable loading

---

## 📊 DATA FLOW EXAMPLE

Here's how data flows through all layers when creating an estimate:

```
1. USER INPUT
   └─> create_estimate.py (Layer 5)
       Reads quote JSON or prompts user

2. PROCESSING
   └─> cli_push_estimate.py (Layer 4)
       Orchestrates workflow

3. DATA TRANSFORMATION
   └─> mapping.py (Layer 3)
       Converts quote format → QBO format

4. API CALLS
   └─> quickbooks_client.py (Layer 2)
       Makes HTTP requests to QuickBooks

5. AUTHENTICATION
   └─> oauth.py (Layer 1)
       Provides auth headers

6. EXTERNAL API
   └─> QuickBooks Online API
       Processes request, returns estimate

7. RESPONSE FLOW (reverse)
   └─> PDF downloaded, saved, logged
```

---

## 🎯 Quick Reference

| File | Layer | Purpose | Used By |
|------|-------|---------|---------|
| `create_estimate.py` | 5 | User interface (CLI) | Users |
| `api_server.py` | 5 | User interface (REST API) | VBA/Excel, Web apps |
| `cli_push_estimate.py` | 4 | Core processing | Layer 5 files |
| `mapping.py` | 3 | Data transformation | Layer 4 |
| `quickbooks_client.py` | 2 | API communication | Layer 4 |
| `oauth.py` | 1 | Authentication | Layer 2 |

---

## 🔄 Dependency Graph

```
create_estimate.py ──┐
                     ├──> cli_push_estimate.py ──> mapping.py
api_server.py ──────┘                    │
                                         ├──> quickbooks_client.py ──> oauth.py
                                         │
                                         └──> QuickBooks API
```

---

**This architecture ensures separation of concerns, making the system modular, testable, and maintainable!** 🚀

