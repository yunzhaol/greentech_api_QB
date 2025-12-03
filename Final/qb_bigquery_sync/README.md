# QuickBooks to BigQuery Synchronizer

A standalone Python application that synchronizes QuickBooks Online estimates/quotes and invoices to normalized Google BigQuery tables.

## Overview

This synchronizer fetches all estimates and invoices from QuickBooks Online and uploads them to normalized BigQuery tables. It's designed to run as a scheduled job (cron, Cloud Scheduler, etc.) or manually.

## How the Sync Works

The synchronization process follows these steps:

### 1. Fetch Data from QuickBooks

The sync script connects to QuickBooks Online via OAuth 2.0 and fetches:
- **All estimates/quotes** (with automatic pagination)
- **All invoices** (with automatic pagination)
- **Customer information** (extracted from quotes and invoices)

The script uses batch processing to efficiently fetch large amounts of data (default batch size: 100 records per API call).

### 2. Transform to Normalized Format

QuickBooks data is transformed into 6 normalized BigQuery tables:

- **`quotes`**: Quote/estimate header information
  - Fields: `quote_id`, `doc_number`, `txn_date`, `total_amt`, `txn_status`, `customer_id`, `customer_name`, etc.
  
- **`invoices`**: Invoice header information
  - Fields: `invoice_id`, `doc_number`, `txn_date`, `total_amt`, `txn_status`, `customer_id`, `customer_name`, etc.
  
- **`quote_lines`**: Line items for each quote
  - Fields: `quote_id`, `line_num`, `description`, `amount`, `qty`, `unit_price`, `item_ref_name`, etc.
  
- **`invoice_lines`**: Line items for each invoice
  - Fields: `invoice_id`, `line_num`, `description`, `amount`, `qty`, `unit_price`, `item_ref_name`, etc.
  
- **`customers`**: Customer information (deduplicated)
  - Fields: `customer_id`, `customer_name`, `email`, `phone`, `address`
  
- **`environmental_impact`**: Environmental metrics linked to quotes
  - Fields: `quote_id`, `trees`, `tons_c02`, `water_saved`

### 3. Upsert Logic (Duplicate Handling)

The sync uses an **insert-only** approach to avoid duplicates:

1. **Check existing records**: Before inserting, the script queries BigQuery to get all existing IDs
   - For quotes/invoices: checks `quote_id`/`invoice_id`
   - For lines: checks `quote_id + line_num` or `invoice_id + line_num` combinations
   - For customers: checks `customer_id`

2. **Filter new records**: Only records that don't already exist in BigQuery are inserted

3. **Batch insert**: New records are inserted using BigQuery's batch load API

**Why insert-only?**
- Avoids BigQuery streaming buffer limitations with UPDATE/DELETE operations
- Faster and more reliable for large datasets
- Idempotent: safe to run multiple times without creating duplicates
- If a record already exists, it's simply skipped

### 4. Table Creation

If tables don't exist, they are automatically created with the correct schema. Use `--no-create-tables` to skip this (useful if you manage schemas separately).

### 5. Execution Order

