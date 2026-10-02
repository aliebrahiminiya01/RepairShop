import os
import tempfile
import unittest

from database import db
from gui.utils import (
    jalali_days_in_month,
    jalali_is_leap,
    to_english_digits,
    validate_jalali_date,
)


class JalaliTests(unittest.TestCase):
    def test_leap_years(self):
        for year in (1395, 1399, 1403, 1408, 1412):
            self.assertTrue(jalali_is_leap(year), year)
        for year in (1396, 1400, 1402, 1404, 1405):
            self.assertFalse(jalali_is_leap(year), year)

    def test_esfand_length(self):
        self.assertEqual(jalali_days_in_month(1403, 12), 30)
        self.assertEqual(jalali_days_in_month(1404, 12), 29)

    def test_validate_date(self):
        self.assertTrue(validate_jalali_date(1403, 12, 30)[0])
        self.assertFalse(validate_jalali_date(1404, 12, 30)[0])
        self.assertTrue(validate_jalali_date(1404, 6, 31)[0])
        self.assertFalse(validate_jalali_date(1404, 7, 31)[0])
        self.assertFalse(validate_jalali_date(1404, 13, 1)[0])

    def test_persian_and_arabic_digits(self):
        self.assertEqual(to_english_digits("۱۴۰۴/۰۲/٣١"), "1404/02/31")
        self.assertEqual(to_english_digits(None), "")


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.original_path = db.DB_PATH
        db.DB_PATH = os.path.join(self.tmp.name, "test.db")
        db.create_tables()

    def tearDown(self):
        db.DB_PATH = self.original_path
        self.tmp.cleanup()

    def test_default_login_and_password_change(self):
        self.assertTrue(db.verify_user("admin", "1234"))
        self.assertFalse(db.verify_user("admin", "wrong"))
        self.assertFalse(db.verify_user("nobody", "1234"))

        db.change_password("admin", "new-secret")
        self.assertFalse(db.verify_user("admin", "1234"))
        self.assertTrue(db.verify_user("admin", "new-secret"))

    def test_create_tables_keeps_changed_password(self):
        db.change_password("admin", "new-secret")
        db.create_tables()  # runs on every start
        self.assertTrue(db.verify_user("admin", "new-secret"))

    def test_password_is_not_stored_in_plain_text(self):
        conn = db.connect()
        stored = conn.execute("SELECT password_hash FROM users").fetchone()[0]
        conn.close()
        self.assertNotIn("1234", stored)

    def test_device_filters_and_report(self):
        db.insert_device("Ali", "0912", "تلویزیون", "LG", "S1", "در حال تعمیر", "", 1404, 1, 10, 100, 300)
        db.insert_device("Sara", "0935", "مانیتور", "Samsung", "S2", "آماده تحویل", "", 1404, 2, 5, 50, 80)

        self.assertEqual(len(db.get_devices_for_list({"name": "Ali"})), 1)
        self.assertEqual(len(db.get_devices_for_list({"date_from": (1404, 2, 1)})), 1)

        parts, received, profit = db.get_report_by_date(1404, 1, 1, 1404, 12, 29)
        self.assertEqual((parts, received, profit), (150, 380, 230))

    def test_deleting_part_removes_its_alerts(self):
        db.insert_part("Capacitor", 3)
        part_id = db.get_all_parts()[0][0]
        db.insert_alert(part_id, 5)
        self.assertEqual(len(db.get_all_alerts()), 1)

        db.delete_part(part_id)
        self.assertEqual(db.get_alerted_part_ids(), set())


if __name__ == "__main__":
    unittest.main()
