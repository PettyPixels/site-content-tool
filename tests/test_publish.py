import subprocess

import pytest

import publish
from publish import Change, NothingToPublish, PublishError


def git(cwd, *args):
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout


@pytest.fixture(autouse=True)
def isolated_git(tmp_path, monkeypatch):
    """Keep the developer's own git config (signing, hooks, default branch) out of tests."""
    empty = tmp_path / "gitconfig"
    empty.write_text("", encoding="utf-8")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(empty))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    for role in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{role}_NAME", "Test")
        monkeypatch.setenv(f"GIT_{role}_EMAIL", "test@example.com")


@pytest.fixture
def repos(tmp_path):
    """A bare 'GitHub' remote, the site clone the tool publishes from, and a second clone
    standing in for changes pushed from somewhere else."""
    remote = tmp_path / "remote.git"
    git(tmp_path, "init", "--bare", "-b", "main", str(remote))

    site = tmp_path / "site"
    git(tmp_path, "clone", str(remote), str(site))
    git(site, "symbolic-ref", "HEAD", "refs/heads/main")
    (site / "data").mkdir()
    (site / "data" / "art.json").write_text("[]", encoding="utf-8")
    (site / "blog").mkdir()
    (site / "blog" / "old-post.html").write_text("<p>old</p>", encoding="utf-8")
    (site / "index.html").write_text("<html></html>", encoding="utf-8")
    git(site, "add", "-A")
    git(site, "commit", "-m", "Initial")
    git(site, "push", "origin", "main")

    other = tmp_path / "other"
    git(tmp_path, "clone", str(remote), str(other))
    return site, remote, other


def remote_files(remote):
    return set(git(remote, "ls-tree", "-r", "--name-only", "main").split())


class TestPrepareAndPublish:
    def test_stages_only_managed_paths(self, repos):
        site, remote, _ = repos
        (site / "data" / "art.json").write_text('[{"title": "New"}]', encoding="utf-8")
        (site / "blog" / "new-post.html").write_text("<p>hi</p>", encoding="utf-8")
        (site / "media" / "images" / "art").mkdir(parents=True)
        (site / "media" / "images" / "art" / "a.png").write_bytes(b"\x89PNG")
        (site / "index.html").write_text("<html>edited</html>", encoding="utf-8")
        (site / "notes.txt").write_text("scratch", encoding="utf-8")

        plan = publish.prepare(site, "origin")
        assert {c.path for c in plan.changes} == {
            "data/art.json",
            "blog/new-post.html",
            "media/images/art/a.png",
        }

        publish.publish(site, plan, plan.message)
        files = remote_files(remote)
        assert {"blog/new-post.html", "media/images/art/a.png"} <= files
        assert "notes.txt" not in files
        assert git(remote, "show", "main:index.html") == "<html></html>"
        # The unmanaged edit is left exactly as it was.
        assert "index.html" in git(site, "status", "--porcelain")

    def test_publishes_deletions(self, repos):
        site, remote, _ = repos
        (site / "blog" / "old-post.html").unlink()
        plan = publish.prepare(site, "origin")
        assert [(c.kind, c.path) for c in plan.changes] == [("deleted", "blog/old-post.html")]
        publish.publish(site, plan, plan.message)
        assert "blog/old-post.html" not in remote_files(remote)

    def test_leaves_unrelated_staged_files_out_of_the_commit(self, repos):
        site, remote, _ = repos
        (site / "index.html").write_text("<html>staged</html>", encoding="utf-8")
        git(site, "add", "index.html")
        (site / "data" / "art.json").write_text('[{"title": "New"}]', encoding="utf-8")

        plan = publish.prepare(site, "origin")
        publish.publish(site, plan, "Update art.json")
        assert git(remote, "show", "main:index.html") == "<html></html>"
        assert git(site, "diff", "--cached", "--name-only").split() == ["index.html"]

    def test_uses_the_edited_message(self, repos):
        site, remote, _ = repos
        (site / "data" / "art.json").write_text('[{"title": "New"}]', encoding="utf-8")
        plan = publish.prepare(site, "origin")
        publish.publish(site, plan, "My own message")
        assert git(remote, "log", "-1", "--format=%s", "main").strip() == "My own message"

    def test_rejects_empty_message(self, repos):
        site, _, _ = repos
        (site / "data" / "art.json").write_text('[{"title": "New"}]', encoding="utf-8")
        plan = publish.prepare(site, "origin")
        with pytest.raises(PublishError, match="empty"):
            publish.publish(site, plan, "   ")

    def test_nothing_to_publish_when_only_unmanaged_files_changed(self, repos):
        site, _, _ = repos
        (site / "index.html").write_text("<html>edited</html>", encoding="utf-8")
        with pytest.raises(NothingToPublish):
            publish.prepare(site, "origin")

    def test_refuses_when_not_on_main(self, repos):
        site, _, _ = repos
        git(site, "checkout", "-b", "dev")
        (site / "data" / "art.json").write_text('[{"title": "New"}]', encoding="utf-8")
        with pytest.raises(PublishError, match='branch "dev"'):
            publish.prepare(site, "origin")

    def test_fast_forwards_when_remote_is_ahead(self, repos):
        site, remote, other = repos
        (other / "data" / "music.json").write_text("[]", encoding="utf-8")
        git(other, "add", "-A")
        git(other, "commit", "-m", "From elsewhere")
        git(other, "push", "origin", "main")

        (site / "data" / "art.json").write_text('[{"title": "New"}]', encoding="utf-8")
        plan = publish.prepare(site, "origin")
        assert (site / "data" / "music.json").exists()
        publish.publish(site, plan, plan.message)
        assert {"data/music.json", "data/art.json"} <= remote_files(remote)

    def test_refuses_when_histories_have_diverged(self, repos):
        site, _, other = repos
        (other / "data" / "music.json").write_text("[]", encoding="utf-8")
        git(other, "add", "-A")
        git(other, "commit", "-m", "From elsewhere")
        git(other, "push", "origin", "main")

        (site / "index.html").write_text("<html>local</html>", encoding="utf-8")
        git(site, "commit", "-am", "Local only")
        with pytest.raises(PublishError, match="diverged"):
            publish.prepare(site, "origin")

    def test_pushes_earlier_unpushed_commits_with_no_file_changes(self, repos):
        site, remote, _ = repos
        (site / "data" / "art.json").write_text('[{"title": "New"}]', encoding="utf-8")
        git(site, "commit", "-am", "Committed by hand")

        plan = publish.prepare(site, "origin")
        assert plan.changes == []
        assert [line.split(" ", 1)[1] for line in plan.unpushed] == ["Committed by hand"]
        publish.publish(site, plan, "")
        assert git(remote, "log", "-1", "--format=%s", "main").strip() == "Committed by hand"


