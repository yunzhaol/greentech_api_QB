# 📚 Complete File Reference - GreenTech QuickBooks API

**A comprehensive guide to all files, their functions, and how they work together.**

---

## 🏗️ Architecture Overview

This project uses a **5-layer architecture** where each layer has a specific responsibility. Files are organized into:

1. **Core Modules** - The 5-layer system
2. **User Interfaces** - Entry points for users
3. **Utility Scripts** - Setup and helper tools
4. **Configuration Files** - Settings and dependencies
5. **Data Files** - Input/output data

---

## 🔵 CORE MODULES (Most Important)

These files form the heart of the system and work together in a specific flow.

### **Layer 1: Authentication** - `oauth.py`

**Purpose:** Manages OAuth 2.0 authentication tokens for QuickBooks API access.

**Key Functions:**
- `get_access_token()` - Returns valid access token (caches and auto-refreshes)
- `refresh_access_token()` - Exchanges refresh token for new access token
- `get_auth_header()` - Returns Authorization header for API requests
- `_load_token_cache()` - Loads cached tokens from `.token_cache.json`
- `_save_token_cache()` - Saves tokens to `.token_cache.json`

**How It Works:**
1. Loads credentials from `.env` file (QBO_CLIENT_ID, QBO_CLIENT_SECRET, QBO_REFRESH_TOKEN)
2. Checks token cache file for valid cached access token
3. If expired or missing, refreshes using refresh token
4. Saves new token to cache file
5. Returns access token for API calls

**Files It Uses:**
- `.env` - Reads credentials
- `.token_cache.json` - Reads/writes cached tokens

**Files That Use It:**
- `quickbooks_client.py` - Gets auth headers for API calls

---

### **Layer 2: API Communication** - `quickbooks_client.py`

**Purpose:** Wraps all QuickBooks Online API interactions into Python functions.

**Key Functions:**
- `get_company_info()` - Tests connection, returns company information
- `get_or_create_customer()` - Finds existing customer or creates new one
- `create_estimate()` - Creates estimate in QuickBooks
- `get_estimate_pdf()` - Downloads estimate PDF
- `get_or_create_service_item()` - Gets or creates service item for line items
- `_make_request()` - Internal function for all API calls (handles authentication)

**How It Works:**
1. Uses `oauth.py` to get authentication headers
2. Makes HTTP requests to QuickBooks API
3. Handles errors and converts to custom exceptions
4. Returns formatted data to callers

**Files It Uses:**
- `oauth.py` - For authentication headers
- `.env` - Reads QBO_REALM_ID and QBO_MODE

**Files That Use It:**
- `cli_push_estimate.py` - Creates estimates, gets customers, downloads PDFs
- `api_server.py` - For health checks and status
- `find_estimate.py` - For searching estimates

**API Endpoints Used:**
- `GET /v3/company/{realm_id}/companyinfo/1` - Company info
- `GET /v3/company/{realm_id}/query` - Query customers/items/estimates
- `POST /v3/company/{realm_id}/customer` - Create customer
- `POST /v3/company/{realm_id}/estimate` - Create estimate
- `GET /v3/company/{realm_id}/estimate/{id}/pdf` - Download PDF

---

### **Layer 3: Data Transformation** - `mapping.py`

**Purpose:** Transforms quote JSON format into QuickBooks API format.

**Key Functions:**
- `validate_quote_data()` - Validates quote JSON structure
- `map_quote_to_qbo_estimate()` - Converts quote JSON to QuickBooks estimate format
- `extract_reference()` - Gets quote reference number
- `extract_customer_name()` - Gets customer display name
- `calculate_subtotal()` - Calculates total from items
- `format_sustainability_memo()` - Formats sustainability data into memo

**How It Works:**
1. Validates input JSON has required fields (customer, items, etc.)
2. Extracts customer information
3. Transforms items array to QuickBooks line items format
4. Adds sustainability metrics to customer memo
5. Returns formatted QuickBooks estimate payload

