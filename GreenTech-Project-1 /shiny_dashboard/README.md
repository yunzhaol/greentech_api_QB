# GreenTech Painting - KPI Dashboard

A Shiny dashboard application to visualize KPIs from QuickBooks data stored in BigQuery.

## Features

- 📊 **Current Month KPIs**: Sales, quotes, conversion rates
- 📈 **Sales Analysis**: Monthly sales trends, top customers
- 📋 **Quotes Analysis**: Monthly quote trends, status distribution
- 👥 **Customer Analytics**: Top customers by sales, customer overview
- 🔄 **Real-time Data**: Connects directly to BigQuery for live data

## Prerequisites

- R (version 4.0 or higher)
- BigQuery credentials configured (via `GOOGLE_APPLICATION_CREDENTIALS` environment variable)
- Access to the BigQuery dataset containing QuickBooks data

## Installation

1. **Install R packages:**
   ```r
   source("requirements.R")
   ```
   
   Or manually:
   ```r
   install.packages(c("shiny", "shinydashboard", "plotly", "DT", "dplyr", 
                     "bigrquery", "lubridate", "ggplot2"))
   ```

2. **Set up BigQuery credentials** (choose one method):
   
   **Option A: Credentials file (recommended)**
   - Place your BigQuery service account JSON file in the `shiny_dashboard` folder as `greentech-bq.json`
   - Or copy it from `../qb_bigquery_sync/greentech-bq.json`
   - The app will automatically detect and use it
   
   **Option B: Environment variable**
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
   ```
   
   **Option C: Custom credentials file location**
   ```bash
   export BQ_CREDENTIALS_FILE=/path/to/your-credentials.json
   ```

3. **Configure BigQuery project and dataset** (optional):
   - Edit `app.R` to change `BQ_PROJECT` and `BQ_DATASET` defaults
   - Or set environment variables: `BQ_PROJECT` and `BQ_DATASET`

## Usage

### Run Locally

```r
shiny::runApp("app.R")
```

Or from command line:
```bash
Rscript -e "shiny::runApp('app.R', port=3838, host='0.0.0.0')"
```

### Deploy to Shiny Server

1. Copy the `shiny_dashboard` folder to your Shiny Server directory
2. Ensure R packages are installed on the server
3. Set environment variables for BigQuery credentials
4. Access via: `http://your-server:3838/shiny_dashboard`

## Dashboard Sections

### Overview
- Current month sales and quotes
- Quote to invoice conversion rate
- Total customers
- Sales and quotes trends by month
- Comparison charts

### Sales Analysis
- Year sales by month (bar chart)
- Top customers by sales (data table)

### Quotes Analysis
- Year quotes by month (bar chart)
- Quote status distribution (pie chart)
- Invoice status distribution (pie chart)

### Customers
- Customer overview table with quote/invoice counts and total sales

## Configuration

### Environment Variables

- `GOOGLE_APPLICATION_CREDENTIALS`: Path to BigQuery service account JSON key
- `BQ_PROJECT`: BigQuery project ID (default: greentech-478022)
- `BQ_DATASET`: BigQuery dataset ID (default: greentech)

### Customization

Edit `app.R` to:
- Add new KPIs
- Modify chart styles
- Add new data sources
- Customize dashboard layout

## Troubleshooting

### Error: "BigQuery authentication failed"
- Check that `GOOGLE_APPLICATION_CREDENTIALS` is set correctly
- Verify the service account has BigQuery Data Viewer and Job User roles

### Error: "Table not found"
- Verify the dataset and table names match your BigQuery setup
- Check that the synchronizer has populated the tables

### Charts not displaying
- Check BigQuery connection
- Verify data exists in the tables
- Check R console for error messages

## License

Part of GreenTech Painting project.

