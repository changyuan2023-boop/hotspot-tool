#!/usr/bin/env python3
"""
帖子推送标题生成器 · 本地服务
启动后自动打开浏览器访问 http://127.0.0.1:5051/
前端请求 /api/run，由后端中转到 babbage API（避免浏览器 CORS 拦截）。
"""
import webbrowser
import threading
import requests as req
from pathlib import Path
from flask import Flask, send_file, request, jsonify

app = Flask(__name__)
HTML_PATH = Path(__file__).resolve().parent / "index.html"
PORT = 5051

AGENT_URL = "https://api.lbkrs.com/v1/babbage/api/agents/1t57lhq5cyim/runs"
AGENT_KEY = "b9b95pp21kijh17m8lsvldvxc0174wnw"


@app.route("/")
def index():
    if HTML_PATH.exists():
        return send_file(HTML_PATH, mimetype="text/html; charset=utf-8")
    return "<p>index.html 未找到</p>", 404


@app.route("/api/run", methods=["POST"])
def api_run():
    """中转到 babbage Agent API，避免浏览器 CORS 问题。"""
    body = request.get_json(force=True, silent=True) or {}
    topic_link = body.get("topic_link", "")
    if not topic_link:
        return jsonify({"ok": False, "error": "请提供 topic_link"}), 400
    try:
        resp = req.post(
            AGENT_URL,
            headers={
                "Content-Type": "application/json",
                "x-agent-key": AGENT_KEY,
            },
            json={"topic_link": topic_link},
            timeout=120,
        )
        return jsonify(resp.json()), resp.status_code
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


if __name__ == "__main__":
    url = f"http://127.0.0.1:{PORT}/"
    print(f"帖子推送标题生成器已启动：{url}")
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    app.run(host="0.0.0.0", port=PORT, debug=False)
