import os
import sys
import tempfile
import subprocess
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from tkinter import filedialog, messagebox

from datetime import date
from database.db import connect

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import cm
from reportlab.pdfbase.pdfmetrics import stringWidth

import arabic_reshaper
from bidi.algorithm import get_display

from gui.utils import resource_path


# ──────────────────────────────────────────────────────────────
class MouseWheelScroller:
    def __init__(self, root_widget, canvas_widget):
        self.root = root_widget
        self.canvas = canvas_widget
        self._bound = False

        self.root.bind("<Enter>", self._bind, add="+")
        self.root.bind("<Leave>", self._unbind, add="+")

    def _on_mousewheel(self, event):
        if sys.platform == "darwin":
            delta = event.delta
            if delta == 0:
                return
            self.canvas.yview_scroll(int(-1 * delta), "units")
        else:
            # Windows
            delta = event.delta
            if delta == 0:
                return
            self.canvas.yview_scroll(int(-1 * (delta / 120)), "units")
        return "break"

    def _on_linux_up(self, event):
        self.canvas.yview_scroll(-3, "units")
        return "break"

    def _on_linux_down(self, event):
        self.canvas.yview_scroll(3, "units")
        return "break"

    def _bind(self, event=None):
        if self._bound:
            return
        self._bound = True

        self.root.bind_all("<MouseWheel>", self._on_mousewheel, add="+")
        self.root.bind_all("<Button-4>", self._on_linux_up, add="+")
        self.root.bind_all("<Button-5>", self._on_linux_down, add="+")

    def _unbind(self, event=None):
        if not self._bound:
            return
        self._bound = False

        self.root.unbind_all("<MouseWheel>")
        self.root.unbind_all("<Button-4>")
        self.root.unbind_all("<Button-5>")


