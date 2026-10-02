import ttkbootstrap as tb
from ttkbootstrap.constants import *
from tkinter import messagebox
from database.db import insert_part, update_part
from gui.utils import to_english_digits


class PartForm(tb.Toplevel):
    def __init__(self, master, refresh, part=None):
        super().__init__(master)
        self.title("قطعه")
        self.geometry("350x200")
        self.refresh = refresh
        self.part = part

        tb.Label(self, text="نام قطعه").pack(anchor=E, padx=10, pady=5)
        self.name_var = tb.StringVar(value=part[1] if part else "")
        tb.Entry(self, textvariable=self.name_var, justify="right").pack(fill=X, padx=10)

        tb.Label(self, text="موجودی").pack(anchor=E, padx=10, pady=5)

        default_qty = str(part[2]) if part else "0"
        self.qty_var = tb.StringVar(value=default_qty)
        tb.Entry(self, textvariable=self.qty_var, justify="right").pack(fill=X, padx=10)

        tb.Button(
            self,
            text="ذخیره",
            bootstyle=SUCCESS,
            command=self.save
        ).pack(pady=15)

    def save(self):
        name = self.name_var.get().strip()
        qty_txt = to_english_digits(self.qty_var.get().strip())

        if not name:
            messagebox.showerror("خطا", "نام قطعه وارد نشده")
            return

        if qty_txt == "":
            qty_txt = "0"

        if not qty_txt.isdigit():
            messagebox.showerror("خطا", "موجودی باید عدد باشد")
            return

        qty = int(qty_txt)

        self.qty_var.set(str(qty))

        if self.part:
            update_part(self.part[0], name, qty)
        else:
            insert_part(name, qty)

        self.refresh()
        self.destroy()
