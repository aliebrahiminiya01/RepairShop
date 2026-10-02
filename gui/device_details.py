import ttkbootstrap as tb
from ttkbootstrap.constants import *
from database.db import get_device_by_id


def _lbl(text: str) -> str:
    # fix RTL colon on Windows
    return f"{text}\u200e:"


class DeviceDetailsWindow(tb.Toplevel):
    def __init__(self, master, device_id: int):
        super().__init__(master)
        self.device_id = device_id

        self.title("جزئیات دستگاه")
        self.geometry("520x640")
        self.minsize(520, 640)

        self._build()

    def _build(self):
        device = get_device_by_id(self.device_id)
        if not device:
            tb.Label(self, text="رکورد پیدا نشد").pack(padx=20, pady=20)
            return

        (
            _id,
            customer_name,
            phone,
            device_type,
            model,
            serial,
            status,
            note,
            year,
            month,
            day,
            parts_cost,
            received_cost,
            created_at
        ) = device

        wrapper = tb.Frame(self)
        wrapper.pack(fill=BOTH, expand=True, padx=14, pady=14)

        tb.Label(wrapper, text="مشخصات کامل دستگاه", font=("Helvetica", 14, "bold")).pack(anchor=E, pady=(0, 10))
        tb.Separator(wrapper).pack(fill=X, pady=6)

        rows = [
            ("نام مشتری", customer_name),
            ("شماره تماس", phone),
            ("نوع دستگاه", device_type),
            ("مدل", model or ""),
            ("سریال", serial or ""),
            ("وضعیت", status or ""),
            ("تاریخ", f"{year:04d}/{month:02d}/{day:02d}" if year and month and day else ""),
            ("هزینه قطعات", f"{parts_cost:,}" if parts_cost is not None else "0"),
            ("هزینه دریافتی", f"{received_cost:,}" if received_cost is not None else "0"),
            ("تاریخ ثبت", created_at or ""),
        ]

        for title, val in rows:
            r = tb.Frame(wrapper)
            r.pack(fill=X, pady=4)
            tb.Label(r, text=_lbl(title), width=16, anchor=E).pack(side=RIGHT)
            tb.Label(r, text=str(val), anchor=E).pack(side=RIGHT, padx=8)

        tb.Separator(wrapper).pack(fill=X, pady=10)
        tb.Label(wrapper, text=_lbl("یادداشت تعمیر"), anchor=E).pack(fill=X)

        note_box = tb.Text(wrapper, height=10, wrap="word")
        note_box.pack(fill=BOTH, expand=True, pady=6)
        note_box.insert("1.0", note or "")
        note_box.config(state="disabled")

        tb.Button(wrapper, text="بستن", command=self.destroy).pack(pady=10)
