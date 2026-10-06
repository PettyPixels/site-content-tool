import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import quote


class _QuietNoCacheHandler(SimpleHTTPRequestHandler):
    # The default handler logs every request to stderr, which is None in the windowed
    # PyInstaller build. Logging there would raise on every request.
    def log_message(self, format, *args):
        pass

    # The site fetch()es its JSON at load time. Without this header the browser can
    # serve a cached copy, so a second Preview after a save would show stale data.
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


class PreviewServer:
    """Serves the site folder over HTTP on localhost.

    The site loads its content with fetch(), and browsers block that under file://,
    so opening index.html directly doesn't work. The server starts on first use and
    then lives until stop() is called or the app exits.
    """

    def __init__(self, site_root):
        self.site_root = site_root
        self._server = None

    def url_for(self, page):
        if self._server is None:
            self._start()
        host, port = self._server.server_address[:2]
        return f"http://{host}:{port}/{quote(page)}"

    def _start(self):
        handler = partial(_QuietNoCacheHandler, directory=str(self.site_root))
        # Bind to loopback only so the preview isn't reachable from other machines on
        # the network. Port 0 lets the OS pick a free port.
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=self._server.serve_forever, daemon=True).start()

    def stop(self):
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
