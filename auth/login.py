import ttkbootstrap as tb
from ttkbootstrap.constants import *

from database.db import verify_user
from gui.main_window import MainWindow


class LoginWindow(tb.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.pack(fill=BOTH, expand=True)
        self._build_ui()

    def _build_ui(self):
        container = tb.Frame(self)
        container.place(relx=0.5, rely=0.5, anchor=CENTER)

        tb.Label(
            container,
            text="ورود به سیستم",
            font=("Helvetica", 16, "bold")
        ).pack(pady=10)

        self.username = tb.StringVar()
        self.password = tb.StringVar()

        u = tb.Entry(container, textvariable=self.username, justify=RIGHT)
        p = tb.Entry(container, textvariable=self.password, show="*", justify=RIGHT)

        u.pack(fill=X, pady=5)
        p.pack(fill=X, pady=5)

        btn = tb.Button(
            container,
            text="ورود",
            bootstyle=PRIMARY,
            command=self._login
        )
        btn.pack(fill=X, pady=10)

        self.error_label = tb.Label(container, text="", bootstyle=DANGER)
        self.error_label.pack()

        # enter key login
        self.master.bind("<Return>", lambda e: self._login())

        u.focus_set()

    def _login(self):
        username = self.username.get().strip()
        if verify_user(username, self.password.get()):
            self.master.unbind("<Return>")
            self.pack_forget()
            MainWindow(self.master, username)
        else:
            self.error_label.config(text="نام کاربری یا رمز عبور اشتباه است")
            self.password.set("")
