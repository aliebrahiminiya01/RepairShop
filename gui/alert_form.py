import ttkbootstrap as tb
from ttkbootstrap.constants import *
from tkinter import messagebox

from database.db import (
    get_all_parts,
    insert_alert,
    update_alert,
    get_alerted_part_ids
)
from gui.utils import to_english_digits


class AlertForm(tb.Toplevel):
    def __init__(self, master, refresh, alert=None):
        super().__init__(master)
        self.title("هشدار قطعه")
        self.geometry("350x220")
        self.refresh = refresh
        self.alert = alert

        tb.Label(self, text="انتخاب قطعه").pack(anchor=E, padx=10, pady=5)

        parts = get_all_parts()  # (id, name, qty)
        alerted_ids = get_alerted_part_ids()

        current_part_id = None
        all_map = {p[1]: p[0] for p in parts}  # name -> id

        if alert:
            current_part_id = all_map.get(alert[1])

        filtered_parts = []
        for p in parts:
            pid, pname, _qty = p
            if pid in alerted_ids and pid != current_part_id:
                continue
            filtered_parts.append(p)

        self.part_map = {p[1]: p[0] for p in filtered_parts}

        self.part_var = tb.StringVar()
        combo = tb.Combobox(
            self,
            values=list(self.part_map.keys()),
            textvariable=self.part_var,
            justify="right",
            state="readonly"
        )
        combo.pack(fill=X, padx=10)

        if alert and alert[1] in self.part_map:
            self.part_var.set(alert[1])

        tb.Label(self, text="حداقل موجودی").pack(anchor=E, padx=10, pady=5)

        # ✅ StringVar تا با رقم فارسی کرش نکنه
        default_min = str(alert[2]) if alert else "0"
        self.min_var = tb.StringVar(value=default_min)
        tb.Entry(self, textvariable=self.min_var, justify="right").pack(fill=X, padx=10)

        tb.Button(self, text="ذخیره", bootstyle=SUCCESS, command=self.save).pack(pady=15)

    def save(self):
        part_name = self.part_var.get().strip()
        min_txt = to_english_digits(self.min_var.get().strip())

        if part_name not in self.part_map:
            messagebox.showerror("خطا", "قطعه انتخاب نشده")
            return

        if not min_txt.isdigit():
            messagebox.showerror("خطا", "حداقل موجودی باید عدد باشد")
            return

        min_qty = int(min_txt)
        part_id = self.part_map[part_name]

        if self.alert:
            update_alert(self.alert[0], part_id, min_qty)
        else:
            insert_alert(part_id, min_qty)

        self.refresh()
        self.destroy()