class TestResolveRemote:
    def test_uses_the_only_remote(self, repos):
        site, _, _ = repos
        assert publish.resolve_remote(site) == "origin"

    def test_uses_saved_remote(self, repos):
        site, remote, _ = repos
        git(site, "remote", "add", "github", str(remote))
        assert publish.resolve_remote(site, "github") == "github"

    def test_prefers_origin_among_several(self, repos):
        site, remote, _ = repos
        git(site, "remote", "add", "github", str(remote))
        assert publish.resolve_remote(site) == "origin"

    def test_saved_remote_missing(self, repos):
        site, _, _ = repos
        with pytest.raises(PublishError, match="gone-remote"):
            publish.resolve_remote(site, "gone-remote")

    def test_ambiguous_without_origin(self, repos):
        site, remote, _ = repos
        git(site, "remote", "rename", "origin", "a")
        git(site, "remote", "add", "b", str(remote))
        with pytest.raises(PublishError, match="several remotes"):
            publish.resolve_remote(site)


class TestDefaultMessage:
    def test_new_post_hides_posts_json(self):
        changes = [Change("??", "blog/my-post.html"), Change(" M", "data/posts.json")]
        assert publish.default_message(changes) == "Add blog post: my-post"

    def test_data_and_images(self):
        changes = [
            Change(" M", "data/art.json"),
            Change("??", "media/images/art/a.png"),
            Change("??", "media/images/art/b.png"),
        ]
        assert publish.default_message(changes) == "Update art.json; add 2 images"

    def test_removed_post(self):
        changes = [Change(" D", "blog/old.html"), Change(" M", "data/posts.json")]
        assert publish.default_message(changes) == "Remove blog post: old"

    def test_long_message_falls_back_to_summary(self):
        changes = [Change("??", f"blog/a-rather-long-post-title-{i}.html") for i in range(5)]
        assert publish.default_message(changes) == "Update site content (5 files)"
