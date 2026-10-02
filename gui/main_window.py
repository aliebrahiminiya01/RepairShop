import ttkbootstrap as tb
from ttkbootstrap.constants import *

from gui.devices_list import DevicesList
from gui.device_form import DeviceForm
from gui.alerts_panel import AlertsPanel
from gui.parts_panel import PartsPanel
from gui.reports_page import ReportsPage
from gui.change_password_form import ChangePasswordForm


class MainWindow(tb.Frame):
    def __init__(self, master, username):
        super().__init__(master)
        self.master = master
        self.username = username
        self.pack(fill=BOTH, expand=True)

        self.master.title("سیستم مدیریت تعمیرگاه")
        self.master.geometry("1330x700")

        self._build_layout()

    def _build_layout(self):
        sidebar = tb.Frame(self, width=220)
        sidebar.pack(side=RIGHT, fill=Y)
        sidebar.pack_propagate(False)

        tb.Label(
            sidebar,
            text="منوی اصلی",
            font=("Helvetica", 14, "bold")
        ).pack(pady=15)

        tb.Button(
            sidebar,
            text="📋 لیست دستگاه‌ها",
            bootstyle=PRIMARY,
            command=self.show_devices
        ).pack(fill=X, padx=10, pady=5)

        tb.Button(
            sidebar,
            text="➕ ثبت دستگاه",
            bootstyle=SUCCESS,
            command=self.open_device_form
        ).pack(fill=X, padx=10, pady=5)

        tb.Button(
            sidebar,
            text="🧩 قطعات",
            bootstyle=INFO,
            command=self.show_parts
        ).pack(fill=X, padx=10, pady=5)

        tb.Button(
            sidebar,
            text="🚨 هشدار قطعات",
            bootstyle=WARNING,
            command=self.show_alerts
        ).pack(fill=X, padx=10, pady=5)

        tb.Button(
            sidebar,
            text="📊 گزارش‌ها",
            bootstyle=INFO,
            command=self.show_reports
        ).pack(fill=X, padx=10, pady=5)

        tb.Button(
            sidebar,
            text="🔑 تغییر رمز عبور",
            bootstyle=SECONDARY,
            command=lambda: ChangePasswordForm(self.master, self.username)
        ).pack(side=BOTTOM, fill=X, padx=10, pady=10)

        self.content = tb.Frame(self)
        self.content.pack(side=LEFT, fill=BOTH, expand=True, padx=10, pady=10)

        self.show_welcome()

    def _clear_content(self):
        for widget in self.content.winfo_children():
            widget.destroy()

    def show_welcome(self):
        self._clear_content()
        tb.Label(
            self.content,
            text="به سیستم مدیریت تعمیرگاه خوش آمدید",
            font=("Helvetica", 18)
        ).pack(expand=True)

    def show_devices(self):
        self._clear_content()
        DevicesList(self.content).pack(fill=BOTH, expand=True)

    def open_device_form(self):
        DeviceForm(self.master, refresh_callback=self.show_devices)

    def show_alerts(self):
        self._clear_content()
        AlertsPanel(self.content).pack(fill=BOTH, expand=True)

    def show_parts(self):
        self._clear_content()
        PartsPanel(self.content).pack(fill=BOTH, expand=True)

    def show_reports(self):
        self._clear_content()
        ReportsPage(self.content)