**Input Format (Our JSON):**
```json
{
  "customer": {"display_name": "John", "email": "..."},
  "items": [{"description": "...", "qty": 2, "unit_price": 150}],
  "quote": {"reference": "GT-001", "date": "2025-01-01"}
}
```

**Output Format (QuickBooks):**
```json
{
  "CustomerRef": {"value": "123"},
  "DocNumber": "GT-001",
  "Line": [{"Description": "...", "Amount": 300, ...}]
}
```

**Files It Uses:**
- None (standalone module - pure data transformation)

**Files That Use It:**
- `cli_push_estimate.py` - Validates and transforms quote data

---

### **Layer 4: Core Processing** - `cli_push_estimate.py`

**Purpose:** Orchestrates the entire estimate creation workflow.

**Key Functions:**
- `process_quote()` - Main function that processes quote JSON file
- `process_mock()` - Creates mock PDF for testing (no API calls)
- `process_quickbooks()` - Creates real estimate via QuickBooks API
- `append_log()` - Logs operations to CSV file

**How It Works:**
1. Loads and validates JSON file
2. Extracts key information (customer, items, reference)
3. If mock mode: Creates fake PDF file
4. If real mode:
   - Tests QuickBooks connection
   - Gets or creates customer
   - Gets or creates service item
   - Transforms data using `mapping.py`
   - Creates estimate via `quickbooks_client.py`
   - Downloads PDF
5. Logs everything to CSV file

**Files It Uses:**
- `mapping.py` - For validation and data transformation
- `quickbooks_client.py` - For all QuickBooks API operations

**Files That Use It:**
- `create_estimate.py` - CLI interface calls this
- `api_server.py` - REST API calls this

**Files It Creates:**
- `logs/quotes_log.csv` - Operation logs
- `Quotes/Estimate_*.pdf` - Generated PDF files

---

## 🎨 USER INTERFACES (Entry Points)

These files provide ways for users to interact with the system.

### **CLI Interface** - `create_estimate.py`

**Purpose:** User-friendly command-line interface for creating estimates.

**Key Functions:**
- `create_estimate_interactive()` - Interactive mode (prompts for input)
- `main()` - Main entry point (handles command-line arguments)

**How It Works:**
1. **Interactive Mode:** Prompts user for customer name, items, etc.
2. **JSON File Mode:** Reads quote data from JSON file
3. Creates temporary JSON file if needed
4. Calls `cli_push_estimate.process_quote()` to do the work
5. Displays results to user

**Usage:**
```bash
# Interactive mode
python create_estimate.py

# From JSON file
python create_estimate.py --json quote.json

# Mock mode (no QuickBooks API)
python create_estimate.py --json quote.json --mock
```

**Files It Uses:**
- `cli_push_estimate.py` - Does the actual processing

