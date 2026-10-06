"""Commit and push the tool's content changes to the live branch.

Uses the git CLI in the site folder, so authentication is whatever git is already set
up with (e.g. Git Credential Manager). The tool never handles tokens itself.
"""
import subprocess
import sys
from dataclasses import dataclass
from pathlib import PurePosixPath

BRANCH = "main"
# Only the folders this tool writes to are ever staged, so unrelated work in the site
# repo (template edits, stray files) can't be swept into a publish by accident.
MANAGED_PATHS = ("data", "media/images", "blog")
_MAX_SUBJECT = 72


class PublishError(Exception):
    pass


class NothingToPublish(PublishError):
    pass


@dataclass
class Change:
    status: str  # two-letter `git status --porcelain` code, e.g. "??", " M", "D "
    path: str
    orig_path: str | None = None  # set for renames/copies

    @property
    def kind(self):
        if self.status == "??" or "A" in self.status:
            return "added"
        if "D" in self.status:
            return "deleted"
        return "modified"


@dataclass
class PublishPlan:
    remote: str
    changes: list[Change]
    unpushed: list[str]  # "<hash> <subject>" for local commits not yet on the remote
    message: str  # suggested commit message


def _git(repo, *args, input=None):
    kwargs = {}
    if sys.platform == "win32":
        # Stop a console window flashing up for each git call in the windowed build.
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=repo,
            input=input,
            # No stdin: if git falls back to a terminal credential prompt, it fails
            # instead of hanging. Credential Manager's own login window still works.
            stdin=subprocess.DEVNULL if input is None else None,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            **kwargs,
        )
    except FileNotFoundError:
        raise PublishError(
            "Git isn't installed, or isn't on PATH. Install it from https://git-scm.com "
            "and restart the tool."
        ) from None
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise PublishError(f"git {args[0]} failed:\n\n{detail}")
    return result.stdout


def list_remotes(repo):
    return _git(repo, "remote").split()


def resolve_remote(repo, preferred=None):
    """Return the remote to push to: the saved one, else the only one, else origin."""
    remotes = list_remotes(repo)
    if preferred:
        if preferred in remotes:
            return preferred
        raise PublishError(
            f'The saved git remote "{preferred}" doesn\'t exist in the site repo '
            f"(remotes: {', '.join(remotes) or 'none'}). Fix git_remote in "
            "~/.site-content-tool/settings.json."
        )
    if len(remotes) == 1:
        return remotes[0]
    if "origin" in remotes:
        return "origin"
    if not remotes:
        raise PublishError("The site repo has no git remote to push to.")
    raise PublishError(
        f"The site repo has several remotes ({', '.join(remotes)}). Set git_remote in "
        "~/.site-content-tool/settings.json to the one GitHub Pages deploys from."
    )


def changed_files(repo):
    out = _git(
        repo, "status", "--porcelain=v1", "-z", "--untracked-files=all", "--", *MANAGED_PATHS
    )
    tokens = out.split("\0")
    changes = []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        i += 1
        if not token:
            continue
        status, path = token[:2], token[3:]
        orig = None
        if "R" in status or "C" in status:
            # In -z output the source path follows as its own token.
            orig = tokens[i]
            i += 1
        changes.append(Change(status, path, orig))
    return changes


def default_message(changes):
    verbs = {"added": "Add", "modified": "Update", "deleted": "Remove"}
    posts = {kind: [] for kind in verbs}
    images = {kind: 0 for kind in verbs}
    data_files = []
    other = 0
    for change in changes:
        path = PurePosixPath(change.path)
        if path.parts[0] == "blog" and path.suffix == ".html":
            posts[change.kind].append(path.stem)
        elif path.parts[0] == "data":
            data_files.append(path.name)
        elif change.path.startswith("media/images/"):
            images[change.kind] += 1
        else:
            other += 1

    parts = []
    for kind, verb in verbs.items():
        if posts[kind]:
            parts.append(f"{verb} blog post: {', '.join(posts[kind])}")
    # posts.json always changes alongside a post, so naming it too would be noise.
    if any(posts.values()):
        data_files = [name for name in data_files if name != "posts.json"]
    if data_files:
        parts.append(f"update {', '.join(sorted(data_files))}")
    for kind, verb in verbs.items():
        if images[kind]:
            parts.append(f"{verb.lower()} {images[kind]} image{'s' if images[kind] > 1 else ''}")
    if other:
        parts.append(f"update {other} other file{'s' if other > 1 else ''}")

    message = "; ".join(parts)
    message = message[:1].upper() + message[1:]
    if not message or len(message) > _MAX_SUBJECT:
        return f"Update site content ({len(changes)} files)"
    return message


def prepare(repo, remote):
    """Sync with the remote and work out what would be published.

    Fast-forwards local main if the remote is ahead. Refuses if main isn't checked
    out or the histories have diverged, since resolving that needs a human.
    """
    try:
        _git(repo, "rev-parse", "--git-dir")
    except PublishError:
        raise PublishError(f"{repo} isn't a git repository.") from None

    branch = _git(repo, "branch", "--show-current").strip()
    if branch != BRANCH:
        raise PublishError(
            f'The site repo is on branch "{branch or "(detached HEAD)"}". Check out '
            f"{BRANCH} before publishing."
        )

    _git(repo, "fetch", remote, BRANCH)
    tracking = f"{remote}/{BRANCH}"
    ahead, behind = (
        int(n) for n in _git(repo, "rev-list", "--left-right", "--count", f"HEAD...{tracking}").split()
    )
    if ahead and behind:
        raise PublishError(
            f"Local {BRANCH} and {tracking} have diverged ({ahead} local and {behind} remote "
            "commits that the other doesn't have). Resolve this with git before publishing."
        )
    if behind:
        _git(repo, "merge", "--ff-only", tracking)

    changes = changed_files(repo)
    unpushed = _git(repo, "log", "--format=%h %s", f"{tracking}..HEAD").splitlines()
    if not changes and not unpushed:
        raise NothingToPublish("Nothing to publish: the live site is already up to date.")
    return PublishPlan(remote, changes, unpushed, default_message(changes))


def publish(repo, plan, message):
    """Commit the plan's changes (if any) and push main. Returns the new HEAD hash."""
    if plan.changes:
        message = message.strip()
        if not message:
            raise PublishError("The commit message can't be empty.")
        paths = []
        for change in plan.changes:
            paths.append(change.path)
            if change.orig_path:
                paths.append(change.orig_path)
        pathspec = "\0".join(paths)
        _git(repo, "add", "-A", "--pathspec-from-file=-", "--pathspec-file-nul", input=pathspec)
        # Committing by pathspec leaves anything else the user had staged out of it.
        _git(
            repo, "commit", "-m", message, "--pathspec-from-file=-", "--pathspec-file-nul",
            input=pathspec,
        )
    _git(repo, "push", plan.remote, f"HEAD:{BRANCH}")
    return _git(repo, "rev-parse", "--short", "HEAD").strip()
