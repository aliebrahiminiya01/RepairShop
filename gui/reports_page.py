import ttkbootstrap as tb
from ttkbootstrap.constants import *
from tkinter import messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

import arabic_reshaper
from bidi.algorithm import get_display

from database.db import (
    get_report_by_date,
    get_status_counts_by_range,
    get_top_device_types_by_range,
    get_monthly_series_by_range,
    get_yearly_series_by_range
)
from gui.utils import jalali_days_in_month, to_english_digits


def _parse_jalali_date(y_str: str, m_str: str, d_str: str):
    y_str = to_english_digits(y_str).strip()
    m_str = to_english_digits(m_str).strip()
    d_str = to_english_digits(d_str).strip()

    if not (y_str.isdigit() and m_str.isdigit() and d_str.isdigit()):
        raise ValueError("تاریخ باید فقط عدد باشد (سال/ماه/روز)")

    y = int(y_str)
    m = int(m_str)
    d = int(d_str)

    if y < 1200 or y > 1600:
        raise ValueError("سال معتبر نیست (مثلاً 1404)")

    if not (1 <= m <= 12):
        raise ValueError("ماه باید بین 1 تا 12 باشد")

    dim = jalali_days_in_month(y, m)
    if not (1 <= d <= dim):
        raise ValueError(f"روز برای این ماه باید بین 1 تا {dim} باشد")

    return y, m, d


def _date_int(y, m, d):
    return y * 10000 + m * 100 + d


def _rtl(text):
    if text is None:
        return ""
    reshaped = arabic_reshaper.reshape(str(text))
    return get_display(reshaped)


def _next_month(y, m):
    if m == 12:
        return y + 1, 1
    return y, m + 1


def _month_key(y, m):
    return y * 100 + m


