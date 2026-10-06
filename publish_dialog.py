import threading
import tkinter as tk
import webbrowser
from tkinter import ttk, messagebox

import publish
import settings


def run_in_background(widget, work, on_done):
    """Run work() off the UI thread, then call on_done(result, error) back on it.

    git fetch/push can take seconds (or wait on a login window), so running them
    on the tkinter thread would freeze the app.
    """
    outcome = {}

    def target():
        try:
            outcome["result"] = work()
        except Exception as e:
            outcome["error"] = e

    thread = threading.Thread(target=target, daemon=True)
    thread.start()

    def poll():
        if thread.is_alive():
            widget.after(100, poll)
        else:
            on_done(outcome.get("result"), outcome.get("error"))

    widget.after(100, poll)


def live_site_url(site_root):
    """The site's public URL, taken from its GitHub Pages CNAME file if it has one."""
    try:
        domain = (site_root / "CNAME").read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return f"https://{domain}" if domain else None


class PublishDialog(tk.Toplevel):
    def __init__(self, parent, site_root, unsaved_edits):
        super().__init__(parent)
        self.site_root = site_root
        self.unsaved_edits = unsaved_edits
        self.plan = None

        self.title("Publish to live site")
        self.transient(parent.winfo_toplevel())
        self.minsize(520, 0)
        self.body = ttk.Frame(self, padding=12)
        self.body.pack(fill="both", expand=True)
        self.status = ttk.Label(self.body, text="Checking the site repo and GitHub…")
        self.status.pack(anchor="w")
        self.grab_set()

        run_in_background(self, self._prepare, self._on_prepared)

    def _prepare(self):
        saved = settings.get_git_remote()
        remote = publish.resolve_remote(self.site_root, saved)
        if saved is None:
            settings.set_git_remote(remote)
        return publish.prepare(self.site_root, remote)

    def _on_prepared(self, plan, error):
        if isinstance(error, publish.NothingToPublish):
            messagebox.showinfo("Publish", str(error), parent=self.master)
            self.destroy()
            return
        if error is not None:
            messagebox.showerror("Can't publish", str(error), parent=self.master)
            self.destroy()
            return
        self.plan = plan
        self.status.destroy()
        self._build_review(plan)

    def _build_review(self, plan):
        body = self.body
        if plan.changes:
            ttk.Label(
                body,
                text=f"These files will be committed to {publish.BRANCH} and pushed to {plan.remote}:",
            ).pack(anchor="w")
            files = tk.Listbox(
                body, height=min(len(plan.changes), 12), activestyle="none", font="TkFixedFont"
            )
            for change in plan.changes:
                files.insert("end", f"{change.kind.capitalize():<10}{change.path}")
            files.pack(fill="both", expand=True, pady=(4, 10))

        if plan.unpushed:
            count = len(plan.unpushed)
            ttk.Label(
                body,
                text=f"{'Also pushing' if plan.changes else 'Pushing'} {count} earlier local "
                f"commit{'s' if count > 1 else ''}:",
            ).pack(anchor="w")
            commits = tk.Listbox(body, height=min(count, 6), activestyle="none")
            for line in plan.unpushed:
                commits.insert("end", line)
            commits.pack(fill="both", expand=True, pady=(4, 10))

        if self.unsaved_edits:
            ttk.Label(
                body,
                text="The open form has unsaved edits. They won't be published until you save them.",
                foreground="#b45309",
            ).pack(anchor="w", pady=(0, 10))

        self.message_var = tk.StringVar(value=plan.message)
        if plan.changes:
            ttk.Label(body, text="Commit message").pack(anchor="w")
            entry = ttk.Entry(body, textvariable=self.message_var, width=70)
            entry.pack(fill="x", pady=(4, 10))
            entry.focus_set()

        buttons = ttk.Frame(body)
        buttons.pack(fill="x")
        self.cancel_button = ttk.Button(buttons, text="Cancel", command=self.destroy)
        self.cancel_button.pack(side="right")
        self.publish_button = ttk.Button(buttons, text="Publish", command=self._publish)
        self.publish_button.pack(side="right", padx=(0, 6))
        self.progress = ttk.Label(buttons, text="")
        self.progress.pack(side="left")

    def _publish(self):
        message = self.message_var.get()
        if self.plan.changes and not message.strip():
            messagebox.showerror("Publish", "The commit message can't be empty.", parent=self)
            return
        self.publish_button.configure(state="disabled")
        self.cancel_button.configure(state="disabled")
        self.protocol("WM_DELETE_WINDOW", lambda: None)  # don't close mid-push
        self.progress.configure(text="Pushing…")
        run_in_background(
            self, lambda: publish.publish(self.site_root, self.plan, message), self._on_published
        )

    def _on_published(self, commit, error):
        parent = self.master
        self.destroy()
        if error is not None:
            messagebox.showerror("Publish failed", str(error), parent=parent)
            return
        text = (
            f"Pushed {commit} to {publish.BRANCH}. GitHub Pages usually updates within "
            "a minute or two."
        )
        url = live_site_url(self.site_root)
        if url is None:
            messagebox.showinfo("Published", text, parent=parent)
        elif messagebox.askyesno("Published", f"{text}\n\nOpen {url}?", parent=parent):
            webbrowser.open(url)