**Files That Use It:**
- None (it's an entry point)

---

### **REST API Server** - `api_server.py`

**Purpose:** Provides HTTP REST API endpoints for programmatic access (VBA/Excel integration).

**Key Functions:**
- `health_check()` - Health check endpoint (`GET /health`)
- `create_estimate()` - Create estimate endpoint (`POST /api/v1/estimate`)
- `create_mock_estimate()` - Mock estimate endpoint (`POST /api/v1/estimate/mock`)
- `get_status()` - API status endpoint (`GET /api/v1/status`)
- `get_logs()` - View logs endpoint (`GET /api/v1/logs`)
- `run_server()` - Starts Flask server

**How It Works:**
1. Flask web server listens on port 5000
2. Receives HTTP POST requests with JSON quote data
3. Creates temporary JSON file from request
4. Calls `cli_push_estimate.process_quote()` to process
5. Returns JSON response with results

**Endpoints:**
- `GET /health` - Health check (tests QuickBooks connection)
- `GET /api/v1/status` - API status and QuickBooks connection info
- `POST /api/v1/estimate` - Create estimate from JSON body
- `POST /api/v1/estimate/mock` - Create mock estimate
- `GET /api/v1/logs` - View recent logs (last 50 entries)

**Files It Uses:**
- `cli_push_estimate.py` - For processing quotes
- `quickbooks_client.py` - For health checks

**Files That Use It:**
- `start_server.py` - Starts this server

**CORS:** Enabled for VBA/Excel cross-origin requests

---

## 🔄 HOW CORE FILES COLLABORATE

### **Complete Data Flow:**

```
User/System Input
    │
    │ (Quote JSON)
    │
    ▼
┌─────────────────────────────────────────┐
│ USER INTERFACE LAYER                    │
│                                         │
│  Option A: CLI                          │
│  create_estimate.py                     │
│    │                                    │
│  Option B: REST API                     │
│  api_server.py (Flask)                  │
│    │                                    │
└────┼────────────────────────────────────┘
     │
     │ Calls
     │
     ▼
┌─────────────────────────────────────────┐
│ CORE PROCESSING LAYER                   │
│                                         │
│  cli_push_estimate.py                   │
│  • Loads JSON                           │
│  • Validates (uses mapping.py)          │
│  • Extracts info                        │
└────┬────────────────────────────────────┘
     │
     │ Uses
     │
     ▼
┌─────────────────────────────────────────┐
│ DATA TRANSFORMATION LAYER               │
│                                         │
│  mapping.py                             │
│  • Validates structure                  │
│  • Transforms to QuickBooks format      │
│  • Returns formatted payload            │
└────┬────────────────────────────────────┘
     │
     │ Returns transformed data
     │
     ▼
┌─────────────────────────────────────────┐
│ API COMMUNICATION LAYER                 │
│                                         │
│  quickbooks_client.py                   │
│  • Get/create customer                  │
│  • Get/create service item              │
│  • Create estimate                      │
│  • Download PDF                         │
│    │                                    │
│    │ Needs authentication               │
│    │                                    │
│    ▼                                    │
│  ┌──────────────────────────────────┐  │
│  │ AUTHENTICATION LAYER             │  │
│  │                                  │  │
│  │  oauth.py                        │  │
│  │  • Gets access token             │  │
│  │  • Refreshes if needed           │  │
│  │  • Returns auth headers          │  │
│  └──────────────────────────────────┘  │
└────┬────────────────────────────────────┘
     │
     │ Makes authenticated API calls
     │
     ▼
QuickBooks Online API
     │
     │ Returns estimate data and PDF
     │
     ▼
┌─────────────────────────────────────────┐
│ OUTPUT                                  │
│                                         │
│  • Estimate created in QuickBooks       │
│  • PDF file saved to Quotes/ folder     │
│  • CSV log entry in logs/ folder        │
│  • JSON response (if API mode)          │
└─────────────────────────────────────────┘
```

### **Collaboration Details:**

**1. User Starts Process:**
- User runs `create_estimate.py` OR sends HTTP POST to `api_server.py`
- Both create a JSON file with quote data

**2. Processing Begins:**
- Both call `cli_push_estimate.process_quote()`
- This loads JSON and validates it

**3. Validation:**
- `cli_push_estimate.py` calls `mapping.validate_quote_data()`
- Ensures required fields are present

**4. Data Transformation:**
- `cli_push_estimate.py` calls `mapping.map_quote_to_qbo_estimate()`
- Converts our JSON format to QuickBooks format

**5. Customer Management:**
- `cli_push_estimate.py` calls `quickbooks_client.get_or_create_customer()`
- `quickbooks_client.py` needs authentication
- It calls `oauth.get_auth_header()` to get token
- `oauth.py` checks cache, refreshes if needed, returns header
- `quickbooks_client.py` makes API call to QuickBooks

**6. Estimate Creation:**
- Similar process: `quickbooks_client.create_estimate()`
- Uses `oauth.py` for authentication
- Makes API call to QuickBooks

**7. PDF Download:**
- `quickbooks_client.get_estimate_pdf()` downloads PDF
- Saves to `Quotes/` folder

**8. Logging:**
- `cli_push_estimate.append_log()` writes to CSV
- Logs timestamp, reference, customer, status, etc.

**9. Response:**
- Results returned to user
- CLI: Prints to console
- API: Returns JSON response

---

## 🛠️ UTILITY SCRIPTS (Important for Setup & Operations)

### **OAuth Setup** - `initial_oauth_setup.py`

**Purpose:** One-time setup script to get OAuth tokens from QuickBooks.

**Key Functions:**
- `generate_auth_url()` - Creates OAuth authorization URL
- `exchange_code_for_tokens()` - Exchanges authorization code for tokens
- `create_callback_server()` - Creates Flask server for OAuth callback (optional)
- `main()` - Main OAuth flow

**How It Works:**
1. Opens browser to QuickBooks authorization page
2. User authorizes the app
3. Redirects to callback URL (or user copies URL)
4. Extracts authorization code from URL
5. Exchanges code for access token and refresh token
6. Automatically saves tokens to `.env` file and cache

**Files It Creates/Modifies:**
- `.env` - Adds QBO_REFRESH_TOKEN and QBO_REALM_ID
- `.token_cache.json` - Saves access token

**When to Use:**
- First time setup
- When refresh token expires
- When switching QuickBooks companies

---

### **Manual Token Setup** - `setup_tokens.py`

**Purpose:** Alternative way to set tokens manually if OAuth flow fails.

**How It Works:**
1. Prompts user to paste tokens from OAuth Playground
2. Saves access token to cache
3. Saves refresh token and realm ID to `.env`

**Files It Creates/Modifies:**
- `.env` - Adds/updates tokens
- `.token_cache.json` - Saves access token

**When to Use:**
- If `initial_oauth_setup.py` fails
- If you have tokens from OAuth Playground

---

### **System Setup Checker** - `setup.py`

**Purpose:** Checks if system is properly configured and guides setup.

**Key Functions:**
- `check_python_version()` - Verifies Python 3.8+
- `check_dependencies()` - Checks if required packages installed
- `check_env_file()` - Validates `.env` file exists and configured
- `check_oauth_setup()` - Tests QuickBooks connection

**How It Works:**
1. Checks Python version
2. Checks dependencies (tries to auto-install if missing)
3. Checks `.env` file exists and has credentials
4. Tests OAuth connection if configured
5. Provides guidance on what to fix

**Files It Reads:**
- `requirements_txt.txt` - For dependency list
- `.env` - For configuration check

**When to Use:**
- First time setup
- When troubleshooting configuration issues
- After installing on new machine

---

### **Find Estimates** - `find_estimate.py`

**Purpose:** Utility to search for estimates in QuickBooks.

**Key Functions:**
- `list_all_estimates()` - Lists all estimates (with limit)
- `find_estimate_by_doc_number()` - Finds estimate by Doc Number
- `main()` - Handles command-line arguments

**How It Works:**
1. Uses `quickbooks_client._make_request()` to query QuickBooks
2. Formats and displays results

**Usage:**
```bash
# List all estimates
python find_estimate.py --list

# Find by Doc Number
python find_estimate.py --doc-number GT-001
```

**Files It Uses:**
- `quickbooks_client.py` - For API queries

**When to Use:**
- Finding existing estimates
- Verifying estimates were created
- Checking estimate details

---

### **System Testing** - `test_system.py`

**Purpose:** Tests all system components to verify everything works.

**Test Functions:**
- `test_imports()` - Tests all modules can be imported
- `test_json_validation()` - Tests JSON validation
- `test_oauth_config()` - Tests OAuth configuration
- `test_quickbooks_connection()` - Tests QuickBooks API connection
- `test_mock_estimate()` - Tests mock estimate creation
- `test_api_server_imports()` - Tests API server setup

**How It Works:**
1. Tests each component individually
2. Reports pass/fail for each test
3. Provides summary at end

**Files It Tests:**
- All core modules
- Configuration
- API server
- Mock processing

**When to Use:**
- After setup
- When troubleshooting
- Before important presentations
- After code changes

---

## 🚀 STARTUP SCRIPTS (Deployment)

### **Server Launcher** - `start_server.py`

**Purpose:** Simple wrapper to start the Flask API server.

**How It Works:**
1. Imports `api_server.run_server()`
2. Sets default host/port
3. Can read from environment variables (API_HOST, API_PORT)
4. Starts Flask server

**Files It Uses:**
- `api_server.py` - The actual server

**Usage:**
```bash
python start_server.py
# Or with custom port
API_PORT=8080 python start_server.py
```

---

### **Unix/Mac Startup** - `start_server.sh`

**Purpose:** Bash script to start server on Unix/Mac systems.

**How It Works:**
1. Changes to script directory
2. Runs `python3 start_server.py`

**Usage:**
```bash
./start_server.sh
# Or
bash start_server.sh
```

---

### **Windows Startup** - `start_server.bat`

**Purpose:** Batch script to start server on Windows.

**How It Works:**
1. Changes to script directory
2. Runs `python start_server.py`
3. Pauses so window doesn't close

**Usage:**
```bash
start_server.bat
# Or double-click the file
```

---

## ⚙️ CONFIGURATION FILES

### **Python Dependencies** - `requirements_txt.txt`

**Purpose:** Lists all Python packages needed for the project.

**Contents:**
- `requests==2.31.0` - HTTP library for API calls
- `python-dotenv==1.0.0` - Loads `.env` file
- `flask==3.0.0` - Web framework for API server
- `flask-cors==4.0.0` - CORS support for Excel/VBA

**How It Works:**
- Used by `pip install -r requirements_txt.txt`
- Read by `setup.py` to check dependencies

**When to Use:**
- Installing dependencies
- Setting up on new machine
- Updating packages

---

### **Deployment Configuration** - `Procfile`

**Purpose:** Tells cloud platforms (Heroku, Railway) how to run the app.

**Contents:**
```
web: python start_server.py --host 0.0.0.0 --port $PORT
```

**How It Works:**
- Cloud platform reads this file
- Runs the command to start the server
- Uses `$PORT` environment variable from platform

**When to Use:**
- Deploying to Heroku, Railway, or similar platforms

---

### **Python Version** - `runtime.txt`

**Purpose:** Specifies Python version for cloud deployment.

**Contents:**
```
python-3.12
```

**How It Works:**
- Cloud platforms read this
- Use specified Python version for deployment

**When to Use:**
- Deploying to cloud platforms that support `runtime.txt`

---

## 📊 DATA FILES

### **Input Sample** - `samples/quote_sample.json`

**Purpose:** Example quote JSON file showing required format.

**Contents:**
- Example customer data
- Example items array
- Example sustainability metrics
- Example quote reference and date

**How It Works:**
- Used for testing and as documentation
- Shows users what format their JSON should be

**When to Use:**
- Testing the system
- Learning the JSON format
- As template for creating quotes

---

### **Operation Logs** - `logs/quotes_log.csv`

**Purpose:** CSV log file tracking all estimate creation operations.

**Columns:**
- `timestamp` - When operation occurred
- `reference` - Quote reference number
- `customer_name` - Customer name
- `items_count` - Number of items
- `subtotal` - Total amount
- `currency` - Currency code
- `status` - Status (created, mock_created, failed)
- `pdf_path` - Path to PDF file
- `qbo_estimate_id` - QuickBooks Estimate ID
- `error` - Error message (if any)

**How It Works:**
- Created automatically by `cli_push_estimate.append_log()`
- Appends new row for each operation
- Never overwrites (append-only)

**When to Use:**
- Tracking all estimate creations
- Audit trail
- Debugging issues
- Reporting

---

### **Generated PDFs** - `Quotes/Estimate_*.pdf`

**Purpose:** PDF files of estimates downloaded from QuickBooks.

**Naming:**
- Format: `Estimate_{DocNumber}.pdf`
- Example: `Estimate_GT-TEST-001.pdf`

**How It Works:**
- Created by `quickbooks_client.get_estimate_pdf()`
- Downloaded from QuickBooks API
- Saved to `Quotes/` folder

**When to Use:**
- Viewing estimates
- Sending to customers
- Archiving quotes

---

## 📚 DOCUMENTATION FILES

### **Main Documentation** - `README.md`

**Purpose:** Primary user guide and documentation.

**Contents:**
- Quick start guide
- Installation instructions
- Usage examples
- Troubleshooting
- Common commands

**When to Use:**
- First-time users
- Quick reference
- Troubleshooting

---

### **Setup Guide** - `GETTING_STARTED.md`

**Purpose:** Step-by-step setup guide for new users.

**Contents:**
- Detailed setup steps
- OAuth configuration walkthrough
- First estimate creation
- Troubleshooting tips

**When to Use:**
- Initial setup
- Learning the system
- Following setup process

---

## 🔗 COMPLETE FILE DEPENDENCY CHART

```
STANDALONE:
  mapping.py (no dependencies)

LEVEL 1 (External libraries only):
  oauth.py
    └── Uses: requests, dotenv, datetime
    └── Reads: .env, .token_cache.json

LEVEL 2 (Uses Level 1):
  quickbooks_client.py
    └── Uses: oauth.py, requests, dotenv
    └── Reads: .env

LEVEL 3 (Uses Level 1-2):
  cli_push_estimate.py
    └── Uses: mapping.py, quickbooks_client.py

LEVEL 4 (Uses Level 3):
  create_estimate.py
    └── Uses: cli_push_estimate.py
  
  api_server.py
    └── Uses: cli_push_estimate.py, quickbooks_client.py, flask

UTILITY SCRIPTS:
  initial_oauth_setup.py
    └── Uses: oauth.py, flask, webbrowser, requests
  
  find_estimate.py
    └── Uses: quickbooks_client.py
  
  test_system.py
    └── Tests: all modules
  
  setup.py
    └── Uses: quickbooks_client.py (for testing)
  
  setup_tokens.py
    └── Reads/Writes: .env, .token_cache.json

STARTUP:
  start_server.py
    └── Uses: api_server.py
  
  start_server.sh / .bat
    └── Calls: start_server.py
```

---

## 🎯 QUICK REFERENCE: FILE PURPOSE

### **Must-Know Files:**
- `oauth.py` - Authentication (auto token refresh)
- `quickbooks_client.py` - QuickBooks API calls
- `mapping.py` - Data format conversion
- `cli_push_estimate.py` - Main processing logic
- `create_estimate.py` - CLI interface
- `api_server.py` - REST API server

### **Setup Files:**
- `initial_oauth_setup.py` - Get OAuth tokens
- `setup.py` - Check system configuration
- `requirements_txt.txt` - Install dependencies

### **Utility Files:**
- `find_estimate.py` - Search estimates
- `test_system.py` - Test everything works
- `setup_tokens.py` - Manual token setup

### **Configuration:**
- `.env` - Secrets (DO NOT COMMIT)
- `.token_cache.json` - Cached tokens (DO NOT COMMIT)
- `Procfile` - Deployment config
- `runtime.txt` - Python version

### **Data:**
- `samples/quote_sample.json` - Example input
- `logs/quotes_log.csv` - Operation logs
- `Quotes/*.pdf` - Generated PDFs

---

## ✅ SUMMARY

**Core Flow:**
1. User starts via `create_estimate.py` or `api_server.py`
2. Both use `cli_push_estimate.py` for processing
3. Processing uses `mapping.py` for transformation
4. Processing uses `quickbooks_client.py` for API calls
5. API client uses `oauth.py` for authentication
6. Results logged and PDF saved

**Key Collaboration:**
- Each layer only knows about the layer below it
- Data flows down (request) and results flow back up
- Modular design allows easy testing and maintenance

**All files work together to automate the quote-to-estimate process!** 🚀

