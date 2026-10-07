from urllib.request import urlopen

import pytest

from preview import PreviewServer


@pytest.fixture
def server(tmp_path):
    (tmp_path / "blog").mkdir()
    (tmp_path / "index.html").write_text("<h1>home</h1>", encoding="utf-8")
    (tmp_path / "blog" / "my post.html").write_text("<p>post</p>", encoding="utf-8")
    server = PreviewServer(tmp_path)
    yield server
    server.stop()


def test_serves_files_from_the_site_root(server):
    with urlopen(server.url_for("index.html")) as response:
        assert response.read() == b"<h1>home</h1>"


def test_quotes_page_paths(server):
    url = server.url_for("blog/my post.html")
    assert url.endswith("/blog/my%20post.html")
    with urlopen(url) as response:
        assert response.read() == b"<p>post</p>"


def test_only_listens_on_localhost(server):
    assert server.url_for("index.html").startswith("http://127.0.0.1:")


def test_disables_caching(server):
    with urlopen(server.url_for("index.html")) as response:
        assert response.headers["Cache-Control"] == "no-store"


def test_reuses_one_server(server):
    assert server.url_for("a.html").rsplit("/", 1)[0] == server.url_for("b.html").rsplit("/", 1)[0]
