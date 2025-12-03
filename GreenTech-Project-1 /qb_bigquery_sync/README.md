# QuickBooks to BigQuery Synchronizer

A standalone Python application that synchronizes QuickBooks Online estimates to Google BigQuery.

## Overview

This synchronizer fetches all estimates from QuickBooks Online and uploads them to a BigQuery table. It's designed to run as a scheduled job (cron, Cloud Scheduler, etc.) or manually.

## Features

- ✅ Fetches all estimates from QuickBooks Online via API
- ✅ Automatically handles pagination
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
- Connect to QuickBooks
- Fetch all estimates
- Upload to `greentech.estimates` table in BigQuery
- Create the table if it doesn't exist

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

- `--batch-size`: Number of estimates per API call (1-1000, default: 100)
- `--limit`: Limit number of estimates to sync (0 = all, default: 0)
- `--bq-project`: BigQuery project ID (defaults to application default)
- `--bq-dataset`: BigQuery dataset ID (default: greentech)
- `--bq-table`: BigQuery table ID (default: estimates)

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

The synchronizer creates a table with the following schema:

- `estimate` (JSON, REQUIRED): Full QuickBooks estimate object as JSON

Each estimate contains all fields from QuickBooks API, including:
- `Id`, `DocNumber`, `TxnDate`
- `CustomerRef`, `Line`, `TotalAmt`
- `TxnStatus`, `SyncToken`, `MetaData`
- And all other QuickBooks estimate fields

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


