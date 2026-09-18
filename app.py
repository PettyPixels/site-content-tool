from tkinter import ttk, messagebox

import schema
import storage
from storage import JSONParseError
from form_panel import EntryFormPanel
from list_panel import EntryListPanel
from blog_tab import BlogTab


class TypeTab(ttk.Frame):
    def __init__(self, parent, content_type):
        super().__init__(parent)
        self.content_type = content_type
        self.entries = []
        self.selected_index = None
        self.load_failed = False

        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        self.list_panel = EntryListPanel(
            self,
            on_select=self._select_entry,
            on_new=self._new_entry,
            on_delete=self._delete_entry,
            on_move_up=lambda index: self._move_entry(index, -1),
            on_move_down=lambda index: self._move_entry(index, 1),
        )
        self.list_panel.grid(row=0, column=0, sticky="ns", padx=(8, 4), pady=8)

        self.form_panel = EntryFormPanel(self, content_type, on_save=self._save_entry)
        self.form_panel.grid(row=0, column=1, sticky="nsew", padx=(4, 8), pady=8)

        self.reload()

    def reload(self):
        try:
            self.entries = storage.load_entries(self.content_type.json_file)
            self.load_failed = False
        except JSONParseError as e:
            messagebox.showerror(
                "Invalid JSON",
                f"{e}\n\nFix it by hand before using this tab — nothing will be saved "
                "here until it parses correctly.",
            )
            self.entries = []
            self.load_failed = True
        self.list_panel.refresh(self.entries)
        self.selected_index = None
        self.form_panel.clear()

    def _select_entry(self, index):
        self.selected_index = index
        self.form_panel.load_entry(self.entries[index])

    def _new_entry(self):
        self.selected_index = None
        self.list_panel.clear_selection()
        self.form_panel.clear()

    def _delete_entry(self, index):
        if self.load_failed:
            messagebox.showerror(
                "Cannot save", f"{self.content_type.json_file} has invalid JSON — fix it by hand first."
            )
            return
        title = self.entries[index].get("title", "(untitled)")
        if not messagebox.askyesno("Delete entry", f'Delete "{title}"? This cannot be undone.'):
            return
        del self.entries[index]
        storage.save_entries(self.content_type.json_file, self.entries)
        self.reload()

    def _move_entry(self, index, delta):
        if self.load_failed:
            messagebox.showerror(
                "Cannot save", f"{self.content_type.json_file} has invalid JSON — fix it by hand first."
            )
            return
        new_index = index + delta
        if new_index < 0 or new_index >= len(self.entries):
            return
        self.entries[index], self.entries[new_index] = self.entries[new_index], self.entries[index]
        storage.save_entries(self.content_type.json_file, self.entries)
        self.reload()
        self.list_panel.tree.selection_set(str(new_index))
        self._select_entry(new_index)

    def _save_entry(self, entry):
        if self.load_failed:
            messagebox.showerror(
                "Cannot save", f"{self.content_type.json_file} has invalid JSON — fix it by hand first."
            )
            return
        if self.selected_index is None:
            # New entries go to the top of the list, so newest content leads on the site
            # (matches the existing hand-curated newest-to-oldest ordering).
            self.entries.insert(0, entry)
        else:
            self.entries[self.selected_index] = entry
        storage.save_entries(self.content_type.json_file, self.entries)
        self.reload()


class App(ttk.Frame):
    def __init__(self, root):
        super().__init__(root)
        self.pack(fill="both", expand=True)
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)
        for content_type in schema.CONTENT_TYPES.values():
            tab = TypeTab(notebook, content_type)
            notebook.add(tab, text=content_type.label)
        notebook.add(BlogTab(notebook), text="Blog")
