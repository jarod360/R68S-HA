from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import secrets

TOKEN = secrets.token_urlsafe(32)
CONFIG = Path("/config")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.client_address[0] != "172.30.32.2":
            self.send_error(403)
            return
        try:
            status = (CONFIG / "status").read_text()
        except OSError:
            status = "等待 HAOS 更新服务。"
        body = f"""<!doctype html><html lang="zh-CN"><meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>R68S 系统更新</title><h1>R68S 系统更新</h1>
        <pre>{escape(status)}</pre>
        <form method="post" action="./">
        <input type="hidden" name="token" value="{TOKEN}">
        <button name="action" value="check">检查更新</button>
        <button name="action" value="install">安装最新版本</button>
        </form><p>安装完成后，在 HA 的系统页面重启设备。</p>
        <a href="./">刷新状态</a></html>""".encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.client_address[0] != "172.30.32.2":
            self.send_error(403)
            return
        actions = {f"token={TOKEN}&action={action}".encode(): action
                   for action in ("check", "install")}
        size = self.headers.get("Content-Length", "")
        if not size.isdecimal() or len(size) > 3 or int(size) > 128:
            self.send_error(400)
            return
        action = actions.get(self.rfile.read(int(size)))
        if not action:
            self.send_error(403)
            return
        try:
            (CONFIG / action).touch(exist_ok=True)
        except OSError:
            self.send_error(503)
            return
        self.send_response(303)
        self.send_header("Location", "./")
        self.end_headers()


ThreadingHTTPServer(("0.0.0.0", 8099), Handler).serve_forever()
