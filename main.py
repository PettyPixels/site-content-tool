import tkinter as tk

from app import App


def main():
    root = tk.Tk()
    root.title("Site Content Tool")
    root.geometry("900x600")
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
