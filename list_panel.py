from tkinter import ttk


class EntryListPanel(ttk.Frame):
    def __init__(self, parent, on_select, on_new, on_delete, on_move_up, on_move_down):
        super().__init__(parent)
        self._on_select = on_select
        self._on_new = on_new
        self._on_delete = on_delete
        self._on_move_up = on_move_up
        self._on_move_down = on_move_down

        self.tree = ttk.Treeview(
            self, columns=("status",), show="tree headings", selectmode="browse", height=18
        )
        self.tree.heading("#0", text="Title")
        self.tree.heading("status", text="")
        self.tree.column("#0", width=200)
        self.tree.column("status", width=130, anchor="center")
        self.tree.pack(side="top", fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._handle_select)

        button_row = ttk.Frame(self)
        button_row.pack(side="top", fill="x", pady=(6, 0))
        ttk.Button(button_row, text="New", command=self._on_new).pack(side="left")
        ttk.Button(button_row, text="Delete", command=self._handle_delete).pack(side="left", padx=(6, 0))

        move_row = ttk.Frame(self)
        move_row.pack(side="top", fill="x", pady=(4, 0))
        ttk.Button(move_row, text="Move Up", command=self._handle_move_up).pack(side="left")
        ttk.Button(move_row, text="Move Down", command=self._handle_move_down).pack(side="left", padx=(6, 0))

    def refresh(self, entries):
        self.tree.delete(*self.tree.get_children())
        for index, entry in enumerate(entries):
            title = entry.get("title", "(untitled)")
            statuses = []
            if entry.get("placeholder"):
                statuses.append("placeholder")
            if entry.get("hidden"):
                statuses.append("hidden")
            status = ", ".join(statuses)
            self.tree.insert("", "end", iid=str(index), text=title, values=(status,))

    def clear_selection(self):
        self.tree.selection_remove(self.tree.selection())

    def _handle_select(self, _event):
        selection = self.tree.selection()
        if not selection:
            return
        self._on_select(int(selection[0]))

    def _handle_delete(self):
        selection = self.tree.selection()
        if not selection:
            return
        self._on_delete(int(selection[0]))

    def _handle_move_up(self):
        selection = self.tree.selection()
        if not selection:
            return
        self._on_move_up(int(selection[0]))

    def _handle_move_down(self):
        selection = self.tree.selection()
        if not selection:
            return
        self._on_move_down(int(selection[0]))
