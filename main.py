import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

import settings


def ensure_portfolio_site() -> bool:
    site = settings.get_portfolio_site()
    if site is not None and site.is_dir():
        return True

    root = tk.Tk()
    root.withdraw()
    messagebox.showinfo(
        "Setup",
        "Select your portfolio-site folder (the one containing data/ and media/).",
    )
    chosen = filedialog.askdirectory(title="Portfolio site folder", mustexist=True)
    root.destroy()

    if not chosen:
        return False
    settings.set_portfolio_site(Path(chosen))
    return True


def main():
    if not ensure_portfolio_site():
        return
    from app import App

    root = tk.Tk()
    root.title("Site Content Tool")
    root.geometry("900x600")
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
