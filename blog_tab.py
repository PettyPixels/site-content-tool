import tkinter as tk
from datetime import date
from tkinter import ttk, messagebox

import blog_logic
import storage
from config import BLOG_DIR, POSTS_JSON
from list_panel import EntryListPanel


class BlogFormPanel(ttk.Frame):
    def __init__(self, parent, on_save):
        super().__init__(parent)
        self._on_save = on_save
        self.mode = "new"

        fields = ttk.Frame(self)
        fields.pack(side="top", fill="both", expand=True)
        fields.columnconfigure(1, weight=1)

        ttk.Label(fields, text="Title").grid(row=0, column=0, sticky="ne", padx=4, pady=4)
        self.title_var = tk.StringVar()
        ttk.Entry(fields, textvariable=self.title_var, width=56).grid(row=0, column=1, sticky="we", padx=4, pady=4)

        ttk.Label(fields, text="Tag").grid(row=1, column=0, sticky="ne", padx=4, pady=4)
        self.tag_var = tk.StringVar()
        ttk.Entry(fields, textvariable=self.tag_var, width=56).grid(row=1, column=1, sticky="we", padx=4, pady=4)

        ttk.Label(fields, text="Slug").grid(row=2, column=0, sticky="ne", padx=4, pady=4)
        self.slug_var = tk.StringVar()
        ttk.Entry(fields, textvariable=self.slug_var, width=56, state="readonly").grid(
            row=2, column=1, sticky="we", padx=4, pady=4
        )

        ttk.Label(fields, text="Date").grid(row=3, column=0, sticky="ne", padx=4, pady=4)
        self.date_var = tk.StringVar()
        ttk.Entry(fields, textvariable=self.date_var, width=56, state="readonly").grid(
            row=3, column=1, sticky="we", padx=4, pady=4
        )

        ttk.Label(fields, text="Body").grid(row=4, column=0, sticky="ne", padx=4, pady=4)
        self.body_text = tk.Text(fields, width=56, height=16, wrap="word")
        self.body_text.grid(row=4, column=1, sticky="we", padx=4, pady=4)

        ttk.Label(fields, text="Excerpt").grid(row=5, column=0, sticky="ne", padx=4, pady=4)
        excerpt_wrap = ttk.Frame(fields)
        excerpt_wrap.grid(row=5, column=1, sticky="we", padx=4, pady=4)
        self.excerpt_var = tk.StringVar()
        ttk.Entry(excerpt_wrap, textvariable=self.excerpt_var, width=44).pack(side="left")
        ttk.Button(excerpt_wrap, text="Auto-fill from body", command=self._autofill_excerpt).pack(
            side="left", padx=(6, 0)
        )

        self.hidden_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(fields, text="Hidden", variable=self.hidden_var).grid(
            row=6, column=1, sticky="w", padx=4, pady=4
        )

        button_row = ttk.Frame(self)
        button_row.pack(side="top", fill="x", pady=(10, 0))
        ttk.Button(button_row, text="Save", command=self._handle_save).pack(side="left")

    def _autofill_excerpt(self):
        body = self.body_text.get("1.0", "end").strip()
        self.excerpt_var.set(blog_logic.strip_tags_and_excerpt(body))

    def clear(self):
        self.mode = "new"
        self.title_var.set("")
        self.tag_var.set("Devlog")
        self.slug_var.set("(generated from title on save)")
        self.date_var.set("(set to today on save)")
        self.body_text.delete("1.0", "end")
        self.excerpt_var.set("")
        self.hidden_var.set(False)

    def load_post(self, post, body_text):
        self.mode = "edit"
        self.title_var.set(post["title"])
        self.tag_var.set(post["tag"])
        self.slug_var.set(post["slug"])
        self.date_var.set(post["date"])
        self.body_text.delete("1.0", "end")
        self.body_text.insert("1.0", body_text)
        self.excerpt_var.set(post["excerpt"])
        self.hidden_var.set(bool(post.get("hidden")))

    def _handle_save(self):
        title = self.title_var.get().strip()
        tag = self.tag_var.get().strip() or "Devlog"
        body = self.body_text.get("1.0", "end").strip()

        missing = []
        if not title:
            missing.append("Title")
        if not body:
            missing.append("Body")
        if missing:
            messagebox.showerror("Missing fields", "Please fill in: " + ", ".join(missing))
            return

        excerpt = self.excerpt_var.get().strip() or blog_logic.strip_tags_and_excerpt(body)
        self._on_save({
            "mode": self.mode,
            "title": title,
            "tag": tag,
            "body": body,
            "excerpt": excerpt,
            "hidden": self.hidden_var.get(),
        })


class BlogTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.posts = []
        self.selected_index = None
        self.load_failed = False

        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        self.list_panel = EntryListPanel(
            self,
            on_select=self._select_post,
            on_new=self._new_post,
            on_delete=self._delete_post,
            on_move_up=lambda index: self._move_post(index, -1),
            on_move_down=lambda index: self._move_post(index, 1),
        )
        self.list_panel.grid(row=0, column=0, sticky="ns", padx=(8, 4), pady=8)

        self.form_panel = BlogFormPanel(self, on_save=self._save_post)
        self.form_panel.grid(row=0, column=1, sticky="nsew", padx=(4, 8), pady=8)

        self.reload()

    def reload(self):
        try:
            self.posts = storage.load_entries(POSTS_JSON)
            self.load_failed = False
        except storage.JSONParseError as e:
            messagebox.showerror(
                "Invalid JSON",
                f"{e}\n\nFix it by hand before using this tab — nothing will be saved "
                "here until it parses correctly.",
            )
            self.posts = []
            self.load_failed = True
        self.list_panel.refresh(self.posts)
        self.selected_index = None
        self.form_panel.clear()

    def _select_post(self, index):
        self.selected_index = index
        post = self.posts[index]
        post_path = BLOG_DIR / post["slug"]
        if post_path.exists():
            body = blog_logic.extract_body(post_path.read_text(encoding="utf-8"))
        else:
            body = ""
            messagebox.showwarning("Missing file", f"{post_path} not found on disk — body left empty.")
        self.form_panel.load_post(post, body)

    def _new_post(self):
        self.selected_index = None
        self.list_panel.clear_selection()
        self.form_panel.clear()

    def _delete_post(self, index):
        if self.load_failed:
            messagebox.showerror("Cannot save", f"{POSTS_JSON} has invalid JSON — fix it by hand first.")
            return
        post = self.posts[index]
        if not messagebox.askyesno(
            "Delete post", f'Delete "{post["title"]}" ({post["date"]})? This cannot be undone.'
        ):
            return
        post_path = BLOG_DIR / post["slug"]
        if post_path.exists():
            post_path.unlink()
        del self.posts[index]
        storage.save_entries(POSTS_JSON, self.posts)
        self.reload()

    def _move_post(self, index, delta):
        if self.load_failed:
            messagebox.showerror("Cannot save", f"{POSTS_JSON} has invalid JSON — fix it by hand first.")
            return
        new_index = index + delta
        if new_index < 0 or new_index >= len(self.posts):
            return
        self.posts[index], self.posts[new_index] = self.posts[new_index], self.posts[index]
        storage.save_entries(POSTS_JSON, self.posts)
        self.reload()
        self.list_panel.tree.selection_set(str(new_index))
        self._select_post(new_index)

    def _save_post(self, data):
        if self.load_failed:
            messagebox.showerror("Cannot save", f"{POSTS_JSON} has invalid JSON — fix it by hand first.")
            return

        if data["mode"] == "new":
            existing_slugs = {p["slug"] for p in self.posts}
            slug = blog_logic.unique_slug(blog_logic.slugify(data["title"]), existing_slugs)
            post_date = date.today().isoformat()
        else:
            post = self.posts[self.selected_index]
            slug = post["slug"].removesuffix(".html")
            post_date = post["date"]

        html = blog_logic.render_post_html(data["title"], data["tag"], post_date, data["body"])
        BLOG_DIR.mkdir(exist_ok=True)
        (BLOG_DIR / f"{slug}.html").write_text(html, encoding="utf-8")

        metadata = {
            "title": data["title"],
            "slug": f"{slug}.html",
            "date": post_date,
            "tag": data["tag"],
            "excerpt": data["excerpt"],
            "hidden": data["hidden"],
        }

        if data["mode"] == "new":
            self.posts.insert(0, metadata)
        else:
            self.posts[self.selected_index] = metadata

        storage.save_entries(POSTS_JSON, self.posts)
        self.reload()
