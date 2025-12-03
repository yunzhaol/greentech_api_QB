# 📁 File Structure & Architecture

## 🗂️ Repository Structure

```
greentech_api_QB/
├── 📄 Core Python Modules
│   ├── initial_oauth_setup.py    # OAuth authorization (run once)
│   ├── oauth.py                  # Token management & refresh
│   ├── quickbooks_client.py      # QuickBooks API client
│   ├── mapping.py                # JSON → QuickBooks format mapping
│   ├── create_estimate.py        # Interactive estimate creator
│   ├── cli_push_estimate.py      # CLI tool for creating estimates
│   ├── find_estimate.py          # Find estimates in QuickBooks
│   ├── api_server.py             # Flask REST API server
│   ├── start_server.py            # Server startup script
│   ├── setup.py                  # Setup checker
│   └── test_system.py            # System testing
│
├── 📋 Configuration & Data
│   ├── .env                       # Your credentials (DO NOT COMMIT)
│   ├── .env.example              # Template (safe to share)
│   ├── .token_cache.json         # Cached access tokens (DO NOT COMMIT)
│   ├── requirements_txt.txt       # Python dependencies
│   ├── runtime.txt               # Python version (for deployment)
│   ├── Procfile                  # Deployment config
│   └── samples/
│       └── quote_sample.json     # Example quote JSON
│
├── 📚 Documentation
│   ├── README.md                 # User guide
│   └── FILE_STRUCTURE_AND_WORKFLOW.md  # This file
│
├── 📊 Logs & Output
│   ├── logs/
│   │   └── quotes_log.csv        # All quote operations logged here
│   └── Quotes/
│       └── Estimate_*.pdf        # Downloaded estimate PDFs
│
└── 🔧 Scripts
    ├── start_server.sh           # Unix server startup
    └── start_server.bat          # Windows server startup
```

---

## 🔄 How Everything Works

### 1. Authentication Flow

```
User → initial_oauth_setup.py → Intuit OAuth → Authorization Code
  ↓
Exchange Code → Get Tokens → Save to .env
  ↓
oauth.py → Caches tokens → Provides access tokens for API calls
```

**Files:**
- `initial_oauth_setup.py` - Handles OAuth flow
- `oauth.py` - Token management with persistent cache
- `.env` - Stores credentials
- `.token_cache.json` - Caches access tokens

---

### 2. Creating Estimates Flow

```
JSON File → create_estimate.py → mapping.py → quickbooks_client.py
  ↓
Validate → Map Format → Get/Create Customer → Create Estimate → Download PDF → Log
```

**Files:**
- `create_estimate.py` - Main entry point (interactive or JSON)
- `mapping.py` - Transforms JSON to QuickBooks format
- `quickbooks_client.py` - Makes QuickBooks API calls
- `oauth.py` - Provides authentication

**Data Flow:**
1. Read JSON file
2. Validate structure (`mapping.validate_quote_data()`)
3. Map to QuickBooks format (`mapping.map_quote_to_qbo_estimate()`)
4. Get/create customer (`quickbooks_client.get_or_create_customer()`)
5. Create estimate (`quickbooks_client.create_estimate()`)
6. Download PDF (`quickbooks_client.get_estimate_pdf()`)
7. Log to CSV (`logs/quotes_log.csv`)

---

### 3. API Server Flow

```
HTTP POST → api_server.py → cli_push_estimate.py → Same flow as CLI
  ↓
Return JSON Response → Client receives result
```

**Files:**
- `api_server.py` - Flask REST API
- `start_server.py` - Starts the server
- `cli_push_estimate.py` - Processes quotes (reused from CLI)

**Endpoints:**
- `GET /health` - Health check
- `GET /api/v1/status` - API status
- `POST /api/v1/estimate` - Create estimate
- `POST /api/v1/estimate/mock` - Create mock estimate
- `GET /api/v1/logs` - View logs

---

## 🔗 Module Dependencies

```
initial_oauth_setup.py
  ├── flask (for local callback server)
  ├── requests (for OAuth API calls)
  └── dotenv (for .env file)

oauth.py
  ├── requests (for token refresh)
  ├── dotenv (for credentials)
  └── (saves to .token_cache.json)

quickbooks_client.py
  ├── oauth.py (for authentication)
  ├── requests (for API calls)
  └── dotenv (for configuration)

mapping.py
  └── (standalone, no external deps)

create_estimate.py
  ├── cli_push_estimate.py (for processing)
  └── (interactive input handling)

cli_push_estimate.py
  ├── mapping.py (for data transformation)
  └── quickbooks_client.py (for API calls)

api_server.py
  ├── flask (for REST API)
  ├── flask-cors (for CORS support)
  └── cli_push_estimate.py (for processing)
```

---

## 📊 Data Formats

### Input: Quote JSON

```json
{
  "customer": {
    "display_name": "John Doe",
    "email": "john@example.com",
    "phone": "416-555-0100"
  },
  "quote": {
    "reference": "GT-001",
    "date": "2025-11-17"
  },
  "items": [
    {
      "description": "Interior painting",
      "qty": 2,
      "unit_price": 150.0
    }
  ],
  "sustainability": {
    "trees": 1,
    "co2_tons": 0.1,
    "water_liters": 10
  },
  "currency": "CAD"
}
```

