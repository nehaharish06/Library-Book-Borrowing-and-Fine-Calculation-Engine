# =============================
# test_app.py (Updated Unit Tests)
# =============================

import unittest
import pandas as pd
import os
from app import process_data, ALLOWED_DAYS

class TestLibrary(unittest.TestCase):

    def setUp(self):
        """Create sample CSV files for testing"""

        # Books CSV
        self.books_file = "test_books.csv"
        books_df = pd.DataFrame({
            'book_id': [1, 2, 3]
        })
        books_df.to_csv(self.books_file, index=False)

        # Records CSV
        self.records_file = "test_records.csv"
        records_df = pd.DataFrame({
            'user_id': ['U1', 'U2', 'U3'],
            'book_id': [1, 2, 99],   # 99 is invalid
            'borrow_date': ['2023-01-01', '2023-01-01', 'invalid-date'],
            'return_date': ['2023-01-05', '2023-01-15', '2023-01-10'],
            'email': ['a@test.com', 'b@test.com', 'c@test.com']
        })
        records_df.to_csv(self.records_file, index=False)

    def tearDown(self):
        """Delete test files"""
        os.remove(self.books_file)
        os.remove(self.records_file)

    # ✅ 1. INVALID BOOK
    def test_invalid_book_rejected(self):
        df, _ = process_data(self.books_file, self.records_file)
        # book_id 99 should not be present
        self.assertNotIn(99, df['book_id'].values)

    # ✅ 2. INVALID DATE
    def test_invalid_date_ignored(self):
        df, _ = process_data(self.books_file, self.records_file)
        # Only 2 valid rows should remain
        self.assertEqual(len(df), 2)

    # ✅ 3. NO FINE WITHIN DUE DATE
    def test_no_fine_within_due_date(self):
        df, _ = process_data(self.books_file, self.records_file)
        row = df[df['user_id'] == 'U1'].iloc[0]
        self.assertEqual(row['fine'], 0)

    # ✅ 4. FINE CALCULATION
    def test_fine_calculation(self):
        df, _ = process_data(self.books_file, self.records_file)
        row = df[df['user_id'] == 'U2'].iloc[0]

        days = row['days']
        expected_fine = (days - ALLOWED_DAYS) * 20
        self.assertEqual(row['fine'], expected_fine)

    # ✅ 5. LATE RETURN FLAG
    def test_late_return_flag(self):
        df, _ = process_data(self.books_file, self.records_file)
        row = df[df['user_id'] == 'U2'].iloc[0]

        self.assertTrue(row['late'])


if __name__ == '__main__':
    unittest.main()