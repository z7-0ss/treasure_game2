"""给手机下载 APK 用的小服务器：多线程 + 支持 Range + 正确 MIME。"""
import http.server
import os
import socketserver
import sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8899
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dist")
MIME = {".apk": "application/vnd.android.package-archive",
        ".html": "text/html; charset=utf-8",
        ".zip": "application/zip",
        ".png": "image/png"}


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def guess_type(self, path):
        ext = os.path.splitext(str(path))[1].lower()
        return MIME.get(ext, super().guess_type(path))

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))


class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


if __name__ == "__main__":
    print(f"serving {ROOT} on http://0.0.0.0:{PORT}", flush=True)
    Server(("0.0.0.0", PORT), Handler).serve_forever()
