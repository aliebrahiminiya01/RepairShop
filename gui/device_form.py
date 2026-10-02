import ttkbootstrap as tb
from ttkbootstrap.constants import *
from tkinter import messagebox
import tkinter as tk

from ttkbootstrap.scrolled import ScrolledFrame

from database.db import insert_device, update_device, get_device_by_id
from gui.utils import to_english_digits, validate_jalali_date


def format_money(value: str):
    value = to_english_digits(value)
    digits = value.replace(",", "")
    if digits == "":
        return ""
    if not digits.isdigit():
        return ""
    return "{:,}".format(int(digits))


def _lbl(text: str) -> str:
    # fix RTL colon on Windows
    return f"{text}\u200e:"


# ──────────────────────────────────────────────────────────────
def enable_scrolledframe_wheel(scrolled: ScrolledFrame):
    canvas = None
    for attr in ("canvas", "_canvas", "cnv", "_cnv"):
        if hasattr(scrolled, attr):
            canvas = getattr(scrolled, attr)
            break
    if canvas is None:
        return

    def _on_mousewheel(event):
        if event.delta == 0:
            return "break"
        step = int(-1 * (event.delta / 120)) if event.delta % 120 == 0 else int(-1 * (event.delta / 10))
        canvas.yview_scroll(step, "units")
        return "break"

    def _on_linux_up(event):
        canvas.yview_scroll(-3, "units")
        return "break"

    def _on_linux_down(event):
        canvas.yview_scroll(3, "units")
        return "break"

    def _bind(_e=None):
        scrolled.bind_all("<MouseWheel>", _on_mousewheel, add="+")
        scrolled.bind_all("<Button-4>", _on_linux_up, add="+")
        scrolled.bind_all("<Button-5>", _on_linux_down, add="+")

    def _unbind(_e=None):
        scrolled.unbind_all("<MouseWheel>")
        scrolled.unbind_all("<Button-4>")
        scrolled.unbind_all("<Button-5>")

    scrolled.bind("<Enter>", _bind, add="+")
    scrolled.bind("<Leave>", _unbind, add="+")


