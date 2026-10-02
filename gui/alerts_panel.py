import ttkbootstrap as tb
from ttkbootstrap.constants import *
from tkinter import messagebox

from database.db import get_all_alerts, delete_alert
from gui.alert_form import AlertForm


class AlertsPanel(tb.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.pack(fill=BOTH, expand=True)
        self._build_ui()
        self.load_alerts()

    def _build_ui(self):
        header = tb.Frame(self)
        header.pack(fill=X, pady=5)

        tb.Label(header, text="🚨 هشدار کمبود قطعه", font=("Helvetica", 16, "bold")).pack(side=RIGHT)

        tb.Button(header, text="➕ افزودن هشدار", bootstyle=WARNING, command=self.add_alert).pack(side=LEFT, padx=5)
        tb.Button(header, text="✏ ویرایش", bootstyle=INFO, command=self.edit_alert).pack(side=LEFT, padx=5)
        tb.Button(header, text="🗑 حذف", bootstyle=DANGER, command=self.delete_selected).pack(side=LEFT, padx=5)

        self.tree = tb.Treeview(self, columns=("id", "part", "min", "current"), show="headings", bootstyle=PRIMARY)
        self.tree.pack(fill=BOTH, expand=True, pady=10)

        self.tree.heading("id", text="ID")
        self.tree.heading("part", text="نام قطعه")
        self.tree.heading("min", text="حداقل")
        self.tree.heading("current", text="موجودی فعلی")

        self.tree.column("id", anchor=CENTER, width=70)
        self.tree.column("part", anchor=CENTER, width=240)
        self.tree.column("min", anchor=CENTER, width=120)
        self.tree.column("current", anchor=CENTER, width=140)

        self.tree.tag_configure("equal", background="#0f2d46", foreground="#ffffff")  # آبی
        self.tree.tag_configure("low", background="#4a1616", foreground="#ffffff")  # قرمز

    def load_alerts(self):
        self.tree.delete(*self.tree.get_children())

        for alert in get_all_alerts():
            # (id, part_name, min_qty, current_qty)
            tag = ""
            if alert[3] == alert[2]:
                tag = "equal"
            elif alert[3] < alert[2]:
                tag = "low"

            self.tree.insert("", END, values=alert, tags=(tag,))

    def add_alert(self):
        AlertForm(self, refresh=self.load_alerts)

    def edit_alert(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showerror("خطا", "هشداری انتخاب نشده")
            return
        alert = self.tree.item(sel[0])["values"]
        AlertForm(self, refresh=self.load_alerts, alert=alert)

    def delete_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showerror("خطا", "هشداری انتخاب نشده")
            return

        alert_id = self.tree.item(sel[0])["values"][0]
        delete_alert(alert_id)
        self.load_alerts()
