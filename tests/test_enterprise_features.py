import hashlib
import sqlite3
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from database import database as analytics_database
from database import datasets
from database.database import load_to_readonly_sqlite, query_df
from database.query_catalog import get_queries
from utils.assistant import answer_question
from utils.exports import pdf_report_bytes
from utils.metrics import filter_data
from utils.visualizations import _format_currency


class EnterpriseFeatureTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.temporary_path = Path(self.temporary_directory.name)
        self.root_patch = patch.object(datasets, "ROOT", self.temporary_path)
        self.database_patch = patch.object(
            datasets, "DATASETS_DATABASE", self.temporary_path / "system.db"
        )
        self.uploads_patch = patch.object(
            datasets, "UPLOAD_DIRECTORY", self.temporary_path / "data" / "uploads"
        )
        self.root_patch.start()
        self.database_patch.start()
        self.uploads_patch.start()

    def tearDown(self):
        self.uploads_patch.stop()
        self.database_patch.stop()
        self.root_patch.stop()
        self.temporary_directory.cleanup()

    def _orders(self):
        return pd.DataFrame(
            [
                {
                    "Order ID": "O1",
                    "Order Date": "2024-01-01",
                    "Order Month": "2024-01",
                    "Ship Mode": "Standard",
                    "Customer ID": "C1",
                    "Customer Name": "Customer One",
                    "Segment": "Consumer",
                    "Country": "USA",
                    "State": "CA",
                    "Region": "West",
                    "Market": "US",
                    "Product ID": "P1",
                    "Product Name": "Product One",
                    "Category": "Office Supplies",
                    "Sub-Category": "Paper",
                    "Sales": 100.0,
                    "Quantity": 2,
                    "Discount": 0.1,
                    "Profit": 20.0,
                    "Shipping Duration": 2,
                    "Order Priority": "High",
                    "Year": 2024,
                    "Quarter": "Q1",
                },
                {
                    "Order ID": "O2",
                    "Order Date": "2024-02-01",
                    "Order Month": "2024-02",
                    "Ship Mode": "Second",
                    "Customer ID": "C2",
                    "Customer Name": "Customer Two",
                    "Segment": "Corporate",
                    "Country": "USA",
                    "State": "NY",
                    "Region": "East",
                    "Market": "US",
                    "Product ID": "P2",
                    "Product Name": "Product Two",
                    "Category": "Technology",
                    "Sub-Category": "Phones",
                    "Sales": 50.0,
                    "Quantity": 1,
                    "Discount": 0.2,
                    "Profit": -5.0,
                    "Shipping Duration": 4,
                    "Order Priority": "Low",
                    "Year": 2024,
                    "Quarter": "Q1",
                },
            ]
        )

    def test_managed_dataset_upload_and_activation_are_persisted(self):
        content = b"validated dataset bytes"
        dataset_id = datasets.save_uploaded_dataset(
            "report.csv", content, 3, ["Order ID", "Sales", "Profit"]
        )
        path = datasets.activate_dataset(dataset_id)
        self.assertEqual(path.read_bytes(), content)
        self.assertEqual(datasets.get_active_dataset_path(), path)
        item = datasets.list_datasets()[0]
        self.assertTrue(item["is_active"])
        self.assertNotIn("uploaded_by", item)

    def test_database_migration_removes_auth_tables_and_preserves_dataset_registry(self):
        content = b"preserved managed dataset"
        digest = hashlib.sha256(content).hexdigest()
        stored_path = "data/uploads/managed.csv"
        upload_path = self.temporary_path / stored_path
        upload_path.parent.mkdir(parents=True)
        upload_path.write_bytes(content)

        connection = sqlite3.connect(datasets.DATASETS_DATABASE)
        try:
            connection.executescript(
                """
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY,
                    username TEXT NOT NULL,
                    password_hash TEXT NOT NULL
                );
                CREATE TABLE login_attempts (id INTEGER PRIMARY KEY);
                CREATE TABLE activity_log (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id)
                );
                CREATE TABLE datasets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    original_name TEXT NOT NULL,
                    stored_path TEXT NOT NULL,
                    sha256 TEXT NOT NULL,
                    uploaded_by TEXT NOT NULL,
                    uploaded_at TEXT NOT NULL,
                    row_count INTEGER NOT NULL,
                    columns_json TEXT NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                INSERT INTO users VALUES (1, 'former-user', 'old-password-hash');
                INSERT INTO login_attempts VALUES (1);
                INSERT INTO activity_log VALUES (1, 1);
                """
            )
            connection.execute(
                """
                INSERT INTO datasets
                    (id, original_name, stored_path, sha256, uploaded_by, uploaded_at,
                     row_count, columns_json, is_active)
                VALUES (1, 'managed.csv', ?, ?, 'former-user', '2024-01-01', 2, '[]', 1)
                """,
                (stored_path, digest),
            )
            connection.execute(
                "INSERT INTO settings (key, value) VALUES ('active_dataset', ?)",
                (stored_path,),
            )
            connection.commit()
        finally:
            connection.close()

        datasets.initialize_dataset_db()

        connection = sqlite3.connect(datasets.DATASETS_DATABASE)
        try:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            self.assertTrue({"users", "login_attempts", "activity_log"}.isdisjoint(tables))
            columns = {
                row[1] for row in connection.execute("PRAGMA table_info(datasets)")
            }
            self.assertNotIn("uploaded_by", columns)
            row = connection.execute(
                "SELECT id, original_name, stored_path, sha256, row_count, is_active "
                "FROM datasets"
            ).fetchone()
            active_setting = connection.execute(
                "SELECT value FROM settings WHERE key = 'active_dataset'"
            ).fetchone()[0]
        finally:
            connection.close()
        self.assertEqual(
            row, (1, "managed.csv", stored_path, digest, 2, 1)
        )
        self.assertEqual(active_setting, stored_path)
        self.assertEqual(datasets.get_active_dataset_path(), upload_path)

    def test_sql_catalog_queries_run_read_only_and_reject_writes(self):
        orders = self._orders()
        connection = sqlite3.connect(":memory:")
        orders.to_sql("orders", connection, index=False)
        queries = get_queries(orders.columns)
        self.assertGreaterEqual(len(queries), 30)
        for label, sql in queries:
            with self.subTest(query=label):
                result = query_df(connection, sql)
                self.assertIsInstance(result, pd.DataFrame)
        with self.assertRaises(ValueError):
            query_df(connection, "DELETE FROM orders")
        with self.assertRaises(sqlite3.DatabaseError):
            query_df(connection, "SELECT name FROM sqlite_master")
        with self.assertRaises(sqlite3.DatabaseError):
            query_df(connection, "SELECT randomblob(1000000000)")
        commented = query_df(connection, "-- report query\nSELECT COUNT(*) AS rows FROM orders")
        self.assertEqual(commented.iloc[0]["rows"], 2)
        connection.close()

        project_with_spaces = self.temporary_path / "workspace with spaces"
        with patch.object(analytics_database, "ROOT", project_with_spaces):
            readonly = load_to_readonly_sqlite(orders)
            with self.assertRaises(sqlite3.OperationalError):
                readonly.execute("DELETE FROM orders")
            readonly.close()

    def test_assistant_and_pdf_use_filtered_data(self):
        orders = self._orders()
        answer, result = answer_question(orders, "Which region has the highest sales?")
        self.assertIn("West", answer)
        self.assertEqual(result.iloc[0]["Sales"], 100.0)
        customer_answer, _ = answer_question(orders, "How many unique customers?")
        self.assertIn("2", customer_answer)
        missing_dimension, missing_result = answer_question(
            orders.drop(columns=["Market"]), "Sales by market"
        )
        self.assertIn("Market is not available", missing_dimension)
        self.assertIsNone(missing_result)
        pdf = pdf_report_bytes(orders, (date(2024, 1, 1), date(2024, 2, 1)))
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertGreater(len(pdf), 500)

    def test_empty_global_filter_means_all_values(self):
        orders = self._orders()
        orders["Order Date"] = pd.to_datetime(orders["Order Date"])
        start, end = date(2024, 1, 1), date(2024, 2, 1)

        unfiltered = filter_data(orders, start, end, {"Region": []})
        selected = filter_data(orders, start, end, {"Region": ["West"]})

        self.assertEqual(len(unfiltered), 2)
        self.assertEqual(selected["Region"].unique().tolist(), ["West"])

    def test_metric_currency_format_is_compact_but_exact_on_hover(self):
        self.assertEqual(_format_currency(12_642_501.91), "$12.64M")
        self.assertEqual(_format_currency(15_400), "$15.4K")
        self.assertEqual(_format_currency(504.99), "$504.99")


if __name__ == "__main__":
    unittest.main()
