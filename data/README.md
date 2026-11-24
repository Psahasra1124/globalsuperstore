# Dataset setup

The dashboard uses `Global_Superstore2.xlsx` as its primary dataset and falls back to `Global_Superstore2.csv` if the Excel file cannot be loaded. Both files should remain in this folder. You can also upload a compatible CSV through the Streamlit sidebar.

The supplied files contain 51,290 rows and the same 24 columns. The essential fields are `Order ID`, `Order Date`, `Sales` and `Profit`. Other fields enable optional filters and dashboard analyses; those analyses are skipped with a helpful message when a field is unavailable. The loader accepts UTF-8 and Windows-1252 CSV files, and normalizes common column-name variations.
