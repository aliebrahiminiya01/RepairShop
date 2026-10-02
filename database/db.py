# database/db.py
import hashlib
import hmac
import os
import secrets
import shutil
import sqlite3
import sys


def resource_path(relative_path: str) -> str:
    base = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base, relative_path)


def app_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


DB_NAME = "repair_shop.db"
DB_PATH = os.path.join(app_dir(), DB_NAME)

BUNDLED_DB_PATH = resource_path(os.path.join("database", "repair_shop.db"))

DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "1234"


def create_tables():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS devices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_name TEXT NOT NULL,
        phone TEXT NOT NULL,
        device_type TEXT NOT NULL,
        model TEXT,
        serial TEXT,
        status TEXT,
        note TEXT,
        year INTEGER,
        month INTEGER,
        day INTEGER,
        parts_cost INTEGER DEFAULT 0,
        received_cost INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS parts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        quantity INTEGER DEFAULT 0
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password_hash TEXT NOT NULL,
        salt TEXT NOT NULL
    )
    """)

    # first run: create the default account (the password should be changed after the first login)
    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        salt = secrets.token_hex(16)
        cur.execute(
            "INSERT INTO users (username, password_hash, salt) VALUES (?, ?, ?)",
            (DEFAULT_USERNAME, _hash_password(DEFAULT_PASSWORD, salt), salt)
        )

    cur.execute("""
    CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        part_id INTEGER NOT NULL,
        min_qty INTEGER NOT NULL,
        FOREIGN KEY(part_id) REFERENCES parts(id)
    )
    """)

    conn.commit()
    conn.close()


def ensure_database():
    if os.path.exists(DB_PATH):
        return

    if os.path.exists(BUNDLED_DB_PATH):
        try:
            shutil.copy2(BUNDLED_DB_PATH, DB_PATH)
            return
        except OSError:
            pass

    create_tables()


def connect():
    ensure_database()
    return sqlite3.connect(DB_PATH)


# USERS

def _hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), 200_000).hex()


def verify_user(username: str, password: str) -> bool:
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT password_hash, salt FROM users WHERE username=?", (username,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return False
    return hmac.compare_digest(row[0], _hash_password(password, row[1]))


def change_password(username: str, new_password: str):
    salt = secrets.token_hex(16)
    conn = connect()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET password_hash=?, salt=? WHERE username=?",
        (_hash_password(new_password, salt), salt, username)
    )
    conn.commit()
    conn.close()


# DEVICES

def insert_device(name, phone, device_type, model, serial,
                  status, note, year, month, day, parts_cost, received_cost):
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO devices (
            customer_name, phone, device_type, model, serial,
            status, note, year, month, day, parts_cost, received_cost
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (name, phone, device_type, model, serial, status, note,
          year, month, day, parts_cost, received_cost))
    conn.commit()
    conn.close()


def delete_device(device_id):
    conn = connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM devices WHERE id=?", (device_id,))
    conn.commit()
    conn.close()


def update_device_status(device_id, new_status):
    conn = connect()
    cur = conn.cursor()
    cur.execute("UPDATE devices SET status=? WHERE id=?", (new_status, device_id))
    conn.commit()
    conn.close()


def get_device_by_id(device_id):
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM devices WHERE id=?", (device_id,))
    row = cur.fetchone()
    conn.close()
    return row


def update_device(device_id, name, phone, device_type, model, serial,
                  status, note, year, month, day, parts_cost, received_cost):
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        UPDATE devices SET
            customer_name=?,
            phone=?,
            device_type=?,
            model=?,
            serial=?,
            status=?,
            note=?,
            year=?,
            month=?,
            day=?,
            parts_cost=?,
            received_cost=?
        WHERE id=?
    """, (name, phone, device_type, model, serial, status, note,
          year, month, day, parts_cost, received_cost, device_id))
    conn.commit()
    conn.close()


def get_devices_for_list(filters=None):
    conn = connect()
    cur = conn.cursor()

    query = """
        SELECT
            id,
            serial,
            printf('%04d/%02d/%02d', year, month, day) AS date,
            customer_name,
            phone,
            status,
            device_type,
            model
        FROM devices
        WHERE 1=1
    """
    params = []

    if filters:
        if filters.get("name"):
            query += " AND customer_name LIKE ?"
            params.append(f"%{filters['name']}%")
        if filters.get("device_type"):
            query += " AND device_type = ?"
            params.append(filters["device_type"])
        if filters.get("model"):
            query += " AND model LIKE ?"
            params.append(f"%{filters['model']}%")
        if filters.get("status"):
            query += " AND status = ?"
            params.append(filters["status"])

        if filters.get("date_from"):
            y, m, d = filters["date_from"]
            query += " AND (year*10000 + month*100 + day) >= ?"
            params.append(y * 10000 + m * 100 + d)
        if filters.get("date_to"):
            y, m, d = filters["date_to"]
            query += " AND (year*10000 + month*100 + day) <= ?"
            params.append(y * 10000 + m * 100 + d)

    query += " ORDER BY created_at DESC"
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    return rows


# PARTS

def get_all_parts():
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT id, name, quantity FROM parts")
    rows = cur.fetchall()
    conn.close()
    return rows