def _apply_xticks(ax, labels, max_labels=12, rotation=90):
    n = len(labels)
    if n == 0:
        return

    step = max(1, (n + max_labels - 1) // max_labels)
    positions = list(range(0, n, step))
    shown_labels = [labels[i] for i in positions]

    ax.set_xticks(positions)
    ax.set_xticklabels(shown_labels, rotation=rotation)

    for tick in ax.get_xticklabels():
        tick.set_ha("center")
        tick.set_va("top")


# Scroll helpers for tables

def _bind_tree_wheel(tree: tb.Treeview, area_widget):

    def on_mousewheel(event):
        if event.delta == 0:
            return "break"
        step = int(-1 * (event.delta / 120)) if event.delta % 120 == 0 else int(-1 * (event.delta / 10))
        tree.yview_scroll(step, "units")
        return "break"

    def on_linux_up(event):
        tree.yview_scroll(-3, "units")
        return "break"

    def on_linux_down(event):
        tree.yview_scroll(3, "units")
        return "break"

    def _bind(_e=None):
        area_widget.bind_all("<MouseWheel>", on_mousewheel, add="+")
        area_widget.bind_all("<Button-4>", on_linux_up, add="+")
        area_widget.bind_all("<Button-5>", on_linux_down, add="+")

    def _unbind(_e=None):
        area_widget.unbind_all("<MouseWheel>")
        area_widget.unbind_all("<Button-4>")
        area_widget.unbind_all("<Button-5>")

    area_widget.bind("<Enter>", _bind, add="+")
    area_widget.bind("<Leave>", _unbind, add="+")


# Reports Page

class ReportsPage(tb.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.pack(fill=BOTH, expand=True)

        self._build_ui()
        self._init_chart_placeholder()

    def _build_ui(self):
        top = tb.Labelframe(self, text="گزارش بر اساس بازه تاریخ", bootstyle=SECONDARY, labelanchor="ne")
        top.pack(fill=X, padx=12, pady=10)

        self.sy = tb.StringVar(value="")
        self.sm = tb.StringVar(value="")
        self.sd = tb.StringVar(value="")

        self.ey = tb.StringVar(value="")
        self.em = tb.StringVar(value="")
        self.ed = tb.StringVar(value="")

        # Grid columns: [0]=button | [1]=spacer | d / m / y + label
        top.grid_columnconfigure(0, weight=0)
        top.grid_columnconfigure(1, weight=1)  # spacer
        for c in (2, 3, 4, 5, 6, 7):
            top.grid_columnconfigure(c, weight=0)

        def date_row(parent, row_idx, title, yvar, mvar, dvar):
            tb.Label(parent, text=title, anchor=E, justify=RIGHT).grid(
                row=row_idx, column=7, sticky=E, padx=(10, 6), pady=8
            )

            ent_y = tb.Entry(parent, width=8, textvariable=yvar, justify=RIGHT)
            ent_m = tb.Entry(parent, width=5, textvariable=mvar, justify=RIGHT)
            ent_d = tb.Entry(parent, width=5, textvariable=dvar, justify=RIGHT)

            ent_y.grid(row=row_idx, column=6, sticky=E, padx=(0, 6))
            tb.Label(parent, text="/").grid(row=row_idx, column=5)
            ent_m.grid(row=row_idx, column=4, sticky=E, padx=6)
            tb.Label(parent, text="/").grid(row=row_idx, column=3)
            ent_d.grid(row=row_idx, column=2, sticky=E, padx=(6, 0))

            tb.Label(parent, text="(سال/ماه/روز)", anchor=E, justify=RIGHT).grid(
                row=row_idx, column=1, sticky=E, padx=(12, 0)
            )

        date_row(top, 0, "از تاریخ:", self.sy, self.sm, self.sd)
        date_row(top, 1, "تا تاریخ:", self.ey, self.em, self.ed)

        self.btn_calc = tb.Button(
            top, text="محاسبه گزارش", bootstyle=SUCCESS, command=self.calculate_report, width=18
        )
        self.btn_calc.grid(row=0, column=0, rowspan=2, sticky=E, padx=12, pady=8)

        body = tb.Frame(self)
        body.pack(fill=BOTH, expand=True, padx=12, pady=10)

        left = tb.Frame(body, width=420)
        left.pack(side=LEFT, fill=Y)
        left.pack_propagate(False)

        left.rowconfigure(0, weight=1)
        left.rowconfigure(1, weight=1)
        left.columnconfigure(0, weight=1)

        right = tb.Labelframe(body, text="نمودار", bootstyle=SECONDARY, labelanchor="ne")
        right.pack(side=LEFT, fill=BOTH, expand=True, padx=(12, 0))

        self.status_table = self._make_table(
            left, "وضعیت‌ها در بازه",
            ("status", "count"),
            ("وضعیت", "تعداد"),
            (260, 90)
        )
        self.status_table.grid(row=0, column=0, sticky="nsew", pady=(0, 12))

        self.types_table = self._make_table(
            left, "نوع دستگاه‌ها (Top)",
            ("type", "count"),
            ("نوع دستگاه", "تعداد"),
            (260, 90)
        )
        self.types_table.grid(row=1, column=0, sticky="nsew")

        self.chart_frame = tb.Frame(right)
        self.chart_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)

        btns = tb.Frame(right)
        btns.pack(fill=X, padx=10, pady=(0, 10))

        tb.Button(
            btns, text="نمودار ماهانه", bootstyle=INFO,
            command=lambda: self.open_chart_window(mode="monthly")
        ).pack(side=LEFT, padx=6)

        tb.Button(
            btns, text="نمودار سالانه", bootstyle=PRIMARY,
            command=lambda: self.open_chart_window(mode="yearly")
        ).pack(side=LEFT, padx=6)

    def _make_table(self, parent, title, cols, headings, widths):
        frame = tb.Labelframe(parent, text=title, bootstyle=SECONDARY, labelanchor="ne")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        # tree + scrollbar
        tree = tb.Treeview(frame, columns=cols, show="headings")
        ybar = tb.Scrollbar(frame, orient=VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=ybar.set)

        tree.grid(row=0, column=0, sticky="nsew", padx=(8, 0), pady=8)
        ybar.grid(row=0, column=1, sticky="ns", padx=(0, 8), pady=8)

        for c, h, w in zip(cols, headings, widths):
            tree.heading(c, text=h)
            tree.column(c, width=w, anchor=CENTER)

        _bind_tree_wheel(tree, frame)

        frame.tree = tree
        return frame

    def _init_chart_placeholder(self):
        for w in self.chart_frame.winfo_children():
            w.destroy()

        tb.Label(
            self.chart_frame,
            text="برای نمایش نمودار، تاریخ‌ها را وارد کنید و «محاسبه گزارش» را بزنید.",
            anchor=CENTER
        ).pack(fill=BOTH, expand=True)

    def _clear_table(self, table_frame):
        table_frame.tree.delete(*table_frame.tree.get_children())

    def _validate_range(self, sy, sm, sd, ey, em, ed):
        if _date_int(sy, sm, sd) > _date_int(ey, em, ed):
            raise ValueError("تاریخ شروع نباید از تاریخ پایان بزرگ‌تر باشد")

    def calculate_report(self):
        try:
            sy, sm, sd = _parse_jalali_date(self.sy.get(), self.sm.get(), self.sd.get())
            ey, em, ed = _parse_jalali_date(self.ey.get(), self.em.get(), self.ed.get())

            self._validate_range(sy, sm, sd, ey, em, ed)

            _parts, _received, _profit = get_report_by_date(sy, sm, sd, ey, em, ed)

            status_rows = get_status_counts_by_range(sy, sm, sd, ey, em, ed)
            self._clear_table(self.status_table)
            for st, cnt in status_rows:
                self.status_table.tree.insert("", END, values=(st or "-", cnt))

            types_rows = get_top_device_types_by_range(sy, sm, sd, ey, em, ed, limit=10)
            self._clear_table(self.types_table)
            for t, cnt in types_rows:
                self.types_table.tree.insert("", END, values=(t or "-", cnt))

            self._draw_embedded_preview_chart(sy, sm, sd, ey, em, ed)

        except Exception as e:
            messagebox.showerror("خطا", str(e))

    def _draw_embedded_preview_chart(self, sy, sm, sd, ey, em, ed):
        for w in self.chart_frame.winfo_children():
            w.destroy()

        series = get_monthly_series_by_range(sy, sm, sd, ey, em, ed)
        if not series:
            tb.Label(self.chart_frame, text="داده‌ای برای نمودار وجود ندارد", anchor=CENTER) \
                .pack(fill=BOTH, expand=True)
            return

        x_labels, rec, prt, prof = self._build_monthly_continuous_series(sy, sm, ey, em, series)

        fig = Figure(figsize=(7.6, 4.2), dpi=100)
        ax = fig.add_subplot(111)

        x = list(range(len(x_labels)))
        ax.plot(x, rec, marker="o", label=_rtl("دریافتی"))
        ax.plot(x, prt, marker="o", label=_rtl("قطعات"))
        ax.plot(x, prof, marker="o", label=_rtl("سود"))

        ax.set_title(_rtl(f"گزارش بازه {sy}/{sm:02d} تا {ey}/{em:02d}"))
        ax.set_xlabel(_rtl("ماه/سال"))
        ax.set_ylabel(_rtl("مبلغ"))

        _apply_xticks(ax, x_labels, max_labels=10, rotation=90)

        ax.grid(True)
        ax.legend()

        fig.tight_layout()
        fig.subplots_adjust(bottom=0.30)

        canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=BOTH, expand=True)

    def open_chart_window(self, mode="monthly"):
        try:
            sy, sm, sd = _parse_jalali_date(self.sy.get(), self.sm.get(), self.sd.get())
            ey, em, ed = _parse_jalali_date(self.ey.get(), self.em.get(), self.ed.get())

            self._validate_range(sy, sm, sd, ey, em, ed)

        except Exception as e:
            messagebox.showerror("خطا", str(e))
            return

        win = tb.Toplevel(self)
        win.title("نمودار گزارش")
        win.geometry("1000x650")

        frame = tb.Frame(win)
        frame.pack(fill=BOTH, expand=True, padx=12, pady=12)

        fig = Figure(figsize=(9.2, 5.2), dpi=100)
        ax = fig.add_subplot(111)

        if mode == "yearly":
            rows = get_yearly_series_by_range(sy, sm, sd, ey, em, ed)
            if not rows:
                tb.Label(frame, text="داده‌ای برای نمایش وجود ندارد", anchor=CENTER).pack(fill=BOTH, expand=True)
                return

            years = [int(r[0]) for r in rows]
            rec = [(r[1] or 0) for r in rows]
            prt = [(r[2] or 0) for r in rows]
            prof = [rec[i] - prt[i] for i in range(len(years))]

            x = list(range(len(years)))
            ax.plot(x, rec, marker="o", label=_rtl("دریافتی"))
            ax.plot(x, prt, marker="o", label=_rtl("قطعات"))
            ax.plot(x, prof, marker="o", label=_rtl("سود"))

            ax.set_title(_rtl("نمودار سالانه"))
            ax.set_xlabel(_rtl("سال"))
            ax.set_ylabel(_rtl("مبلغ"))

            year_labels = [str(y) for y in years]
            _apply_xticks(ax, year_labels, max_labels=12, rotation=90)

        else:
            rows = get_monthly_series_by_range(sy, sm, sd, ey, em, ed)
            if not rows:
                tb.Label(frame, text="داده‌ای برای نمایش وجود ندارد", anchor=CENTER).pack(fill=BOTH, expand=True)
                return

            x_labels, rec, prt, prof = self._build_monthly_continuous_series(sy, sm, ey, em, rows)
            x = list(range(len(x_labels)))

            ax.plot(x, rec, marker="o", label=_rtl("دریافتی"))
            ax.plot(x, prt, marker="o", label=_rtl("قطعات"))
            ax.plot(x, prof, marker="o", label=_rtl("سود"))

            ax.set_title(_rtl("نمودار ماهانه (کل بازه)"))
            ax.set_xlabel(_rtl("ماه/سال"))
            ax.set_ylabel(_rtl("مبلغ"))

            _apply_xticks(ax, x_labels, max_labels=12, rotation=90)

        ax.grid(True)
        ax.legend()

        fig.tight_layout()
        fig.subplots_adjust(bottom=0.30)

        canvas = FigureCanvasTkAgg(fig, master=frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=BOTH, expand=True)

    def _build_monthly_continuous_series(self, sy, sm, ey, em, rows):
        mp = {}
        for y, m, rec, prt in rows:
            mp[_month_key(int(y), int(m))] = (int(rec or 0), int(prt or 0))

        labels, rec_list, prt_list, prof_list = [], [], [], []

        y, m = int(sy), int(sm)
        end_y, end_m = int(ey), int(em)

        while (y < end_y) or (y == end_y and m <= end_m):
            key = _month_key(y, m)
            rec, prt = mp.get(key, (0, 0))
            labels.append(f"{y}/{m:02d}")
            rec_list.append(rec)
            prt_list.append(prt)
            prof_list.append(rec - prt)
            y, m = _next_month(y, m)

        return labels, rec_list, prt_list, prof_list
