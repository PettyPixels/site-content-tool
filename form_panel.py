import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import storage
from config import images_dir_for


class _TextField:
    def __init__(self, parent, row, field):
        ttk.Label(parent, text=field.label).grid(row=row, column=0, sticky="ne", padx=4, pady=4)
        self.var = tk.StringVar()
        ttk.Entry(parent, textvariable=self.var, width=56).grid(row=row, column=1, sticky="we", padx=4, pady=4)

    def get(self):
        return self.var.get().strip()

    def set(self, value):
        self.var.set(value or "")

    def is_empty(self):
        return self.get() == ""


class _MultilineField:
    def __init__(self, parent, row, field):
        ttk.Label(parent, text=field.label).grid(row=row, column=0, sticky="ne", padx=4, pady=4)
        self.text = tk.Text(parent, width=56, height=4, wrap="word")
        self.text.grid(row=row, column=1, sticky="we", padx=4, pady=4)

    def get(self):
        return self.text.get("1.0", "end").strip()

    def set(self, value):
        self.text.delete("1.0", "end")
        self.text.insert("1.0", value or "")

    def is_empty(self):
        return self.get() == ""


class _BoolField:
    def __init__(self, parent, row, field):
        self.var = tk.BooleanVar(value=False)
        ttk.Checkbutton(parent, text=field.label, variable=self.var).grid(
            row=row, column=1, sticky="w", padx=4, pady=4
        )

    def get(self):
        return bool(self.var.get())

    def set(self, value):
        self.var.set(bool(value))

    def is_empty(self):
        return False


class _ListOfStrField:
    def __init__(self, parent, row, field):
        ttk.Label(parent, text=f"{field.label} (comma-separated)").grid(
            row=row, column=0, sticky="ne", padx=4, pady=4
        )
        self.var = tk.StringVar()
        ttk.Entry(parent, textvariable=self.var, width=56).grid(row=row, column=1, sticky="we", padx=4, pady=4)

    def get(self):
        return [part.strip() for part in self.var.get().split(",") if part.strip()]

    def set(self, value):
        self.var.set(", ".join(value or []))

    def is_empty(self):
        return len(self.get()) == 0


class _NestedLinksField:
    def __init__(self, parent, row, field):
        self.sub_fields = field.sub_fields
        self.vars = {}
        group = ttk.LabelFrame(parent, text=field.label)
        group.grid(row=row, column=0, columnspan=2, sticky="we", padx=4, pady=4)
        for i, sub in enumerate(field.sub_fields):
            ttk.Label(group, text=sub).grid(row=i, column=0, sticky="e", padx=4, pady=2)
            var = tk.StringVar()
            ttk.Entry(group, textvariable=var, width=50).grid(row=i, column=1, sticky="we", padx=4, pady=2)
            self.vars[sub] = var

    def get(self):
        return {sub: var.get().strip() for sub, var in self.vars.items()}

    def set(self, value):
        value = value or {}
        for sub, var in self.vars.items():
            var.set(value.get(sub, ""))

    def is_empty(self):
        return all(v == "" for v in self.get().values())


class _ImageField:
    def __init__(self, parent, row, field, content_type_key):
        ttk.Label(parent, text=field.label).grid(row=row, column=0, sticky="ne", padx=4, pady=4)
        wrap = ttk.Frame(parent)
        wrap.grid(row=row, column=1, sticky="we", padx=4, pady=4)
        self.var = tk.StringVar()
        self.images_dir = images_dir_for(content_type_key)
        ttk.Entry(wrap, textvariable=self.var, width=42, state="readonly").pack(side="left")
        ttk.Button(wrap, text="Browse...", command=self._browse).pack(side="left", padx=(6, 0))

    def _browse(self):
        path = filedialog.askopenfilename(
            title="Choose an image",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.gif *.webp *.svg"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            relative_path = storage.copy_image(path, self.images_dir)
        except OSError as e:
            messagebox.showerror("Could not copy image", str(e))
            return
        self.var.set(relative_path)

    def get(self):
        return self.var.get().strip()

    def set(self, value):
        self.var.set(value or "")

    def is_empty(self):
        return self.get() == ""


_WIDGET_TYPES = {
    "text": _TextField,
    "url": _TextField,
    "multiline": _MultilineField,
    "bool": _BoolField,
    "list_of_str": _ListOfStrField,
    "nested_links": _NestedLinksField,
    "image": _ImageField,
}


class EntryFormPanel(ttk.Frame):
    def __init__(self, parent, content_type, on_save):
        super().__init__(parent)
        self.content_type = content_type
        self._on_save = on_save
        self._widgets = {}

        fields_frame = ttk.Frame(self)
        fields_frame.pack(side="top", fill="both", expand=True)
        fields_frame.columnconfigure(1, weight=1)

        for row, entry_field in enumerate(content_type.fields):
            widget_cls = _WIDGET_TYPES[entry_field.type]
            if entry_field.type == "image":
                self._widgets[entry_field.name] = widget_cls(fields_frame, row, entry_field, content_type.key)
            else:
                self._widgets[entry_field.name] = widget_cls(fields_frame, row, entry_field)

        button_row = ttk.Frame(self)
        button_row.pack(side="top", fill="x", pady=(10, 0))
        ttk.Button(button_row, text="Save", command=self._handle_save).pack(side="left")

    def clear(self):
        for entry_field in self.content_type.fields:
            self._widgets[entry_field.name].set(None)

    def load_entry(self, entry):
        for entry_field in self.content_type.fields:
            self._widgets[entry_field.name].set(entry.get(entry_field.name))

    def _handle_save(self):
        missing = [
            entry_field.label
            for entry_field in self.content_type.fields
            if entry_field.required and self._widgets[entry_field.name].is_empty()
        ]
        if missing:
            messagebox.showerror("Missing fields", "Please fill in: " + ", ".join(missing))
            return

        entry = {}
        if self.content_type.supports_placeholder:
            entry["placeholder"] = False
        for entry_field in self.content_type.fields:
            entry[entry_field.name] = self._widgets[entry_field.name].get()
        self._on_save(entry)
