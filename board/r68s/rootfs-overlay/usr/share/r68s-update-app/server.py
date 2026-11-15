from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
import secrets

TOKEN = secrets.token_urlsafe(32)
CONFIG = Path("/config")
VERSION = r"[0-9]+\.[0-9]+(?:\.[0-9]+)?(?:\.(?:dev|rc)[0-9]+)?"


def read_status():
    try:
        lines = (CONFIG / "status").read_text().splitlines()
    except OSError:
        lines = []
    current = next((line.removeprefix("当前版本 ") for line in lines
                    if re.fullmatch(f"当前版本 {VERSION}", line)), "—")
    target = next((line.removeprefix("仓库最新版本 ") for line in lines
                   if re.fullmatch(f"仓库最新版本 {VERSION}", line)), "")
    message = next((line for line in lines if not line.startswith(
        ("当前版本 ", "仓库最新版本 ")
    )), "有可用更新" if target else "等待系统更新服务")
    if message == "暂未找到正式发布的 R68S 系统更新。":
        message = "暂无正式版更新"
    queued = (CONFIG / "check").exists() or (CONFIG / "install").exists()
    busy = queued or message.startswith("正在下载和安装 ")
    if queued:
        message = "等待安装…" if (CONFIG / "install").exists() else "正在检查…"
    return current, target, message, busy


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.client_address[0] != "172.30.32.2":
            self.send_error(403)
            return
        current, target, message, busy = read_status()
        refresh = '<meta http-equiv="refresh" content="5">' if busy else ""
        disabled = "disabled" if busy else ""
        target_row = f"<dt>目标版本</dt><dd>{escape(target)}</dd>" if target else ""
        install = ('<button class="primary" name="action" value="install" '
                   f'{disabled}>安装最新版</button>') if target else ""
        check_style = "" if target else "primary"
        body = f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        {refresh}<title>系统更新</title>
        <style>
        :root {{
          color-scheme: light dark;
          --surface: #fff; --background: #f7f7f7; --border: #ddd;
          --text: #212121; --muted: #616161; --accent: #007da0; --on-accent: #fff;
        }}
        @media (prefers-color-scheme: dark) {{
          :root {{
            --surface: #1c1c1c; --background: #111; --border: #383838;
            --text: #eee; --muted: #bbb; --accent: #4bc4e7; --on-accent: #102b33;
          }}
        }}
        * {{ box-sizing: border-box; }}
        body {{ margin: 0; background: var(--background); color: var(--text);
                font: 14px/1.5 Roboto, "Microsoft YaHei", system-ui, sans-serif; }}
        header {{ background: var(--surface); border-bottom: 1px solid var(--border);
                  padding: 13px 24px; }}
        h1 {{ margin: 0; font-size: 20px; font-weight: 500; }}
        main {{ padding: 28px 16px; }}
        section {{ max-width: 560px; margin: auto; border: 1px solid var(--border);
                   border-radius: 12px; background: var(--surface); padding: 20px; }}
        h2 {{ display: flex; align-items: center; gap: 10px; margin: 0 0 16px;
              font-size: 18px; font-weight: 600; }}
        h2 span {{ color: var(--accent); font-size: 24px; line-height: 1; }}
        dl {{ display: grid; grid-template-columns: auto minmax(0, 1fr);
              gap: 12px 20px; margin: 0; }}
        dt {{ color: var(--muted); }}
        dd {{ margin: 0; text-align: right; overflow-wrap: anywhere; }}
        form {{ display: flex; justify-content: flex-end; gap: 8px; flex-wrap: wrap;
                margin-top: 18px; padding-top: 12px; border-top: 1px solid var(--border); }}
        button {{ font: inherit; font-weight: 500; padding: 0 14px; min-height: 40px;
                  border: 0; border-radius: 8px; background: transparent;
                  color: var(--accent); cursor: pointer; }}
        button.primary {{ background: var(--accent); color: var(--on-accent); }}
        button:disabled {{ opacity: .5; cursor: default; }}
        button:focus-visible {{ outline: 2px solid var(--accent); outline-offset: 2px; }}
        </style></head><body>
        <header><h1>系统更新</h1></header>
        <main><section aria-labelledby="device">
        <h2 id="device"><span aria-hidden="true">⟳</span>R68S · Home Assistant OS</h2>
        <dl><dt>当前版本</dt><dd>{escape(current)}</dd>
        {target_row}<dt>更新状态</dt><dd role="status">{escape(message)}</dd></dl>
        <form method="post" action="./">
        <input type="hidden" name="token" value="{TOKEN}">
        <button class="{check_style}" name="action" value="check" {disabled}>检查更新</button>
        {install}</form></section></main></body></html>""".encode()
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
        _, target, _, busy = read_status()
        if busy or (action == "install" and not target):
            self.send_error(409)
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