class DeviceForm(tb.Toplevel):
    """
      - add: device_id=None
      - edit: device_id=int
    """

    def __init__(self, master, refresh_callback=None, device_id=None):
        super().__init__(master)

        self.refresh_callback = refresh_callback
        self.device_id = device_id

        self.title("ثبت دستگاه جدید" if device_id is None else "ویرایش دستگاه")
        self.minsize(720, 520)

        try:
            h = int(self.winfo_screenheight() * 0.82)
            w = 1070
            self.geometry(f"{w}x{h}")
        except tk.TclError:
            self.geometry("1070x680")

        # vars
        self.serial_var = tk.StringVar()
        self.model_var = tk.StringVar()

        self.year_var = tk.StringVar()
        self.month_var = tk.StringVar()
        self.day_var = tk.StringVar()

        self.parts_cost_var = tk.StringVar()
        self.received_cost_var = tk.StringVar()

        self.year_var.trace_add("write", lambda *args: self._force_english_digits(self.year_var))
        self.month_var.trace_add("write", lambda *args: self._force_english_digits(self.month_var))
        self.day_var.trace_add("write", lambda *args: self._force_english_digits(self.day_var))

        self.parts_cost_var.trace_add("write", lambda *args: self._on_money_change(self.parts_cost_var))
        self.received_cost_var.trace_add("write", lambda *args: self._on_money_change(self.received_cost_var))

        self._loaded_device = None
        if self.device_id is not None:
            self._loaded_device = get_device_by_id(self.device_id)

        self._build_form()
        self._fill_if_edit()

    # helpers
    def _force_english_digits(self, var: tk.StringVar):
        v = var.get()
        nv = to_english_digits(v)
        if v != nv:
            var.set(nv)

    def _build_form(self):
        sc = ScrolledFrame(self, autohide=True)
        sc.pack(fill=BOTH, expand=True)
        enable_scrolledframe_wheel(sc)

        container = tb.Frame(sc)
        container.pack(fill=BOTH, expand=True, padx=16, pady=14)

        header = tb.Frame(container)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        container.columnconfigure(0, weight=1)

        header_right = tb.Frame(header)
        header_right.pack(side=RIGHT)

        tb.Label(
            header_right,
            text="فرم ثبت دستگاه",
            font=("Helvetica", 14, "bold"),
            anchor=E,
            justify=RIGHT
        ).grid(row=0, column=0, sticky=E)

        tb.Label(
            header_right,
            text="(اطلاعات را کامل وارد کنید)",
            foreground="#888",
            anchor=E,
            justify=RIGHT
        ).grid(row=1, column=0, sticky=E, pady=(2, 0))

        # main
        main = tb.Frame(container)
        main.grid(row=1, column=0, sticky="nsew")
        container.rowconfigure(1, weight=1)

        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=1)

        customer_box = tb.Labelframe(main, text="اطلاعات مشتری", bootstyle=SECONDARY, labelanchor="ne")
        customer_box.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=6)
        customer_box.columnconfigure(0, weight=1)

        tb.Label(customer_box, text=_lbl("نام مشتری"), anchor=E).grid(row=0, column=0, sticky="ew")
        self.name_entry = tb.Entry(customer_box, justify=RIGHT)
        self.name_entry.grid(row=1, column=0, sticky="ew", pady=(4, 10))

        tb.Label(customer_box, text=_lbl("شماره تماس"), anchor=E).grid(row=2, column=0, sticky="ew")
        self.phone_entry = tb.Entry(customer_box, justify=RIGHT)
        self.phone_entry.grid(row=3, column=0, sticky="ew", pady=(4, 10))

        tb.Label(customer_box, text=_lbl("نوع دستگاه"), anchor=E).grid(row=4, column=0, sticky="ew")
        self.type_combo = tb.Combobox(
            customer_box,
            values=["تلویزیون", "مانیتور", "گیرنده دیجیتال", "ماهواره", "سیستم صوتی", "سایر"],
            state="readonly",
            justify=RIGHT
        )
        self.type_combo.grid(row=5, column=0, sticky="ew", pady=(4, 10))

        tb.Label(customer_box, text=_lbl("وضعیت"), anchor=E).grid(row=6, column=0, sticky="ew")
        self.status_combo = tb.Combobox(
            customer_box,
            values=["در انتظار بررسی", "در حال تعمیر", "آماده تحویل", "تحویل داده شد"],
            state="readonly",
            justify=RIGHT
        )
        self.status_combo.current(0)
        self.status_combo.grid(row=7, column=0, sticky="ew", pady=(4, 6))

        device_box = tb.Labelframe(main, text="اطلاعات دستگاه", bootstyle=PRIMARY, labelanchor="ne")
        device_box.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=6)
        device_box.columnconfigure(0, weight=1)

        top_row = tb.Frame(device_box)
        top_row.grid(row=0, column=0, sticky="ew", pady=(2, 10))
        top_row.columnconfigure(0, weight=1)
        top_row.columnconfigure(1, weight=1)

        f_serial = tb.Frame(top_row)
        f_serial.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        f_serial.columnconfigure(0, weight=1)

        tb.Label(f_serial, text=_lbl("سریال دستگاه"), anchor=E).grid(row=0, column=0, sticky="ew")
        tb.Entry(f_serial, textvariable=self.serial_var, justify=RIGHT) \
            .grid(row=1, column=0, sticky="ew", pady=(4, 0))

        f_model = tb.Frame(top_row)
        f_model.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        f_model.columnconfigure(0, weight=1)

        tb.Label(f_model, text=_lbl("مدل دستگاه"), anchor=E).grid(row=0, column=0, sticky="ew")
        tb.Entry(f_model, textvariable=self.model_var, justify=RIGHT) \
            .grid(row=1, column=0, sticky="ew", pady=(4, 0))

        tb.Label(device_box, text=_lbl("تاریخ (روز/ماه/سال)"), anchor=E).grid(row=1, column=0, sticky="ew")
        date_frame = tb.Frame(device_box)
        date_frame.grid(row=2, column=0, sticky="ew", pady=(4, 10))

        tb.Entry(date_frame, width=10, textvariable=self.year_var, justify=RIGHT) \
            .grid(row=0, column=0, padx=5, sticky=E)
        tb.Label(date_frame, text="/").grid(row=0, column=1)
        tb.Entry(date_frame, width=6, textvariable=self.month_var, justify=RIGHT) \
            .grid(row=0, column=2, padx=5)
        tb.Label(date_frame, text="/").grid(row=0, column=3)
        tb.Entry(date_frame, width=6, textvariable=self.day_var, justify=RIGHT) \
            .grid(row=0, column=4, padx=5)

        cost_row = tb.Frame(device_box)
        cost_row.grid(row=3, column=0, sticky="ew", pady=(0, 6))
        cost_row.columnconfigure(0, weight=1)
        cost_row.columnconfigure(1, weight=1)

        f_parts = tb.Frame(cost_row)
        f_parts.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        f_parts.columnconfigure(0, weight=1)

        tb.Label(f_parts, text=_lbl("هزینه قطعات"), anchor=E).grid(row=0, column=0, sticky="ew")
        tb.Entry(f_parts, textvariable=self.parts_cost_var, justify=RIGHT) \
            .grid(row=1, column=0, sticky="ew", pady=(4, 0))

        f_recv = tb.Frame(cost_row)
        f_recv.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        f_recv.columnconfigure(0, weight=1)

        tb.Label(f_recv, text=_lbl("هزینه دریافتی"), anchor=E).grid(row=0, column=0, sticky="ew")
        tb.Entry(f_recv, textvariable=self.received_cost_var, justify=RIGHT) \
            .grid(row=1, column=0, sticky="ew", pady=(4, 0))

        note_box = tb.Labelframe(main, text="یادداشت تعمیر", bootstyle=INFO, labelanchor="ne")
        note_box.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(10, 6))
        note_box.columnconfigure(0, weight=1)

        self.note_text = tb.Text(note_box, height=5, wrap="word")
        self.note_text.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        tb.Separator(container).grid(row=2, column=0, sticky="ew", pady=10)

        btn_row = tb.Frame(container)
        btn_row.grid(row=3, column=0, sticky="w", pady=(2, 10))

        tb.Button(
            btn_row,
            text="💾 ذخیره",
            bootstyle=SUCCESS,
            command=self._save_device,
            width=14
        ).pack(side=LEFT, padx=6)

        tb.Button(
            btn_row,
            text="بستن",
            command=self.destroy,
            width=12
        ).pack(side=LEFT)

        tb.Frame(container, height=6).grid(row=4, column=0)

    def _fill_if_edit(self):
        if not self._loaded_device:
            return

        (
            _id, customer_name, phone, device_type, model, serial,
            status, note, year, month, day, parts_cost, received_cost, _created
        ) = self._loaded_device

        self.serial_var.set(serial or "")
        self.model_var.set(model or "")
        self.name_entry.insert(0, customer_name or "")
        self.phone_entry.insert(0, phone or "")

        self.type_combo.set(device_type or "")
        self.status_combo.set(status or "در انتظار بررسی")

        self.year_var.set(str(year or ""))
        self.month_var.set(str(month or ""))
        self.day_var.set(str(day or ""))

        self.parts_cost_var.set(f"{(parts_cost or 0):,}" if parts_cost else "")
        self.received_cost_var.set(f"{(received_cost or 0):,}" if received_cost else "")

        self.note_text.insert("1.0", note or "")

    def _get_int_money(self, var):
        v = to_english_digits(var.get()).replace(",", "").strip()
        return int(v) if v.isdigit() else 0

    def _save_device(self):
        name = self.name_entry.get().strip()

        phone = to_english_digits(self.phone_entry.get().strip())
        model = to_english_digits(self.model_var.get().strip())
        serial = to_english_digits(self.serial_var.get().strip())

        device_type = self.type_combo.get().strip()
        status = self.status_combo.get().strip()
        note = self.note_text.get("1.0", "end").strip()

        self.phone_entry.delete(0, "end")
        self.phone_entry.insert(0, phone)
        self.model_var.set(model)
        self.serial_var.set(serial)

        if not name or not phone or not device_type:
            messagebox.showerror("خطا", "لطفاً اطلاعات ضروری را کامل کنید")
            return

        y_txt = to_english_digits(self.year_var.get()).strip()
        m_txt = to_english_digits(self.month_var.get()).strip()
        d_txt = to_english_digits(self.day_var.get()).strip()

        self.year_var.set(y_txt)
        self.month_var.set(m_txt)
        self.day_var.set(d_txt)

        if not (y_txt.isdigit() and m_txt.isdigit() and d_txt.isdigit()):
            messagebox.showerror("خطا", "تاریخ نامعتبر است (فقط عدد وارد کنید)")
            return

        y = int(y_txt)
        m = int(m_txt)
        d = int(d_txt)

        ok, msg = validate_jalali_date(y, m, d)
        if not ok:
            messagebox.showerror("خطا", msg)
            return

        parts_cost = self._get_int_money(self.parts_cost_var)
        received_cost = self._get_int_money(self.received_cost_var)

        if self.device_id is None:
            insert_device(
                name, phone, device_type, model, serial,
                status, note, y, m, d, parts_cost, received_cost
            )
            messagebox.showinfo("موفق", "دستگاه ثبت شد")
        else:
            update_device(
                self.device_id,
                name, phone, device_type, model, serial,
                status, note, y, m, d, parts_cost, received_cost
            )
            messagebox.showinfo("موفق", "دستگاه ویرایش شد")

        if self.refresh_callback:
            self.refresh_callback()

        self.destroy()

    def _on_money_change(self, var):
        value = var.get()
        formatted = format_money(value)
        if value != formatted:
            var.set(formatted)
