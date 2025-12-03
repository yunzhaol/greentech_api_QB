#!/usr/bin/env Rscript
# GreenTech Painting - KPI Dashboard
# Shiny application to display KPIs from BigQuery

library(shiny)
library(shinydashboard)
library(plotly)
library(DT)
library(dplyr)
library(bigrquery)
library(lubridate)
library(ggplot2)

# ==================== Configuration ====================

# BigQuery Configuration
BQ_PROJECT <- Sys.getenv("BQ_PROJECT", "greentech-478022")
BQ_DATASET <- Sys.getenv("BQ_DATASET", "greentech")

# BigQuery Credentials
# Priority: 
# 1. GOOGLE_APPLICATION_CREDENTIALS (path to credentials file)
# 2. BQ_CREDENTIALS_FILE (custom credentials file path)
# 3. Default location (greentech-bq.json in app directory or parent qb_bigquery_sync folder)

GOOGLE_APPLICATION_CREDENTIALS <- Sys.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
BQ_CREDENTIALS_FILE <- Sys.getenv("BQ_CREDENTIALS_FILE", "greentech-bq.json")

if (GOOGLE_APPLICATION_CREDENTIALS != "" && file.exists(GOOGLE_APPLICATION_CREDENTIALS)) {
  # Use environment variable if set and file exists
  cat("Using BigQuery credentials from GOOGLE_APPLICATION_CREDENTIALS environment variable:", GOOGLE_APPLICATION_CREDENTIALS, "\n")
} else if (file.exists(BQ_CREDENTIALS_FILE)) {
  # Use credentials file in app directory
  Sys.setenv(GOOGLE_APPLICATION_CREDENTIALS = normalizePath(BQ_CREDENTIALS_FILE))
  cat("Using BigQuery credentials from file:", BQ_CREDENTIALS_FILE, "\n")
} else {
  # Try default location (same directory as sync script)
  default_creds <- file.path("..", "qb_bigquery_sync", "greentech-bq.json")
  if (file.exists(default_creds)) {
    Sys.setenv(GOOGLE_APPLICATION_CREDENTIALS = normalizePath(default_creds))
    cat("Using BigQuery credentials from default location:", default_creds, "\n")
  } else {
    cat("Warning: No BigQuery credentials file found. Please set GOOGLE_APPLICATION_CREDENTIALS or place greentech-bq.json in the app directory.\n")
  }
}

# Authenticate with BigQuery
auth_creds <- Sys.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
if (auth_creds != "" && file.exists(auth_creds)) {
  tryCatch({
    bq_auth(path = auth_creds)
    cat("BigQuery authentication successful using credentials file.\n")
  }, error = function(e) {
    cat("BigQuery authentication error:", e$message, "\n")
    cat("Attempting to use default authentication...\n")
    tryCatch({
      bq_auth()  # Try default authentication
    }, error = function(e2) {
      cat("Failed to authenticate with BigQuery:", e2$message, "\n")
    })
  })
} else {
  # Try default authentication (uses cached credentials or interactive auth)
  tryCatch({
    bq_auth()
    cat("BigQuery authentication successful using default method.\n")
  }, error = function(e) {
    cat("BigQuery authentication error:", e$message, "\n")
    cat("Please set up credentials file or GOOGLE_APPLICATION_CREDENTIALS environment variable.\n")
  })
}

# ==================== Helper Functions ====================

get_bq_data <- function(query) {
  # Execute BigQuery query and return results as data frame
  tryCatch({
    # Use bq_project_query to execute query
    bq_table <- bq_project_query(BQ_PROJECT, query)
    bq_table_download(bq_table)
  }, error = function(e) {
    # Note: showNotification only works in server context
    print(paste("BigQuery Error:", e$message))
    return(data.frame())
  })
}

