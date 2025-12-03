# GreenTech Painting - Shiny Dashboard

An interactive R Shiny dashboard for visualizing KPIs, sales analytics, and business metrics from QuickBooks data stored in Google BigQuery.

## Overview

This dashboard provides real-time insights into:
- **Sales Performance**: Current month sales, year-over-year trends, top customers
- **Quote Analysis**: Quote status, conversion rates, unconfirmed quotes
- **Customer Analytics**: New vs returning clients, customer rankings
- **Environmental Impact**: Trees saved, CO₂ reduction, water conservation metrics
- **Product Performance**: Top products by sales volume

## Features

### Dashboard Tabs

1. **Overview**: High-level KPIs and key metrics
   - Current month sales and quotes
   - Conversion rates (quote to invoice)
   - Customer counts (new vs returning)
   - Environmental impact totals
   - Sales and quotes trends
   - Top products table

2. **Sales Analysis**: Detailed sales performance
   - Year sales by month (interactive chart)
   - Top customers by sales volume

3. **Quotes Analysis**: Quote tracking and status
   - Year quotes by month
   - Quote status distribution
   - Invoice status distribution

4. **Customers**: Customer management
   - Complete customer list with details
   - Sortable and searchable table

5. **Settings**: Configuration and controls
   - BigQuery connection status
   - Manual data refresh button

## Prerequisites

- **R** (version 4.0 or higher)
- **RStudio** (recommended) or R command line
- **Google Cloud Project** with BigQuery enabled
- **Service Account** credentials for BigQuery access
- **BigQuery Dataset** populated by the sync script (see [Data Synchronization](#data-synchronization))

## Installation

### 1. Install R Packages

Run the installation script:

```r
source("requirements.R")
```

Or install manually:

```r
install.packages(c(
  "shiny",
  "shinydashboard",
  "plotly",
  "DT",
  "dplyr",
  "bigrquery",
  "lubridate",
  "ggplot2",
  "scales"
))
```

### 2. Set Up BigQuery Credentials

You need a Google Cloud service account JSON key file with BigQuery access.

**Option 1: Environment Variable (Recommended)**
```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/service-account-key.json
```

**Option 2: Place in App Directory**
- Copy your service account JSON file to `greentech-bq.json` in the `shiny_dashboard` directory

**Option 3: Custom Path**
```bash
export BQ_CREDENTIALS_FILE=/path/to/your/credentials.json
```

### 3. Configure BigQuery Project and Dataset

The app uses environment variables with defaults:

```bash
export BQ_PROJECT="your-gcp-project-id"  # Default: greentech-478022
export BQ_DATASET="your-dataset-name"    # Default: greentech
```

Or edit the defaults in `app.R`:
```r
BQ_PROJECT <- Sys.getenv("BQ_PROJECT", "your-project-id")
BQ_DATASET <- Sys.getenv("BQ_DATASET", "your-dataset")
```

## Running the Dashboard

### From RStudio

1. Open `app.R` in RStudio
2. Click "Run App" button (top right of editor)
3. Or run: `shiny::runApp()`

### From Command Line

```bash
Rscript -e "shiny::runApp('.', port=3838, host='0.0.0.0')"
```

### From R Console

```r
shiny::runApp()
```

The dashboard will open in your default web browser, typically at `http://127.0.0.1:3838`

## Data Synchronization

The dashboard reads data from BigQuery tables that are populated by the `qb_bigquery_sync` sync script.

**How it works:**
1. The sync script (`qb_bigquery_sync/sync.py`) fetches data from QuickBooks Online
2. Data is transformed and loaded into 6 normalized BigQuery tables:
   - `quotes`: Quote/estimate header information
   - `invoices`: Invoice header information
   - `quote_lines`: Line items for quotes
   - `invoice_lines`: Line items for invoices
   - `customers`: Customer information
   - `environmental_impact`: Environmental metrics

3. The Shiny dashboard queries these tables to display real-time metrics

**To keep data fresh:**
- Run the sync script regularly (daily recommended)
- Use cron/scheduled tasks for automated syncing
- Click "Refresh Data" button in the Settings tab to reload queries

For more details on the sync process, see `../qb_bigquery_sync/README.md`

## Troubleshooting

### "BigQuery authentication error"

**Solution**: Ensure your credentials file is properly set:
```bash
# Check if environment variable is set
echo $GOOGLE_APPLICATION_CREDENTIALS

# Or verify file exists
ls -la greentech-bq.json
```

### "No data showing" or "Empty results"

**Possible causes:**
1. **No data in BigQuery**: Run the sync script first to populate tables
2. **Wrong project/dataset**: Verify `BQ_PROJECT` and `BQ_DATASET` settings
3. **Date mismatch**: The app uses local date (`Sys.Date()`) for current month calculations. Ensure your system date is correct.

### "Package not found" errors

**Solution**: Install missing packages:
```r
install.packages("package-name")
```

### Dashboard shows old data

**Solution**: 
- Click "Refresh Data" button in Settings tab
- Or restart the Shiny app to reload all queries

## Date Handling

The dashboard uses **local system date** (`Sys.Date()`) for "current month" calculations to avoid timezone issues. This ensures:
- Current month sales/quotes use your local date
- Year selector uses local year
- No discrepancies from BigQuery server timezone

## Security Notes

- ⚠️ **Never commit `greentech-bq.json`** to version control
- ⚠️ **Never commit service account keys**
- ✅ Use environment variables for credentials in production
- ✅ Restrict service account permissions to BigQuery only

## License

Part of GreenTech Painting project.