### Output: QuickBooks Estimate Format

```json
{
  "CustomerRef": {"value": "123"},
  "DocNumber": "GT-001",
  "TxnDate": "2025-11-17",
  "Line": [
    {
      "Description": "Interior painting",
      "DetailType": "SalesItemLineDetail",
      "Amount": 300.0,
      "SalesItemLineDetail": {
        "Qty": 2,
        "UnitPrice": 150.0,
        "ItemRef": {"name": "Interior painting"}
      }
    }
  ],
  "CurrencyRef": {"value": "CAD"}
}
```

---

## 🎯 Key Functions

### `oauth.py`
- `get_access_token()` - Gets valid access token (uses cache, refreshes if needed)
- `refresh_access_token()` - Exchanges refresh token for new access token
- `get_auth_header()` - Returns Authorization header for API calls
- `_load_token_cache()` - Loads cached tokens from file
- `_save_token_cache()` - Saves tokens to file

### `quickbooks_client.py`
- `get_company_info()` - Tests connection, returns company info
- `get_or_create_customer()` - Finds existing or creates new customer
- `create_estimate()` - Creates estimate in QuickBooks
- `get_estimate_pdf()` - Downloads estimate PDF
- `query_customers()` - Lists all customers
- `_make_request()` - Internal function for API calls

### `mapping.py`
- `validate_quote_data()` - Validates JSON structure
- `map_quote_to_qbo_estimate()` - Transforms JSON to QuickBooks format
- `calculate_subtotal()` - Calculates total from items
- `extract_customer_info()` - Extracts customer data

### `create_estimate.py`
- `create_estimate_interactive()` - Interactive mode (simplified input)
- `main()` - Main entry point

### `cli_push_estimate.py`
- `process_quote()` - Main processing function
- `process_mock()` - Creates mock PDF (no API call)
- `process_quickbooks()` - Creates real estimate
- `append_log()` - Logs to CSV

### `api_server.py`
- `/health` - Health check endpoint
- `/api/v1/status` - API status and connection info
- `/api/v1/estimate` - Create estimate (POST)
- `/api/v1/estimate/mock` - Create mock estimate (POST)
- `/api/v1/logs` - View recent logs (GET)

---

## 🔄 Common Workflows

### Workflow 1: First-Time Setup
1. Install dependencies → `pip3 install -r requirements_txt.txt`
2. Copy `.env.example` to `.env`
3. Add `QBO_CLIENT_ID` and `QBO_CLIENT_SECRET` to `.env`
4. Run OAuth setup → `python3 initial_oauth_setup.py`
5. Set token cache → `python3 set_token_cache.py`
6. Test connection → `python3 quickbooks_client.py`

### Workflow 2: Create Estimate via CLI
1. Prepare JSON file with quote data
2. Run CLI → `python3 create_estimate.py --json quote.json`
3. Check output PDF in `Quotes/` folder
4. View logs in `logs/quotes_log.csv`

### Workflow 3: Create Estimate via API Server
1. Start server → `python3 start_server.py`
2. Send HTTP POST to `http://localhost:5000/api/v1/estimate`
3. Receive JSON response
4. Server logs to CSV automatically

### Workflow 4: Find Estimates
1. List all → `python3 find_estimate.py --list`
2. Find specific → `python3 find_estimate.py --doc-number GT-001`
3. Or use QuickBooks web: https://app.sandbox.intuit.com

---

## 🔐 Security & Configuration

### Files to Protect (Never Commit):
- `.env` - Contains Client ID, Secret, Refresh Token, Realm ID
- `.token_cache.json` - Contains cached access tokens

### Files Safe to Share:
- `.env.example` - Template with placeholders
- All `.py` files
- All `.md` files
- `requirements_txt.txt`
- `samples/` folder

### Configuration:
All configuration is in `.env`:
```bash
QBO_CLIENT_ID=your_client_id
QBO_CLIENT_SECRET=your_client_secret
QBO_REFRESH_TOKEN=your_refresh_token
QBO_REALM_ID=your_realm_id
QBO_MODE=sandbox  # or 'production'
```

---

## 📦 Output Files

### Logs (`logs/quotes_log.csv`)
CSV file with columns:
- `timestamp` - When estimate was created
- `reference` - Quote reference (Doc Number)
- `customer_name` - Customer name
- `items_count` - Number of line items
- `subtotal` - Total amount
- `currency` - Currency code
- `status` - Status (created, mock_created, error)
- `pdf_path` - Path to PDF file
- `qbo_estimate_id` - QuickBooks Estimate ID
- `error` - Error message (if any)

### PDFs (`Quotes/`)
- `Estimate_<reference>.pdf` - Downloaded estimate PDFs

---

## 🚀 Deployment

### Local Development
```bash
python3 start_server.py
```

### Production Deployment
- Use `Procfile` for Heroku/Railway
- Set environment variables (not `.env` file)
- Use `runtime.txt` for Python version

---

**This architecture supports both CLI and API usage, with persistent token caching and comprehensive logging.**