The sync processes data in this order:
1. **Customers** (upserted first, as they're referenced by quotes/invoices)
2. **Quotes** (with validation for missing IDs)
3. **Invoices**
4. **Quote lines**
5. **Invoice lines**
6. **Environmental impact**

### Running Multiple Times

The sync is **idempotent** - you can run it multiple times safely:
- First run: Inserts all records
- Subsequent runs: Only inserts new records, skips existing ones
- No data loss or duplication

This makes it perfect for scheduled jobs that run daily or hourly.

## Features

- ✅ Fetches all estimates/quotes and invoices from QuickBooks Online via API
- ✅ Automatically handles pagination
- ✅ Transforms data into 6 normalized BigQuery tables
- ✅ Upsert logic: inserts only new records, skips duplicates
- ✅ Idempotent: safe to run multiple times
- ✅ Uploads to BigQuery with automatic table creation
- ✅ OAuth 2.0 token management with automatic refresh
- ✅ Configurable via environment variables
- ✅ Standalone and deployable independently

## Prerequisites

- Python 3.11 or 3.12 (3.14+ not supported due to BigQuery library compatibility)
- QuickBooks Online account with API access
- Google Cloud Project with BigQuery enabled
- Service account credentials for BigQuery

## Installation

1. **Clone or copy this folder** to your deployment location

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

4. **Configure BigQuery credentials:**
   - Option 1: Set `GOOGLE_APPLICATION_CREDENTIALS` environment variable
     ```bash
     export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
     ```
   - Option 2: Add to `.env` file:
     ```
     GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
     ```

## Configuration

### Environment Variables

Create a `.env` file in this directory with the following:

```env
# QuickBooks OAuth Credentials
QBO_CLIENT_ID=your_client_id
QBO_CLIENT_SECRET=your_client_secret
QBO_REFRESH_TOKEN=your_refresh_token
QBO_REALM_ID=your_realm_id
QBO_MODE=sandbox  # or 'production'

# BigQuery (optional if using GOOGLE_APPLICATION_CREDENTIALS env var)
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
```

### Getting QuickBooks Credentials

1. **Client ID & Secret:** Get from [Intuit Developer Dashboard](https://developer.intuit.com)
2. **Realm ID:** Found in QuickBooks Online (Settings → Company → Company ID) or Developer Dashboard
3. **Refresh Token:** Run OAuth flow once using `initial_oauth_setup.py` from the main project

### BigQuery Setup

1. Create a service account in Google Cloud Console
2. Grant it BigQuery Data Editor and BigQuery Job User roles
3. Download the JSON key file
4. Set `GOOGLE_APPLICATION_CREDENTIALS` to point to this file

## Usage

### Basic Usage

```bash
python sync.py
```

This will:
- Connect to QuickBooks Online
- Fetch all estimates/quotes and invoices
- Transform data into normalized format (6 tables: quotes, invoices, quote_lines, invoice_lines, customers, environmental_impact)
- Upload to BigQuery dataset (default: `greentech`)
- Create tables if they don't exist
- Skip existing records (idempotent - safe to run multiple times)

### Advanced Usage

```bash
# Limit number of estimates
python sync.py --limit 50

# Custom BigQuery destination
python sync.py --bq-dataset my_dataset --bq-table my_estimates

# Custom project
python sync.py --bq-project my-gcp-project

# Adjust batch size for API calls
python sync.py --batch-size 250
```

### Command Line Options

- `--batch-size`: Number of records per API call (1-1000, default: 100)
- `--limit`: Limit number of estimates/invoices to sync (0 = all, default: 0)
- `--bq-project`: BigQuery project ID (defaults to application default)
- `--bq-dataset`: BigQuery dataset ID (default: greentech)
- `--no-create-tables`: Skip table creation (tables must already exist)

## Deployment

### Local/Scheduled Job

Add to crontab for daily sync:
```bash
0 2 * * * cd /path/to/qb_bigquery_sync && /usr/bin/python3 sync.py >> logs/sync.log 2>&1
```

### Cloud Functions / Cloud Run

1. Package the application
2. Deploy with environment variables configured
3. Set up Cloud Scheduler to trigger periodically

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "sync.py"]
```

## BigQuery Schema

The synchronizer creates 6 normalized tables with structured schemas:

### Quotes Table
- `quote_id` (STRING, REQUIRED): QuickBooks estimate ID
- `doc_number` (STRING): Document number
- `txn_date` (DATE): Transaction date
- `total_amt` (FLOAT): Total amount
- `txn_status` (STRING): Status (e.g., "Accepted", "Pending")
- `customer_id` (STRING): Customer ID reference
- `customer_name` (STRING): Customer name
- Plus many other fields (currency, subtotal, dates, etc.)

### Invoices Table
- `invoice_id` (STRING, REQUIRED): QuickBooks invoice ID
- Similar structure to quotes table
- Additional fields: `due_date`, `balance`, `ship_date`, etc.

### Quote Lines / Invoice Lines Tables
- `quote_id`/`invoice_id` (STRING, REQUIRED): Parent transaction ID
- `line_num` (INTEGER): Line number
- `description` (STRING): Line item description
- `amount` (FLOAT): Line amount
- `qty` (FLOAT): Quantity
- `unit_price` (FLOAT): Unit price
- `item_ref_name` (STRING): Item name
- Plus other fields (tax codes, discounts, etc.)

### Customers Table
- `customer_id` (STRING, REQUIRED): QuickBooks customer ID
- `customer_name` (STRING): Customer name
- `email` (STRING): Email address
- `phone` (STRING): Phone number
- `address` (STRING): Address

### Environmental Impact Table
- `quote_id` (STRING, REQUIRED): Quote ID reference
- `trees` (FLOAT): Number of trees equivalent
- `tons_c02` (FLOAT): Tons of CO₂ saved
- `water_saved` (FLOAT): Liters of water saved

For the complete schema definition, see `create_bigquery_schemas()` in `sync.py`.

## Troubleshooting

### Error: "QBO_REALM_ID not set"
- Check your `.env` file has `QBO_REALM_ID` set

### Error: "Token refresh failed"
- Your refresh token may have expired. Re-run OAuth flow to get a new one.

### Error: "google-cloud-bigquery is not installed"
- Run: `pip install google-cloud-bigquery`

### Error: "Metaclasses with custom tp_new are not supported"
- You're using Python 3.14+. Switch to Python 3.11 or 3.12.

### Error: "BigQuery insertion errors"
- Check that your service account has proper permissions
- Verify the table schema matches (should be single JSON column)

## Security Notes

- ⚠️ **Never commit `.env` file** to version control
- ⚠️ **Never commit service account JSON keys**
- ✅ Use environment variables or secure secret management in production
- ✅ Rotate refresh tokens regularly (they expire after ~100 days of inactivity)

## License

Part of GreenTech Painting project.


