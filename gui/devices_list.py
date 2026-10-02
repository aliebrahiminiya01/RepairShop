import ttkbootstrap as tb
from ttkbootstrap.constants import *
from tkinter import messagebox

from database.db import (
    get_devices_for_list,
    update_device_status,
    delete_device
)

from gui.device_form import DeviceForm
from gui.device_details import DeviceDetailsWindow
from gui.invoice_window import InvoiceWindow


def _lbl(text: str) -> str:
    return f"{text}\u200e:"


class DevicesList(tb.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.pack(fill=BOTH, expand=True)
        self.filters = {}

        self._build_search_panel()
        self._build_table()
        self._build_buttons()

        self.load_devices()

        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.bind("<Double-1>", lambda e: self.open_details())  # ✅ double click => details

    # ─────────────────────────────
    def _build_search_panel(self):
        box = tb.Labelframe(self, text="جستجو", bootstyle=SECONDARY, labelanchor="ne")
        box.pack(fill=X, padx=12, pady=10)

        self.name_var = tb.StringVar()
        self.type_var = tb.StringVar()
        self.model_var = tb.StringVar()
        self.status_var = tb.StringVar()
        self.date_from_var = tb.StringVar()
        self.date_to_var = tb.StringVar()

        row0 = tb.Frame(box)
        row0.pack(fill=X, padx=10, pady=(8, 4))

        row1 = tb.Frame(box)
        row1.pack(fill=X, padx=10, pady=(0, 8))

        def field(parent, label_text, widget_maker, width=18):
            f = tb.Frame(parent)
            f.pack(side=RIGHT, padx=10)

            tb.Label(f, text=_lbl(label_text), anchor=E, justify=RIGHT).pack(side=RIGHT, padx=(0, 6))
            w = widget_maker(f)
            # ورودی دقیقاً کنار لیبل خودش
            w.pack(side=RIGHT)
            return w

        field(
            row0, "وضعیت",
            lambda p: tb.Combobox(
                p,
                textvariable=self.status_var,
                values=["", "در انتظار بررسی", "در حال تعمیر", "آماده تحویل", "تحویل داده شد", "تحویل داده شده"],
                state="readonly",
                justify=RIGHT,
                width=18
            )
        )

        field(
            row0, "مدل",
            lambda p: tb.Entry(p, textvariable=self.model_var, justify=RIGHT, width=18)
        )

        field(
            row0, "نوع دستگاه",
            lambda p: tb.Combobox(
                p,
                textvariable=self.type_var,
                values=["", "تلویزیون", "مانیتور", "گیرنده دیجیتال", "ماهواره", "سیستم صوتی", "سایر"],
                state="readonly",
                justify=RIGHT,
                width=18
            )
        )

        field(
            row0, "نام مشتری",
            lambda p: tb.Entry(p, textvariable=self.name_var, justify=RIGHT, width=18)
        )

        field(
            row1, "از تاریخ",
            lambda p: tb.Entry(p, textvariable=self.date_from_var, justify=RIGHT, width=18)
        )

        field(
            row1, "تا تاریخ",
            lambda p: tb.Entry(p, textvariable=self.date_to_var, justify=RIGHT, width=18)
        )

        btns = tb.Frame(row1)
        btns.pack(side=LEFT, padx=10)

        tb.Button(btns, text="اعمال 🔍", bootstyle=PRIMARY, command=self.apply_filters, width=14) \
            .pack(side=LEFT, padx=6)

        tb.Button(btns, text="پاک کردن ♻️", bootstyle=SECONDARY, command=self.clear_filters, width=14) \
            .pack(side=LEFT, padx=6)

    # ─────────────────────────────
    def _bind_tree_scrolling(self, area_widget):

        def on_mousewheel(event):
            # Windows/macOS: event.delta
            if event.delta == 0:
                return "break"
            step = int(-1 * (event.delta / 120)) if event.delta % 120 == 0 else int(-1 * (event.delta / 10))
            self.tree.yview_scroll(step, "units")
            return "break"

        def on_shift_mousewheel(event):
            if event.delta == 0:
                return "break"
            step = int(-1 * (event.delta / 120)) if event.delta % 120 == 0 else int(-1 * (event.delta / 10))
            self.tree.xview_scroll(step, "units")
            return "break"

        def on_linux_up(event):
            self.tree.yview_scroll(-3, "units")
            return "break"

        def on_linux_down(event):
            self.tree.yview_scroll(3, "units")
            return "break"

        def _bind(_e=None):
            area_widget.bind_all("<MouseWheel>", on_mousewheel, add="+")
            area_widget.bind_all("<Shift-MouseWheel>", on_shift_mousewheel, add="+")
            area_widget.bind_all("<Button-4>", on_linux_up, add="+")
            area_widget.bind_all("<Button-5>", on_linux_down, add="+")

        def _unbind(_e=None):
            area_widget.unbind_all("<MouseWheel>")
            area_widget.unbind_all("<Shift-MouseWheel>")
            area_widget.unbind_all("<Button-4>")
            area_widget.unbind_all("<Button-5>")

        area_widget.bind("<Enter>", _bind, add="+")
        area_widget.bind("<Leave>", _unbind, add="+")

    # ─────────────────────────────
    def _build_table(self):
        table_wrap = tb.Frame(self)
        table_wrap.pack(fill=BOTH, expand=True, padx=12, pady=(0, 10))

        table_wrap.rowconfigure(0, weight=1)
        table_wrap.columnconfigure(0, weight=1)

        cols = ("serial", "date", "name", "phone", "status")
        self.tree = tb.Treeview(table_wrap, columns=cols, show="headings", bootstyle=PRIMARY)

        headers = ["سریال", "تاریخ", "نام مشتری", "شماره تماس", "وضعیت"]
        widths = [160, 130, 240, 170, 170]
        anchors = [CENTER, CENTER, E, CENTER, CENTER]

        for c, t, w, a in zip(cols, headers, widths, anchors):
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w, anchor=a)

        self.tree.tag_configure("pending", foreground="#7FB3FF")
        self.tree.tag_configure("working", foreground="#FFD479")
        self.tree.tag_configure("ready", foreground="#B7E4C7")
        self.tree.tag_configure("delivered", foreground="#6EE7B7")

        # Scrollbars
        ybar = tb.Scrollbar(table_wrap, orient=VERTICAL, command=self.tree.yview)
        xbar = tb.Scrollbar(table_wrap, orient=HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=ybar.set, xscrollcommand=xbar.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        ybar.grid(row=0, column=1, sticky="ns")
        xbar.grid(row=1, column=0, sticky="ew")

        self._bind_tree_scrolling(table_wrap)

    # ─────────────────────────────
    def _build_buttons(self):
        bar = tb.Frame(self)
        bar.pack(fill=X, padx=12, pady=8)

        self.details_btn = tb.Button(
            bar, text="ℹ️ جزئیات", bootstyle=INFO,
            command=self.open_details, state=DISABLED, width=12
        )
        self.details_btn.pack(side=RIGHT, padx=6)

        self.edit_btn = tb.Button(
            bar, text="✏️ ویرایش", bootstyle=WARNING,
            command=self.edit_device, state=DISABLED, width=12
        )
        self.edit_btn.pack(side=RIGHT, padx=6)

        self.deliver_btn = tb.Button(
            bar, text="✅ تحویل", bootstyle=SUCCESS,
            command=self.deliver_device, state=DISABLED, width=12
        )
        self.deliver_btn.pack(side=RIGHT, padx=6)

        tb.Button(bar, text="🗑 حذف", bootstyle=DANGER, command=self.delete_device, width=10) \
            .pack(side=RIGHT, padx=6)

        self.invoice_btn = tb.Button(
            bar, text="🧾 فاکتور", bootstyle=SECONDARY,
            command=self.open_invoice, state=DISABLED, width=10
        )
        self.invoice_btn.pack(side=LEFT, padx=6)

    # ─────────────────────────────
    def clear_filters(self):
        self.name_var.set("")
        self.type_var.set("")
        self.model_var.set("")
        self.status_var.set("")
        self.date_from_var.set("")
        self.date_to_var.set("")
        self.filters = {}
        self.load_devices()

    def apply_filters(self):
        def parse_date(value: str):
            value = (value or "").strip()
            if not value:
                return None
            try:
                y, m, d = value.split("/")
                return int(y), int(m), int(d)
            except Exception:
                return None

        self.filters = {
            "name": self.name_var.get().strip(),
            "device_type": self.type_var.get().strip(),
            "model": self.model_var.get().strip(),
            "status": self.status_var.get().strip(),
            "date_from": parse_date(self.date_from_var.get()),
            "date_to": parse_date(self.date_to_var.get()),
        }
        self.load_devices()

    def _status_tag(self, status: str) -> str:
        s = (status or "").strip()
        if s in {"تحویل داده شد", "تحویل داده شده"}:
            return "delivered"
        if s == "در حال تعمیر":
            return "working"
        if s == "آماده تحویل":
            return "ready"
        return "pending"

    # ─────────────────────────────
    def load_devices(self):
        self.tree.delete(*self.tree.get_children())
        devices = get_devices_for_list(self.filters)

        for d in devices:
            device_id, serial, date, name, phone, status, *rest = d

            self.tree.insert(
                "",
                END,
                iid=device_id,
                values=(serial, date, name, phone, status),
                tags=(self._status_tag(status),)
            )

        self.on_select(None)

    def on_select(self, _event):
        sel = self.tree.focus()
        enabled = bool(sel)

        self.details_btn.config(state=NORMAL if enabled else DISABLED)
        self.edit_btn.config(state=NORMAL if enabled else DISABLED)
        self.invoice_btn.config(state=NORMAL if enabled else DISABLED)

        if not sel:
            self.deliver_btn.config(state=DISABLED)
            return

        status = self.tree.item(sel)["values"][4]
        delivered = status in ("تحویل داده شد", "تحویل داده شده")
        self.deliver_btn.config(state=DISABLED if delivered else NORMAL)

    # ─────────────────────────────
    def open_details(self):
        sel = self.tree.focus()
        if sel:
            DeviceDetailsWindow(self.master, int(sel))

    def edit_device(self):
        sel = self.tree.focus()
        if not sel:
            return
        DeviceForm(self.master, refresh_callback=self.load_devices, device_id=int(sel))

    def deliver_device(self):
        sel = self.tree.focus()
        if not sel:
            return
        update_device_status(int(sel), "تحویل داده شد")
        self.load_devices()

    def delete_device(self):
        sel = self.tree.focus()
        if not sel:
            return
        if messagebox.askyesno("حذف", "آیا مطمئن هستید؟"):
            delete_device(int(sel))
            self.load_devices()

    def open_invoice(self):
        sel = self.tree.focus()
        if sel:
            InvoiceWindow(self.master, int(sel))