get_current_month_sales <- function() {
  # Get total sales for current month from invoices
  # Use local date instead of BigQuery's CURRENT_DATE() to avoid timezone issues
  current_date <- Sys.Date()
  current_year <- year(current_date)
  current_month <- month(current_date)
  
  query <- sprintf("
    SELECT 
      COALESCE(SUM(total_amt), 0) as total_sales
    FROM `%s.%s.invoices`
    WHERE EXTRACT(YEAR FROM txn_date) = %d
      AND EXTRACT(MONTH FROM txn_date) = %d
  ", BQ_PROJECT, BQ_DATASET, current_year, current_month)
  
  result <- get_bq_data(query)
  if (nrow(result) > 0) {
    return(result$total_sales[1])
  }
  return(0)
}

get_current_month_quoted <- function() {
  # Get total quoted amount for current month from quotes
  # Use local date instead of BigQuery's CURRENT_DATE() to avoid timezone issues
  current_date <- Sys.Date()
  current_year <- year(current_date)
  current_month <- month(current_date)
  
  query <- sprintf("
    SELECT 
      COALESCE(SUM(total_amt), 0) as total_quoted
    FROM `%s.%s.quotes`
    WHERE EXTRACT(YEAR FROM txn_date) = %d
      AND EXTRACT(MONTH FROM txn_date) = %d
  ", BQ_PROJECT, BQ_DATASET, current_year, current_month)
  
  result <- get_bq_data(query)
  if (nrow(result) > 0) {
    return(result$total_quoted[1])
  }
  return(0)
}

get_year_sales_by_month <- function(year = NULL) {
  # Get sales by month for the year
  if (is.null(year)) {
    year <- year(Sys.Date())
  }
  # Convert to numeric in case it's a character from selectInput
  year <- as.numeric(year)
  
  query <- sprintf("
    SELECT 
      EXTRACT(MONTH FROM txn_date) as month,
      COALESCE(SUM(total_amt), 0) as total_sales,
      COUNT(*) as invoice_count
    FROM `%s.%s.invoices`
    WHERE EXTRACT(YEAR FROM txn_date) = %d
    GROUP BY month
    ORDER BY month
  ", BQ_PROJECT, BQ_DATASET, year)
  
  result <- get_bq_data(query)
  if (nrow(result) > 0) {
    result$month_name <- month.abb[result$month]
    return(result)
  }
  return(data.frame(month = 1:12, month_name = month.abb, total_sales = 0, invoice_count = 0))
}

get_year_quotes_by_month <- function(year = NULL) {
  # Get quotes by month for the year
  if (is.null(year)) {
    year <- year(Sys.Date())
  }
  # Convert to numeric in case it's a character from selectInput
  year <- as.numeric(year)
  
  query <- sprintf("
    SELECT 
      EXTRACT(MONTH FROM txn_date) as month,
      COALESCE(SUM(total_amt), 0) as total_quoted,
      COUNT(*) as quote_count
    FROM `%s.%s.quotes`
    WHERE EXTRACT(YEAR FROM txn_date) = %d
    GROUP BY month
    ORDER BY month
  ", BQ_PROJECT, BQ_DATASET, year)
  
  result <- get_bq_data(query)
  if (nrow(result) > 0) {
    result$month_name <- month.abb[result$month]
    return(result)
  }
  return(data.frame(month = 1:12, month_name = month.abb, total_quoted = 0, quote_count = 0))
}

get_top_customers <- function(limit = 10, year = NULL) {
  # Get top customers by sales
  if (is.null(year)) {
    year <- year(Sys.Date())
  }
  # Convert to numeric in case it's a character from selectInput
  year <- as.numeric(year)
  limit <- as.numeric(limit)
  
  query <- sprintf("
    SELECT 
      customer_name,
      COALESCE(SUM(total_amt), 0) as total_sales,
      COUNT(*) as invoice_count
    FROM `%s.%s.invoices`
    WHERE EXTRACT(YEAR FROM txn_date) = %d
      AND customer_name IS NOT NULL
    GROUP BY customer_name
    ORDER BY total_sales DESC
    LIMIT %d
  ", BQ_PROJECT, BQ_DATASET, year, limit)
  
  return(get_bq_data(query))
}

get_quote_to_invoice_conversion <- function(year = NULL) {
  # Calculate quote to invoice conversion rate
  if (is.null(year)) {
    year <- year(Sys.Date())
  }
  # Convert to numeric in case it's a character from selectInput
  year <- as.numeric(year)
  
  # Get total quoted
  quotes_query <- sprintf("
    SELECT COALESCE(SUM(total_amt), 0) as total_quoted
    FROM `%s.%s.quotes`
    WHERE EXTRACT(YEAR FROM txn_date) = %d
  ", BQ_PROJECT, BQ_DATASET, year)
  
  # Get total invoiced
  invoices_query <- sprintf("
    SELECT COALESCE(SUM(total_amt), 0) as total_invoiced
    FROM `%s.%s.invoices`
    WHERE EXTRACT(YEAR FROM txn_date) = %d
  ", BQ_PROJECT, BQ_DATASET, year)
  
  quoted <- get_bq_data(quotes_query)
  invoiced <- get_bq_data(invoices_query)
  
  total_quoted <- if (nrow(quoted) > 0) quoted$total_quoted[1] else 0
  total_invoiced <- if (nrow(invoiced) > 0) invoiced$total_invoiced[1] else 0
  
  if (total_quoted > 0) {
    conversion_rate <- (total_invoiced / total_quoted) * 100
  } else {
    conversion_rate <- 0
  }
  
  return(list(
    total_quoted = total_quoted,
    total_invoiced = total_invoiced,
    conversion_rate = conversion_rate
  ))
}

get_unconfirmed_quotes <- function() {
  # Get count of unconfirmed quotes (not Accepted)
  # Use local date instead of BigQuery's CURRENT_DATE() to avoid timezone issues
  current_date <- Sys.Date()
  current_year <- year(current_date)
  current_month <- month(current_date)
  
  query <- sprintf("
    SELECT COUNT(*) as count
    FROM `%s.%s.quotes`
    WHERE EXTRACT(YEAR FROM txn_date) = %d
      AND EXTRACT(MONTH FROM txn_date) = %d
      AND (txn_status IS NULL OR txn_status != 'Accepted')
  ", BQ_PROJECT, BQ_DATASET, current_year, current_month)
  
  result <- get_bq_data(query)
  if (nrow(result) > 0) {
    return(result$count[1])
  }
  return(0)
}

get_new_clients <- function() {
  # Get count of new clients (first transaction is in current month)
  # Use local date instead of BigQuery's CURRENT_DATE() to avoid timezone issues
  current_date <- Sys.Date()
  current_year <- year(current_date)
  current_month <- month(current_date)
  
  query <- sprintf("
    WITH first_transactions AS (
      SELECT 
        customer_id,
        MIN(txn_date) as first_txn_date
      FROM (
        SELECT customer_id, txn_date FROM `%s.%s.quotes`
        UNION ALL
        SELECT customer_id, txn_date FROM `%s.%s.invoices`
      )
      WHERE customer_id IS NOT NULL
      GROUP BY customer_id
    )
    SELECT COUNT(DISTINCT customer_id) as count
    FROM first_transactions
    WHERE EXTRACT(YEAR FROM first_txn_date) = %d
      AND EXTRACT(MONTH FROM first_txn_date) = %d
  ", BQ_PROJECT, BQ_DATASET, BQ_PROJECT, BQ_DATASET, current_year, current_month)
  
  result <- get_bq_data(query)
  if (nrow(result) > 0) {
    return(result$count[1])
  }
  return(0)
}

get_returning_clients <- function() {
  # Get count of returning clients (first transaction is before current month)
  # Use local date instead of BigQuery's CURRENT_DATE() to avoid timezone issues
  current_date <- Sys.Date()
  current_year <- year(current_date)
  current_month <- month(current_date)
  
  query <- sprintf("
    WITH first_transactions AS (
      SELECT 
        customer_id,
        MIN(txn_date) as first_txn_date
      FROM (
        SELECT customer_id, txn_date FROM `%s.%s.quotes`
        UNION ALL
        SELECT customer_id, txn_date FROM `%s.%s.invoices`
      )
      WHERE customer_id IS NOT NULL
      GROUP BY customer_id
    )
    SELECT COUNT(DISTINCT customer_id) as count
    FROM first_transactions
    WHERE EXTRACT(YEAR FROM first_txn_date) < %d
       OR (EXTRACT(YEAR FROM first_txn_date) = %d
           AND EXTRACT(MONTH FROM first_txn_date) < %d)
  ", BQ_PROJECT, BQ_DATASET, BQ_PROJECT, BQ_DATASET, current_year, current_year, current_month)
  
  result <- get_bq_data(query)
  if (nrow(result) > 0) {
    return(result$count[1])
  }
  return(0)
}

get_top_products <- function(limit = 10) {
  # Get top products by sales amount from invoice lines
  query <- sprintf("
    SELECT 
      COALESCE(item_ref_name, description, 'Unknown') as product_name,
      SUM(amount) as total_sales,
      SUM(qty) as total_quantity,
      COUNT(*) as transaction_count
    FROM `%s.%s.invoice_lines`
    WHERE item_ref_name IS NOT NULL OR description IS NOT NULL
    GROUP BY product_name
    ORDER BY total_sales DESC
    LIMIT %d
  ", BQ_PROJECT, BQ_DATASET, limit)
  
  return(get_bq_data(query))
}

get_total_trees <- function() {
  # Get total trees saved from environmental impact
  query <- sprintf("
    SELECT COALESCE(SUM(trees), 0) as total_trees
    FROM `%s.%s.environmental_impact`
    WHERE trees IS NOT NULL
  ", BQ_PROJECT, BQ_DATASET)
  
  result <- get_bq_data(query)
  if (nrow(result) > 0) {
    return(result$total_trees[1])
  }
  return(0)
}

get_total_water_saved <- function() {
  # Get total water saved from environmental impact
  query <- sprintf("
    SELECT COALESCE(SUM(water_saved), 0) as total_water
    FROM `%s.%s.environmental_impact`
    WHERE water_saved IS NOT NULL
  ", BQ_PROJECT, BQ_DATASET)
  
  result <- get_bq_data(query)
  if (nrow(result) > 0) {
    return(result$total_water[1])
  }
  return(0)
}

get_total_co2_saved <- function() {
  # Get total CO2 saved from environmental impact
  query <- sprintf("
    SELECT COALESCE(SUM(tons_c02), 0) as total_co2
    FROM `%s.%s.environmental_impact`
    WHERE tons_c02 IS NOT NULL
  ", BQ_PROJECT, BQ_DATASET)
  
  result <- get_bq_data(query)
  if (nrow(result) > 0) {
    return(result$total_co2[1])
  }
  return(0)
}

# ==================== UI ====================

ui <- dashboardPage(
  dashboardHeader(title = "Dashboard"),
  
  dashboardSidebar(
    sidebarMenu(
      menuItem("Overview", tabName = "overview", icon = icon("dashboard")),
      menuItem("Sales Analysis", tabName = "sales", icon = icon("chart-line")),
      menuItem("Quotes Analysis", tabName = "quotes", icon = icon("file-invoice")),
      menuItem("Customers", tabName = "customers", icon = icon("users")),
      menuItem("Settings", tabName = "settings", icon = icon("cog"))
    ),
    br(),
    selectInput("year_select", "Select Year:", 
                choices = (year(Sys.Date())-2):year(Sys.Date()),
                selected = year(Sys.Date()))
  ),
  
  dashboardBody(
    tags$head(
      tags$style(HTML("
        .content-wrapper, .right-side {
          background-color: #f4f4f4;
        }
      "))
    ),
    
    tabItems(
      # Overview Tab
      tabItem(tabName = "overview",
        fluidRow(
          valueBoxOutput("current_month_sales", width = 3),
          valueBoxOutput("current_month_quoted", width = 3),
          valueBoxOutput("conversion_rate", width = 3),
          valueBoxOutput("total_customers", width = 3)
        ),
        fluidRow(
          valueBoxOutput("unconfirmed_quotes", width = 4),
          valueBoxOutput("new_clients", width = 4),
          valueBoxOutput("returning_clients", width = 4)
        ),
        fluidRow(
          valueBoxOutput("total_trees", width = 4),
          valueBoxOutput("total_water_saved", width = 4),
          valueBoxOutput("total_co2_saved", width = 4)
        ),
        fluidRow(
          box(
            title = "Sales by Month (Current Year)", 
            status = "primary", 
            solidHeader = TRUE,
            width = 6,
            plotlyOutput("sales_by_month_plot")
          ),
          box(
            title = "Quotes by Month (Current Year)", 
            status = "info", 
            solidHeader = TRUE,
            width = 6,
            plotlyOutput("quotes_by_month_plot")
          )
        ),
        fluidRow(
          box(
            title = "Sales vs Quotes Comparison", 
            status = "success", 
            solidHeader = TRUE,
            width = 6,
            plotlyOutput("sales_vs_quotes_plot")
          ),
          box(
            title = "Top Products by Sales", 
            status = "warning", 
            solidHeader = TRUE,
            width = 6,
            DT::dataTableOutput("top_products_table")
          )
        )
      ),
      
      # Sales Analysis Tab
      tabItem(tabName = "sales",
        fluidRow(
          box(
            title = "Year Sales by Month", 
            status = "primary", 
            solidHeader = TRUE,
            width = 12,
            plotlyOutput("year_sales_plot")
          )
        ),
        fluidRow(
          box(
            title = "Top Customers by Sales", 
            status = "primary", 
            solidHeader = TRUE,
            width = 12,
            DT::dataTableOutput("top_customers_table")
          )
        )
      ),
      
      # Quotes Analysis Tab
      tabItem(tabName = "quotes",
        fluidRow(
          box(
            title = "Year Quotes by Month", 
            status = "info", 
            solidHeader = TRUE,
            width = 12,
            plotlyOutput("year_quotes_plot")
          )
        ),
        fluidRow(
          box(
            title = "Quote Status Distribution", 
            status = "info", 
            solidHeader = TRUE,
            width = 6,
            plotlyOutput("quote_status_plot")
          ),
          box(
            title = "Invoice Status Distribution", 
            status = "primary", 
            solidHeader = TRUE,
            width = 6,
            plotlyOutput("invoice_status_plot")
          )
        )
      ),
      
      # Customers Tab
      tabItem(tabName = "customers",
        fluidRow(
          box(
            title = "Top Customers", 
            status = "primary", 
            solidHeader = TRUE,
            width = 12,
            DT::dataTableOutput("customers_table")
          )
        )
      ),
      
      # Settings Tab
      tabItem(tabName = "settings",
        fluidRow(
          box(
            title = "BigQuery Configuration", 
            status = "info", 
            solidHeader = TRUE,
            width = 12,
            p("Project:", strong(BQ_PROJECT)),
            p("Dataset:", strong(BQ_DATASET)),
            p("Credentials:", strong(ifelse(Sys.getenv("GOOGLE_APPLICATION_CREDENTIALS") != "", 
                                          "Set via GOOGLE_APPLICATION_CREDENTIALS", 
                                          "Not set"))),
            br(),
            actionButton("refresh_data", "Refresh Data", icon = icon("refresh"))
          )
        )
      )
    )
  )
)

# ==================== Server ====================

server <- function(input, output, session) {
  
  # Reactive values
  values <- reactiveValues(
    refresh_trigger = 0
  )
  
  # Refresh trigger
  observeEvent(input$refresh_data, {
    values$refresh_trigger <- values$refresh_trigger + 1
    showNotification("Data refreshed!", type = "message")
  })
  
  # Current Month Sales
  output$current_month_sales <- renderValueBox({
    sales <- get_current_month_sales()
    valueBox(
      value = paste0("$", format(round(sales, 2), big.mark = ",")),
      subtitle = "Current Month Sales",
      icon = icon("dollar-sign"),
      color = "green"
    )
  })
  
  # Current Month Quoted
  output$current_month_quoted <- renderValueBox({
    quoted <- get_current_month_quoted()
    valueBox(
      value = paste0("$", format(round(quoted, 2), big.mark = ",")),
      subtitle = "Current Month Quoted",
      icon = icon("file-invoice-dollar"),
      color = "blue"
    )
  })
  
  # Conversion Rate
  output$conversion_rate <- renderValueBox({
    conversion <- get_quote_to_invoice_conversion(input$year_select)
    valueBox(
      value = paste0(round(conversion$conversion_rate, 1), "%"),
      subtitle = "Quote to Invoice Conversion",
      icon = icon("percentage"),
      color = "yellow"
    )
  })
  
  # Total Customers
  output$total_customers <- renderValueBox({
    query <- sprintf("
      SELECT COUNT(DISTINCT customer_id) as total
      FROM `%s.%s.customers`
    ", BQ_PROJECT, BQ_DATASET)
    result <- get_bq_data(query)
    total <- if (nrow(result) > 0) result$total[1] else 0
    valueBox(
      value = total,
      subtitle = "Total Customers",
      icon = icon("users"),
      color = "purple"
    )
  })
  
  # Unconfirmed Quotes
  output$unconfirmed_quotes <- renderValueBox({
    count <- get_unconfirmed_quotes()
    valueBox(
      value = count,
      subtitle = "Unconfirmed Quotes (This Month)",
      icon = icon("exclamation-triangle"),
      color = "orange"
    )
  })
  
  # New Clients
  output$new_clients <- renderValueBox({
    count <- get_new_clients()
    valueBox(
      value = count,
      subtitle = "New Clients (This Month)",
      icon = icon("user-plus"),
      color = "teal"
    )
  })
  
  # Returning Clients
  output$returning_clients <- renderValueBox({
    count <- get_returning_clients()
    valueBox(
      value = count,
      subtitle = "Returning Clients",
      icon = icon("user-check"),
      color = "navy"
    )
  })
  
  # Total Trees
  output$total_trees <- renderValueBox({
    trees <- get_total_trees()
    valueBox(
      value = format(round(trees, 0), big.mark = ","),
      subtitle = "Total Trees Saved",
      icon = icon("tree"),
      color = "green"
    )
  })
  
  # Total Water Saved
  output$total_water_saved <- renderValueBox({
    water <- get_total_water_saved()
    valueBox(
      value = paste0(format(round(water, 0), big.mark = ","), "L"),
      subtitle = "Total Water Saved",
      icon = icon("tint"),
      color = "blue"
    )
  })
  
  # Total CO2 Saved
  output$total_co2_saved <- renderValueBox({
    co2 <- get_total_co2_saved()
    valueBox(
      value = paste0(format(round(co2, 2), big.mark = ","), " tons"),
      subtitle = "Total CO₂ Saved",
      icon = icon("leaf"),
      color = "olive"
    )
  })
  
  # Top Products Table
  output$top_products_table <- DT::renderDataTable({
    data <- get_top_products(limit = 10)
    if (nrow(data) > 0) {
      data$total_sales <- paste0("$", format(round(data$total_sales, 2), big.mark = ","))
      data$total_quantity <- format(round(data$total_quantity, 2), big.mark = ",")
      colnames(data) <- c("Product Name", "Total Sales", "Total Quantity", "Transactions")
    }
    DT::datatable(data, options = list(pageLength = 10, order = list(1, 'desc'))) %>%
      DT::formatStyle("Total Sales", fontWeight = "bold")
  })
  
  # Sales by Month Plot
  output$sales_by_month_plot <- renderPlotly({
    data <- get_year_sales_by_month(input$year_select)
    p <- ggplot(data, aes(x = month_name, y = total_sales)) +
      geom_col(fill = "#2E7D32", alpha = 0.8) +
      geom_line(group = 1, color = "#1B5E20", size = 1) +
      geom_point(color = "#1B5E20", size = 3) +
      labs(x = "Month", y = "Sales ($)", title = paste("Sales by Month -", input$year_select)) +
      theme_minimal() +
      theme(axis.text.x = element_text(angle = 45, hjust = 1))
    ggplotly(p)
  })
  
  # Quotes by Month Plot
  output$quotes_by_month_plot <- renderPlotly({
    data <- get_year_quotes_by_month(input$year_select)
    p <- ggplot(data, aes(x = month_name, y = total_quoted)) +
      geom_col(fill = "#1976D2", alpha = 0.8) +
      geom_line(group = 1, color = "#0D47A1", size = 1) +
      geom_point(color = "#0D47A1", size = 3) +
      labs(x = "Month", y = "Quoted ($)", title = paste("Quotes by Month -", input$year_select)) +
      theme_minimal() +
      theme(axis.text.x = element_text(angle = 45, hjust = 1))
    ggplotly(p)
  })
  
  # Sales vs Quotes Comparison
  output$sales_vs_quotes_plot <- renderPlotly({
    sales_data <- get_year_sales_by_month(input$year_select)
    quotes_data <- get_year_quotes_by_month(input$year_select)
    
    combined <- merge(sales_data, quotes_data, by = "month", all = TRUE)
    combined$month_name <- month.abb[combined$month]
    
    p <- ggplot(combined, aes(x = month_name)) +
      geom_col(aes(y = total_sales, fill = "Sales"), alpha = 0.7, position = "dodge") +
      geom_col(aes(y = total_quoted, fill = "Quoted"), alpha = 0.7, position = "dodge") +
      scale_fill_manual(values = c("Sales" = "#2E7D32", "Quoted" = "#1976D2")) +
      labs(x = "Month", y = "Amount ($)", title = paste("Sales vs Quotes -", input$year_select), fill = "Type") +
      theme_minimal() +
      theme(axis.text.x = element_text(angle = 45, hjust = 1), legend.position = "bottom")
    ggplotly(p)
  })
  
  # Year Sales Plot
  output$year_sales_plot <- renderPlotly({
    data <- get_year_sales_by_month(input$year_select)
    p <- ggplot(data, aes(x = month_name, y = total_sales)) +
      geom_col(fill = "#2E7D32", alpha = 0.8) +
      geom_text(aes(label = paste0("$", format(round(total_sales), big.mark = ","))), 
                vjust = -0.5, size = 3) +
      labs(x = "Month", y = "Sales ($)", title = paste("Sales by Month -", input$year_select)) +
      theme_minimal() +
      theme(axis.text.x = element_text(angle = 45, hjust = 1))
    ggplotly(p)
  })
  
  # Year Quotes Plot
  output$year_quotes_plot <- renderPlotly({
    data <- get_year_quotes_by_month(input$year_select)
    p <- ggplot(data, aes(x = month_name, y = total_quoted)) +
      geom_col(fill = "#1976D2", alpha = 0.8) +
      geom_text(aes(label = paste0("$", format(round(total_quoted), big.mark = ","))), 
                vjust = -0.5, size = 3) +
      labs(x = "Month", y = "Quoted ($)", title = paste("Quotes by Month -", input$year_select)) +
      theme_minimal() +
      theme(axis.text.x = element_text(angle = 45, hjust = 1))
    ggplotly(p)
  })
  
  # Top Customers Table
  output$top_customers_table <- DT::renderDataTable({
    data <- get_top_customers(limit = 20, year = input$year_select)
    if (nrow(data) > 0) {
      data$total_sales <- paste0("$", format(round(data$total_sales, 2), big.mark = ","))
      colnames(data) <- c("Customer Name", "Total Sales", "Invoice Count")
    }
    DT::datatable(data, options = list(pageLength = 10, order = list(1, 'desc')))
  })
  
  # Customers Table
  output$customers_table <- DT::renderDataTable({
    query <- sprintf("
      SELECT 
        customer_name,
        (SELECT COUNT(*) FROM `%s.%s.quotes` q WHERE q.customer_id = c.customer_id) as quote_count,
        (SELECT COUNT(*) FROM `%s.%s.invoices` i WHERE i.customer_id = c.customer_id) as invoice_count,
        (SELECT COALESCE(SUM(total_amt), 0) FROM `%s.%s.invoices` i WHERE i.customer_id = c.customer_id) as total_sales
      FROM `%s.%s.customers` c
      ORDER BY total_sales DESC
      LIMIT 50
    ", BQ_PROJECT, BQ_DATASET, BQ_PROJECT, BQ_DATASET, BQ_PROJECT, BQ_DATASET, BQ_PROJECT, BQ_DATASET)
    
    data <- get_bq_data(query)
    if (nrow(data) > 0) {
      data$total_sales <- paste0("$", format(round(data$total_sales, 2), big.mark = ","))
      colnames(data) <- c("Customer Name", "Quotes", "Invoices", "Total Sales")
    }
    DT::datatable(data, options = list(pageLength = 15, order = list(3, 'desc')))
  })
  
  # Quote Status Distribution
  output$quote_status_plot <- renderPlotly({
    year <- as.numeric(input$year_select)
    query <- sprintf("
      SELECT 
        txn_status,
        COUNT(*) as count
      FROM `%s.%s.quotes`
      WHERE EXTRACT(YEAR FROM txn_date) = %d
      GROUP BY txn_status
    ", BQ_PROJECT, BQ_DATASET, year)
    
    data <- get_bq_data(query)
    if (nrow(data) > 0) {
      p <- plot_ly(data, labels = ~txn_status, values = ~count, type = "pie",
                   textinfo = "label+percent") %>%
        layout(title = paste("Quote Status -", input$year_select))
    } else {
      p <- plot_ly() %>% layout(title = "No data available")
    }
    p
  })
  
  # Invoice Status Distribution
  output$invoice_status_plot <- renderPlotly({
    year <- as.numeric(input$year_select)
    query <- sprintf("
      SELECT 
        txn_status,
        COUNT(*) as count
      FROM `%s.%s.invoices`
      WHERE EXTRACT(YEAR FROM txn_date) = %d
      GROUP BY txn_status
    ", BQ_PROJECT, BQ_DATASET, year)
    
    data <- get_bq_data(query)
    if (nrow(data) > 0) {
      p <- plot_ly(data, labels = ~txn_status, values = ~count, type = "pie",
                   textinfo = "label+percent") %>%
        layout(title = paste("Invoice Status -", input$year_select))
    } else {
      p <- plot_ly() %>% layout(title = "No data available")
    }
    p
  })
}

# ==================== Run App ====================

shinyApp(ui = ui, server = server)

