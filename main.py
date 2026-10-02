import tkinter as tk

import ttkbootstrap as tb
from database.db import create_tables
from auth.login import LoginWindow


def main():
    create_tables()

    root = tb.Window(themename="darkly")
    root.title("سیستم مدیریت تعمیرگاه")

    # maximized window
    try:
        root.state("zoomed")  # Windows / macOS
    except tk.TclError:
        root.attributes("-zoomed", True)  # Linux

    root.minsize(1200, 750)

    LoginWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()
