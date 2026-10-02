# Repair Shop Management System

A desktop application for managing an electronics repair shop (TVs, monitors, receivers, audio systems),
built with Python, Tkinter/[ttkbootstrap](https://ttkbootstrap.readthedocs.io/) and SQLite.
The user interface is in **Persian (right-to-left)** and uses the **Jalali (Solar Hijri) calendar**.

## Features

- **Login** with a hashed password (PBKDF2-SHA256) and a *change password* dialog
- **Devices** – register customer devices, edit them, mark them as delivered, delete them,
  and view full details; colour-coded repair status
- **Search & filters** – by customer name, device type, model, status and Jalali date range
- **Invoices** – generate a PDF invoice with correct Persian text shaping (Vazir font),
  preview it, save it, or send it to the printer
- **Parts inventory** – add, edit and delete spare parts and their stock
- **Low-stock alerts** – set a minimum quantity per part; parts at or below the minimum are highlighted
- **Reports** – income, parts cost and profit for any date range, plus monthly/yearly charts,
  status breakdown and most common device types
- Persian and Arabic digits are accepted in every number field

## Requirements

- Python 3.10 or newer (with Tkinter)
- The packages in `requirements.txt`

## Run the app

```bash
python3 -m pip install -r requirements.txt
python3 main.py
```

On the first run the app creates its database (`repair_shop.db`) next to `main.py` and a default account:

| Username | Password |
|----------|----------|
| `admin`  | `1234`   |

> **Change the default password** after the first login using the *🔑 تغییر رمز عبور* button in the sidebar.

## Run the tests

```bash
python3 -m unittest discover -s tests -v
```

## Build a standalone app

```bash
python3 -m pip install -r requirements-dev.txt
pyinstaller main.spec
```

The application is created in the `dist/` folder (`RepairShop.app` on macOS).
When the built app runs, the database is created next to the executable.

## Project structure

```text
main.py                     entry point
auth/login.py               login screen
database/db.py              SQLite schema and all database queries
gui/main_window.py          main window and sidebar navigation
gui/devices_list.py         device list, search and actions
gui/device_form.py          add / edit device form
gui/device_details.py       device details window
gui/invoice_window.py       invoice editor, PDF export, preview and printing
gui/parts_panel.py          parts inventory
gui/alerts_panel.py         low-stock alerts
gui/reports_page.py         financial reports and charts
gui/change_password_form.py change password dialog
gui/utils.py                Jalali calendar, digit conversion and resource helpers
tests/                      unit tests
Vazir.ttf                   Persian font used in PDF invoices
```

## Data and privacy

All data (customers, phone numbers, devices, invoices) is stored locally in `repair_shop.db`.
The database file is excluded from git so that customer data is never committed.

## Credits

- [Vazir font](https://github.com/rastikerdar/vazir-font) by Saber Rastikerdar (SIL Open Font License)