def insert_part(name, quantity):
    conn = connect()
    cur = conn.cursor()
    cur.execute("INSERT INTO parts (name, quantity) VALUES (?, ?)", (name, quantity))
    conn.commit()
    conn.close()


def update_part(part_id, name, quantity):
    conn = connect()
    cur = conn.cursor()
    cur.execute("UPDATE parts SET name=?, quantity=? WHERE id=?", (name, quantity, part_id))
    conn.commit()
    conn.close()


def delete_part(part_id):
    conn = connect()
    cur = conn.cursor()
    # remove the part's low-stock alerts too, otherwise they stay orphaned
    cur.execute("DELETE FROM alerts WHERE part_id=?", (part_id,))
    cur.execute("DELETE FROM parts WHERE id=?", (part_id,))
    conn.commit()
    conn.close()


# ALERTS

def get_all_alerts():
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT alerts.id, parts.name, alerts.min_qty, parts.quantity
        FROM alerts
        JOIN parts ON alerts.part_id = parts.id
    """)
    rows = cur.fetchall()
    conn.close()
    return rows


def insert_alert(part_id, min_qty):
    conn = connect()
    cur = conn.cursor()
    cur.execute("INSERT INTO alerts (part_id, min_qty) VALUES (?, ?)", (part_id, min_qty))
    conn.commit()
    conn.close()


def update_alert(alert_id, part_id, min_qty):
    conn = connect()
    cur = conn.cursor()
    cur.execute("UPDATE alerts SET part_id=?, min_qty=? WHERE id=?", (part_id, min_qty, alert_id))
    conn.commit()
    conn.close()


def delete_alert(alert_id):
    conn = connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM alerts WHERE id=?", (alert_id,))
    conn.commit()
    conn.close()


# REPORTS

def get_report_by_date(sy, sm, sd, ey, em, ed):
    conn = connect()
    cur = conn.cursor()
    start_value = sy * 10000 + sm * 100 + sd
    end_value = ey * 10000 + em * 100 + ed

    cur.execute("""
        SELECT SUM(parts_cost), SUM(received_cost)
        FROM devices
        WHERE (year*10000 + month*100 + day) BETWEEN ? AND ?
    """, (start_value, end_value))

    row = cur.fetchone()
    conn.close()

    parts = row[0] or 0
    received = row[1] or 0
    return parts, received, received - parts


# REPORTS

def _range_to_int(y, m, d):
    return int(y) * 10000 + int(m) * 100 + int(d)


def get_status_counts_by_range(sy, sm, sd, ey, em, ed):
    """
     (status, count)
    """
    conn = connect()
    cur = conn.cursor()

    start_value = _range_to_int(sy, sm, sd)
    end_value = _range_to_int(ey, em, ed)

    cur.execute("""
        SELECT status, COUNT(*)
        FROM devices
        WHERE (year*10000 + month*100 + day) BETWEEN ? AND ?
        GROUP BY status
        ORDER BY COUNT(*) DESC
    """, (start_value, end_value))

    rows = cur.fetchall()
    conn.close()
    return rows


def get_top_device_types_by_range(sy, sm, sd, ey, em, ed, limit=10):
    """
     (device_type, count)
    """
    conn = connect()
    cur = conn.cursor()

    start_value = _range_to_int(sy, sm, sd)
    end_value = _range_to_int(ey, em, ed)

    cur.execute("""
        SELECT device_type, COUNT(*)
        FROM devices
        WHERE (year*10000 + month*100 + day) BETWEEN ? AND ?
        GROUP BY device_type
        ORDER BY COUNT(*) DESC
        LIMIT ?
    """, (start_value, end_value, int(limit)))

    rows = cur.fetchall()
    conn.close()
    return rows


def get_monthly_series_by_range(sy, sm, sd, ey, em, ed):
    """
     (year, month, received_sum, parts_sum)
    """
    conn = connect()
    cur = conn.cursor()

    start_value = _range_to_int(sy, sm, sd)
    end_value = _range_to_int(ey, em, ed)

    cur.execute("""
        SELECT
            year,
            month,
            SUM(received_cost) AS received_sum,
            SUM(parts_cost) AS parts_sum
        FROM devices
        WHERE (year*10000 + month*100 + day) BETWEEN ? AND ?
        GROUP BY year, month
        ORDER BY year, month
    """, (start_value, end_value))

    rows = cur.fetchall()
    conn.close()
    return rows


def get_yearly_series_by_range(sy, sm, sd, ey, em, ed):
    """
     (year, received_sum, parts_sum)
    """
    conn = connect()
    cur = conn.cursor()

    start_value = _range_to_int(sy, sm, sd)
    end_value = _range_to_int(ey, em, ed)

    cur.execute("""
        SELECT
            year,
            SUM(received_cost) AS received_sum,
            SUM(parts_cost) AS parts_sum
        FROM devices
        WHERE (year*10000 + month*100 + day) BETWEEN ? AND ?
        GROUP BY year
        ORDER BY year
    """, (start_value, end_value))

    rows = cur.fetchall()
    conn.close()
    return rows


def get_alerted_part_ids():
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT part_id FROM alerts")
    rows = cur.fetchall()
    conn.close()
    return {r[0] for r in rows}  # set of ids
