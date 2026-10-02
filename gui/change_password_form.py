import ttkbootstrap as tb
from ttkbootstrap.constants import *
from tkinter import messagebox

from database.db import verify_user, change_password

MIN_PASSWORD_LENGTH = 4


class ChangePasswordForm(tb.Toplevel):
    def __init__(self, master, username):
        super().__init__(master)
        self.username = username
        self.title("تغییر رمز عبور")
        self.geometry("350x300")

        self.current_var = tb.StringVar()
        self.new_var = tb.StringVar()
        self.confirm_var = tb.StringVar()

        for label, var in (
            ("رمز فعلی", self.current_var),
            ("رمز جدید", self.new_var),
            ("تکرار رمز جدید", self.confirm_var),
        ):
            tb.Label(self, text=label).pack(anchor=E, padx=10, pady=(10, 2))
            tb.Entry(self, textvariable=var, show="*", justify="right").pack(fill=X, padx=10)

        tb.Button(self, text="ذخیره", bootstyle=SUCCESS, command=self.save).pack(pady=15)

    def save(self):
        if not verify_user(self.username, self.current_var.get()):
            messagebox.showerror("خطا", "رمز فعلی اشتباه است", parent=self)
            return

        new_password = self.new_var.get()
        if len(new_password) < MIN_PASSWORD_LENGTH:
            messagebox.showerror("خطا", f"رمز جدید باید حداقل {MIN_PASSWORD_LENGTH} کاراکتر باشد", parent=self)
            return

        if new_password != self.confirm_var.get():
            messagebox.showerror("خطا", "رمز جدید و تکرار آن یکسان نیستند", parent=self)
            return

        change_password(self.username, new_password)
        messagebox.showinfo("موفق", "رمز عبور تغییر کرد", parent=self)
        self.destroy()
