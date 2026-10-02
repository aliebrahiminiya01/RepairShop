import ttkbootstrap as tb
from ttkbootstrap.constants import *
from tkinter import messagebox

from database.db import get_all_parts, delete_part
from gui.part_form import PartForm


class PartsPanel(tb.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.pack(fill=BOTH, expand=True)
        self._build_ui()
        self.load_parts()

    def _build_ui(self):
        header = tb.Frame(self)
        header.pack(fill=X, pady=5)

        tb.Label(header, text="📦 مدیریت قطعات", font=("Helvetica", 16, "bold")).pack(side=RIGHT)

        tb.Button(header, text="➕ افزودن قطعه", bootstyle=SUCCESS, command=self.add_part).pack(side=LEFT, padx=5)
        tb.Button(header, text="✏ ویرایش", bootstyle=WARNING, command=self.edit_part).pack(side=LEFT, padx=5)
        tb.Button(header, text="🗑 حذف", bootstyle=DANGER, command=self.delete_selected).pack(side=LEFT, padx=5)

        self.tree = tb.Treeview(self, columns=("id", "name", "qty"), show="headings", bootstyle=PRIMARY)
        self.tree.pack(fill=BOTH, expand=True, pady=10)

        self.tree.heading("id", text="ID")
        self.tree.heading("name", text="نام قطعه")
        self.tree.heading("qty", text="موجودی")

        self.tree.column("id", anchor=CENTER, width=70)
        self.tree.column("name", anchor=CENTER, width=320)
        self.tree.column("qty", anchor=CENTER, width=140)

    def load_parts(self):
        self.tree.delete(*self.tree.get_children())
        for part in get_all_parts():
            self.tree.insert("", END, values=part)

    def add_part(self):
        PartForm(self, refresh=self.load_parts)

    def edit_part(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showerror("خطا", "قطعه‌ای انتخاب نشده")
            return

        part = self.tree.item(sel[0])["values"]
        PartForm(self, refresh=self.load_parts, part=part)

    def delete_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showerror("خطا", "قطعه‌ای انتخاب نشده")
            return

        part_id = self.tree.item(sel[0])["values"][0]
        if messagebox.askyesno("حذف", "آیا مطمئن هستید؟"):
            delete_part(part_id)
            self.load_parts()