# ──────────────────────────────────────────────────────────────
class ScrollableFrame(tb.Frame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.canvas = tb.Canvas(self, highlightthickness=0)
        self.v_scroll = tb.Scrollbar(self, orient=VERTICAL, command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.v_scroll.set)

        self.v_scroll.pack(side=RIGHT, fill=Y)
        self.canvas.pack(side=LEFT, fill=BOTH, expand=True)

        self.inner = tb.Frame(self.canvas)
        self._window_id = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")

        self.inner.bind("<Configure>", self._on_frame_configure, add="+")
        self.canvas.bind("<Configure>", self._on_canvas_configure, add="+")

        self._mw = MouseWheelScroller(self, self.canvas)

    def _on_frame_configure(self, event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfigure(self._window_id, width=event.width)


# ──────────────────────────────────────────────────────────────
class InvoiceWindow(tb.Toplevel):

    def __init__(self, master, device_id: int):
        super().__init__(master)
        self.device_id = device_id

        self.title("فاکتور")
        self.geometry("820x860")
        self.minsize(780, 640)

        self._last_pdf_path = None
        self.final_price_var = tb.StringVar()

        self._load_device()
        self._build_ui()

    # ─────────────────────────────
    def _rtl(self, text) -> str:
        if text is None:
            return ""
        reshaped = arabic_reshaper.reshape(str(text))
        return get_display(reshaped)

    def draw_rtl(self, c, text, x, y, font="Vazir", size=11):
        rtl_text = self._rtl(text)
        c.setFont(font, size)
        w = stringWidth(rtl_text, font, size)
        c.drawString(x - w, y, rtl_text)

    # ─────────────────────────────
    def _load_device(self):
        conn = connect()
        cur = conn.cursor()
        cur.execute("SELECT * FROM devices WHERE id=?", (self.device_id,))
        self.device = cur.fetchone()
        conn.close()

        if not self.device:
            messagebox.showerror("خطا", "دستگاه پیدا نشد")
            self.destroy()
            return

    # ─────────────────────────────
    def _build_ui(self):
        sc = ScrollableFrame(self)
        sc.pack(fill=BOTH, expand=True)

        root = tb.Frame(sc.inner)
        root.pack(fill=BOTH, expand=True, padx=16, pady=16)

        # ---------- header
        header = tb.Frame(root)
        header.pack(fill=X)

        tb.Label(header, text="🧾 فاکتور تعمیرگاه", font=("Helvetica", 16, "bold")).pack(side=RIGHT)
        tb.Label(
            header,
            text=f"تاریخ صدور: {date.today().strftime('%Y/%m/%d')}",
            font=("Helvetica", 11),
            anchor=E
        ).pack(side=LEFT)

        tb.Separator(root).pack(fill=X, pady=10)

        (
            _id, customer_name, phone, device_type, model,
            serial, status, note, year, month,
            day, parts_cost, received_cost, created_at
        ) = self.device

        # ---------- info
        info = tb.Labelframe(root, text="اطلاعات دستگاه / مشتری", bootstyle=SECONDARY)
        info.pack(fill=X, pady=8)

        grid = tb.Frame(info)
        grid.pack(fill=X, padx=10, pady=10)

        def row(label, value, r, c):
            tb.Label(grid, text=f"{label}:", anchor=E, width=12).grid(row=r, column=c, sticky=E, padx=6, pady=4)
            tb.Label(grid, text=value if value else "-", anchor=E).grid(row=r, column=c - 1, sticky=E, padx=6, pady=4)

        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(2, weight=1)

        row("نام مشتری", customer_name, 0, 3)
        row("شماره تماس", phone, 0, 1)

        row("نوع دستگاه", device_type, 1, 3)
        row("مدل", model, 1, 1)

        row("سریال", serial, 2, 3)
        row("وضعیت", status, 2, 1)

        row("تاریخ پذیرش", f"{year:04d}/{month:02d}/{day:02d}", 3, 3)
        row("کد", str(_id), 3, 1)

        # ---------- note
        note_box = tb.Labelframe(root, text="یادداشت تعمیر", bootstyle=INFO)
        note_box.pack(fill=X, pady=8)

        self.note_lbl = tb.Label(
            note_box,
            text=note if note else "—",
            anchor=E,
            justify=RIGHT,
            wraplength=760
        )
        self.note_lbl.pack(fill=X, padx=10, pady=10)

        # ---------- parts
        parts_box = tb.Labelframe(root, text="قطعات مصرفی", bootstyle=PRIMARY)
        parts_box.pack(fill=X, pady=10)

        tbl = tb.Frame(parts_box)
        tbl.pack(fill=X, padx=10, pady=10)

        tb.Label(tbl, text="نام قطعه", anchor=E, width=35, relief=SOLID).grid(row=0, column=1, sticky="ew")
        tb.Label(tbl, text="هزینه", anchor=E, width=18, relief=SOLID).grid(row=0, column=0, sticky="ew")

        self.part_entries = []
        for i in range(8):
            name_e = tb.Entry(tbl, justify=RIGHT)
            price_e = tb.Entry(tbl, justify=RIGHT)
            name_e.grid(row=i + 1, column=1, padx=2, pady=2, sticky="ew")
            price_e.grid(row=i + 1, column=0, padx=2, pady=2, sticky="ew")
            self.part_entries.append((name_e, price_e))

        tbl.columnconfigure(1, weight=1)

        # ---------- totals
        totals = tb.Frame(root)
        totals.pack(fill=X, pady=8)

        tb.Label(totals, text="هزینه نهایی (دستی):", anchor=E).pack(side=RIGHT, padx=6)
        tb.Entry(totals, textvariable=self.final_price_var, justify=RIGHT, width=22).pack(side=RIGHT, padx=6)
        tb.Label(totals, text="(اختیاری)", foreground="#999").pack(side=RIGHT, padx=6)

        # ---------- buttons
        btns = tb.Frame(root)
        btns.pack(fill=X, pady=14)

        tb.Button(btns, text="پیش‌نمایش", bootstyle=SECONDARY, command=self.preview_pdf).pack(side=LEFT, padx=6)
        tb.Button(btns, text="ذخیره PDF", bootstyle=SUCCESS, command=self.export_pdf).pack(side=LEFT, padx=6)
        tb.Button(btns, text="🖨 چاپ", bootstyle=INFO, command=self.print_invoice).pack(side=LEFT, padx=6)
        tb.Button(btns, text="بستن", bootstyle=DANGER, command=self.destroy).pack(side=RIGHT, padx=6)

        tb.Frame(root, height=10).pack(fill=X)

    # ─────────────────────────────
    def _ensure_font(self):
        font_path = resource_path("Vazir.ttf")
        if not os.path.exists(font_path):
            raise FileNotFoundError(f"فونت پیدا نشد: {font_path}")

        if "Vazir" not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont("Vazir", font_path))

    def _wrap_rtl_lines(self, text: str, max_width_pt: float, font="Vazir", size=10):
        text = (text or "").strip()
        if not text:
            return ["—"]

        words = text.split()
        lines = []
        cur = ""

        for w in words:
            test = (cur + " " + w).strip()
            test_rtl = self._rtl(test)
            if stringWidth(test_rtl, font, size) <= max_width_pt:
                cur = test
            else:
                if cur:
                    lines.append(cur)
                cur = w

        if cur:
            lines.append(cur)

        return lines

    # ─────────────────────────────
    def _export_pdf_to_path(self, path: str):
        self._ensure_font()

        c = canvas.Canvas(path, pagesize=A4)
        w, h = A4

        x_right = w - 2 * cm
        x_left = 2 * cm

        def new_page():
            c.showPage()
            self._ensure_font()

        def ensure_space(min_y=2.5 * cm):
            nonlocal y
            if y < min_y:
                new_page()
                y = h - 2 * cm

        y = h - 2 * cm
        self.draw_rtl(c, "فاکتور تعمیرگاه", x_right, y, size=16)
        y -= 0.9 * cm

        self.draw_rtl(c, f"تاریخ صدور: {date.today().strftime('%Y/%m/%d')}", x_right, y, size=11)
        y -= 0.6 * cm

        c.line(x_left, y, x_right, y)
        y -= 0.8 * cm

        (
            _id, customer_name, phone, device_type, model,
            serial, status, note, year, month,
            day, parts_cost, received_cost, created_at
        ) = self.device

        info_lines = [
            f"کد: {_id}",
            f"نام مشتری: {customer_name}",
            f"شماره تماس: {phone}",
            f"نوع دستگاه: {device_type}",
            f"مدل: {model or '-'}",
            f"سریال: {serial or '-'}",
            f"وضعیت: {status or '-'}",
            f"تاریخ پذیرش: {year:04d}/{month:02d}/{day:02d}",
        ]

        for line in info_lines:
            ensure_space()
            self.draw_rtl(c, line, x_right, y, size=11)
            y -= 0.65 * cm

        y -= 0.2 * cm
        ensure_space()
        c.line(x_left, y, x_right, y)
        y -= 0.8 * cm

        ensure_space()
        self.draw_rtl(c, "یادداشت تعمیر:", x_right, y, size=12)
        y -= 0.65 * cm

        note_lines = self._wrap_rtl_lines(
            note or "—",
            max_width_pt=(w - 4 * cm),
            font="Vazir",
            size=10
        )

        for ch in note_lines[:8]:
            ensure_space()
            self.draw_rtl(c, ch, x_right, y, size=10)
            y -= 0.55 * cm

        y -= 0.2 * cm
        ensure_space()
        c.line(x_left, y, x_right, y)
        y -= 0.9 * cm

        ensure_space()
        self.draw_rtl(c, "قطعات مصرفی", x_right, y, size=13)
        y -= 0.8 * cm

        col_name_x = x_right - 4 * cm
        col_price_x = x_left + 4 * cm

        ensure_space()
        self.draw_rtl(c, "نام قطعه", col_name_x, y, size=11)
        self.draw_rtl(c, "هزینه", col_price_x, y, size=11)
        y -= 0.5 * cm
        c.line(x_left, y, x_right, y)
        y -= 0.4 * cm

        any_row = False
        for name_e, price_e in self.part_entries:
            pname = (name_e.get() or "").strip()
            pprice = (price_e.get() or "").strip()
            if not pname and not pprice:
                continue

            any_row = True
            ensure_space(min_y=3.2 * cm)
            self.draw_rtl(c, pname if pname else "-", col_name_x, y, size=10)
            self.draw_rtl(c, pprice if pprice else "-", col_price_x, y, size=10)
            y -= 0.55 * cm

        if not any_row:
            ensure_space()
            self.draw_rtl(c, "—", x_right, y, size=10)
            y -= 0.55 * cm

        y -= 0.3 * cm
        ensure_space()
        c.line(x_left, y, x_right, y)
        y -= 0.9 * cm

        final_price = (self.final_price_var.get() or "").strip()
        if final_price:
            ensure_space()
            self.draw_rtl(c, f"هزینه نهایی: {final_price}", x_right, y, size=12)
            y -= 0.8 * cm

        y -= 0.6 * cm
        ensure_space(min_y=3 * cm)
        self.draw_rtl(c, "امضای مشتری", x_right, y, size=11)
        self.draw_rtl(c, "امضای تعمیرگاه", x_left + 6 * cm, y, size=11)

        c.save()
        self._last_pdf_path = path

    # ─────────────────────────────
    def export_pdf(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")]
        )
        if not path:
            return
        try:
            self._export_pdf_to_path(path)
            messagebox.showinfo("موفق", "PDF ذخیره شد")
        except Exception as e:
            messagebox.showerror("خطا", f"ذخیره انجام نشد:\n{e}")

    # ─────────────────────────────
    def preview_pdf(self):
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        tmp.close()

        try:
            self._export_pdf_to_path(tmp.name)
        except Exception as e:
            messagebox.showerror("خطا", f"ساخت PDF انجام نشد:\n{e}")
            return

        try:
            import pymupdf as fitz
            from PIL import Image, ImageTk
        except Exception as e:
            messagebox.showerror("خطا", "پیش‌نمایش نیاز به PyMuPDF و Pillow دارد.\n" + str(e))
            return

        self._show_pdf_preview(tmp.name, fitz, Image, ImageTk)

    # ─────────────────────────────
    def _show_pdf_preview(self, path, fitz, Image, ImageTk):
        win = tb.Toplevel(self)
        win.title("پیش‌نمایش فاکتور")
        win.geometry("860x920")
        win.minsize(1250, 640)

        top = tb.Frame(win)
        top.pack(fill=X, padx=10, pady=10)

        tb.Button(top, text="🖨 چاپ", bootstyle=INFO, command=lambda: self._print_path(path)).pack(side=LEFT, padx=5)
        tb.Button(top, text="ذخیره نهایی", bootstyle=SUCCESS, command=self.export_pdf).pack(side=LEFT, padx=5)
        tb.Button(top, text="بستن", bootstyle=DANGER, command=win.destroy).pack(side=RIGHT, padx=5)

        body = tb.Frame(win)
        body.pack(fill=BOTH, expand=True, padx=10, pady=(0, 10))

        pdf = fitz.open(path)
        try:
            page = pdf.load_page(0)
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        finally:
            pdf.close()

        photo = ImageTk.PhotoImage(img)

        # canvas + scrollbar
        canvas_w = tb.Canvas(body, highlightthickness=0)
        vbar = tb.Scrollbar(body, orient=VERTICAL, command=canvas_w.yview)
        canvas_w.configure(yscrollcommand=vbar.set)

        vbar.pack(side=RIGHT, fill=Y)
        canvas_w.pack(side=LEFT, fill=BOTH, expand=True)

        holder = tb.Frame(canvas_w)
        canvas_w.create_window((0, 0), window=holder, anchor="nw")

        lbl = tb.Label(holder, image=photo)
        lbl.image = photo
        lbl.pack(padx=5, pady=5)

        def _cfg(_e=None):
            canvas_w.configure(scrollregion=canvas_w.bbox("all"))

        holder.bind("<Configure>", _cfg, add="+")

        MouseWheelScroller(body, canvas_w)

    # ─────────────────────────────
    def _print_path(self, pdf_path: str):
        try:
            if sys.platform.startswith("win"):
                os.startfile(pdf_path, "print")
            else:
                subprocess.run(["lp", pdf_path], check=True)

            messagebox.showinfo("چاپ", "دستور چاپ ارسال شد ✅")
        except Exception as e:
            messagebox.showerror("خطا", f"چاپ انجام نشد:\n{e}")

    def print_invoice(self):
        if self._last_pdf_path and os.path.exists(self._last_pdf_path):
            self._print_path(self._last_pdf_path)
            return

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        tmp.close()
        try:
            self._export_pdf_to_path(tmp.name)
            self._print_path(tmp.name)
        except Exception as e:
            messagebox.showerror("خطا", f"چاپ انجام نشد:\n{e}")
