<<<<<<< HEAD
# Global Superstore — Business Intelligence & Analytics

A Python and Streamlit business intelligence application for exploring sales, profit, customer value, products, geography, shipping, and data quality. The application uses interactive Plotly visualizations and SQLite; it does not use Power BI or Tableau.

## Technology

Python 3.10+, Streamlit, Pandas, NumPy, Plotly, openpyxl, ReportLab, and SQLite. Optional MySQL connectivity remains available. The sales forecast uses a NumPy least-squares model; scikit-learn is not required.

## Dataset

The app loads `data/Global_Superstore2.xlsx` first and falls back to `data/Global_Superstore2.csv` if the workbook cannot be read. A compatible CSV can also be uploaded in the sidebar. Paths are resolved relative to the project. Streamlit caches the loaded and cleaned dataset and invalidates the cache when the source files change.

`Order ID`, `Order Date`, `Sales`, and `Profit` are essential. Filters, charts, and query examples that depend on other fields are enabled only when those fields exist. Dates are parsed day-first for the supplied data; CSVs encoded as UTF-8 or Windows-1252 are supported. Original dataset files are read-only from the app.

## Dashboard

The navy-and-blue interface opens directly to Executive Overview, with all pages immediately available in the sidebar. Shared date, country, region, market, category, sub-category, segment, and shipping-mode filters can be reset in the sidebar. KPI cards compare the active date range with the immediately preceding range using the same dimension filters; a comparison is shown only when prior-period records exist. Filtered data can be downloaded as CSV, Excel, or a PDF summary report.

1. **Executive Overview** — sales, profit, orders, customers, average order value, weighted margin, trends, regional results, product leaders, and dynamically calculated insights.
2. **Sales & Forecasting** — monthly, quarterly, and yearly trends; month-over-month, quarter-over-quarter, and year-over-year growth; sales mix; product leaders and laggards; 3- or 6-month forecast.
3. **Profitability** — weighted margins, profit by category and region, margin heatmap, loss-making products, high-sales/low-margin watchlist, and discount-profit association.
4. **Customer Intelligence** — unique and repeat customers, purchase frequency, spending, top customers by sales/profit, searchable customer results, and RFM segments.
5. **Product Performance** — product rankings, category contribution, searchable catalogue, sales/profit matrix, and cumulative Pareto contribution.
6. **Geographic Analytics** — country map and sales/profit analysis by country, market, and region.
7. **Shipping & Operations** — shipping-mode sales and profit, shipping cost, delivery duration, regional delivery speed, and order priority.
8. **SQL Insights** — 35 curated SQL analyses and a read-only SQL explorer against the currently filtered SQLite `orders` table. Queries requiring absent optional fields are hidden. Custom SQL is constrained to reads from `orders`, a five-second execution budget, and at most 10,000 rows.
9. **Data Explorer** — source and cleaned previews, schema, missing values, cleaning report, and CSV/Excel exports.
10. **BI Assistant** — deterministic answers to supported business questions, computed from the current filters.
11. **Data Management** — CSV/XLSX validation, upload history, and dataset activation.

The application has no login, sign-up, accounts, authentication, or role-based restrictions. Data Management is available to every person who can reach the Streamlit app, so deploy it only in an environment appropriate for unrestricted dataset uploads and activation. Uploaded datasets are stored with generated filenames in `data/uploads/`; activation does not overwrite the supplied Excel or CSV files.

The managed dataset registry is stored in `database/system.db`; analytics data remains separate in `database/superstore.db`. On startup, the app removes legacy user, login-attempt, and activity-log tables and removes uploader identity from the managed dataset registry while preserving dataset records and active-dataset settings.

## Definitions and methods

- **Average order value:** average of each distinct order's summed sales.
- **Profit margin:** total profit divided by total sales (weighted).
- **RFM:** recency is days since the most recent order in the filtered data; frequency is distinct orders; monetary is summed sales. Customers receive 1–5 relative scores and a descriptive segment.
- **Pareto:** products are ranked by sales and displayed with cumulative share of positive sales.
- **Forecast:** additive linear trend plus month-of-year effects fitted with least squares. The most recent months are held out for MAE, RMSE, and sMAPE evaluation. Forecasts are labeled as estimates and require at least 18 months of filtered history; they are not actual results or a guarantee of future performance.
- **Insights:** calculated from the filtered records. Discount patterns are presented as associations, not causal findings.

## Data cleaning

The cleaning pipeline normalizes known column aliases, trims text, parses dates, converts available numeric fields, removes duplicate rows, and drops rows missing essential values. Non-positive quantities and discounts outside 0–1 are excluded when those fields exist. Negative profit and negative sales are preserved. Missing descriptive values are labeled `Unknown`; missing postal codes remain missing. Invalid dates/numeric values and IQR outlier counts are available in Data Explorer. Invalid or missing ship dates do not receive fabricated delivery durations.

## Installation and run

From the project directory in PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

For later runs, activate the environment and run `python -m streamlit run app.py`. The supplied datasets in `data/` are loaded automatically.

## SQL and optional MySQL

SQLite is the default and requires no separate service. The SQL Insights page replaces only the analytics `orders` table with the current filtered data before each query. The read-only authorizer denies write operations, schema access, and unapproved SQL functions.

Optional MySQL setup requires a MySQL 8+ server and a database named `superstore`. Configure `DB_TYPE=mysql`, `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, and `MYSQL_DATABASE` in the environment. Unset `DB_TYPE` or set it to `sqlite` to use the local database.

## Data limitations

The commonly circulated Global Superstore dataset is an educational retail dataset, not audited company financial data. Currency and scope depend on the dataset version. Validate the source and assumptions before using results for business decisions.
=======
# globalsuperstore
>>>>>>> 5183f26d3a6991e168168556277059c8b29c340b
