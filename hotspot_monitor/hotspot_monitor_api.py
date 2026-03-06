#!/usr/bin/env python3
"""
热点监控 API：为前端提供 LongPort 涨跌幅。
- 站内数据：由你在 Metabase 复制表格后粘贴到前端，前端解析后把 symbols 发来。
- 本接口：POST /api/quotes 接收 symbols，返回各标的当前/盘前涨跌幅。
"""
import os
from pathlib import Path
from datetime import datetime, timezone

from dotenv import load_dotenv
_script_dir = Path(__file__).resolve().parent
if not load_dotenv(_script_dir / ".env"):
    load_dotenv(Path.cwd() / ".env")

from flask import Flask, jsonify, request, send_file

app = Flask(__name__)
# 页面由本服务在 / 提供，与 /api 同源，无需 CORS

# 同目录下的热点监控页面
HOTSPOT_HTML = _script_dir / "hotspot_monitor.html"


@app.route("/")
def index():
    """直接打开 http://127.0.0.1:5000/ 即为热点监控页，避免 file:// 打开时的 Failed to fetch。"""
    if HOTSPOT_HTML.exists():
        return send_file(HOTSPOT_HTML, mimetype="text/html; charset=utf-8")
    return "<p>请将 hotspot_monitor.html 放在本脚本同目录下。</p>", 404


def _last_trading_day_close(ctx, symbol):
    """盘前涨跌幅专用：用日 K 最近一根（上一交易日）收盘价，与 .cursor/rules/longport-quote 及 LongBridge Pro 一致。"""
    try:
        from longport.openapi import Period, AdjustType
        daily = ctx.history_candlesticks_by_offset(symbol, Period.Day, AdjustType.NoAdjust, False, 2)
        if daily:
            return float(daily[-1].close)
    except Exception:
        pass
    return None


def fetch_quotes(symbols):
    """用 LongPort 拉取报价（含盘前）。涨跌幅规则：盘前一律用上一交易日收盘价（日 K 昨收），盘中用 quote.prev_close。"""
    if not symbols or not os.environ.get("LONGPORT_APP_KEY"):
        return {}
    try:
        from longport.openapi import QuoteContext, Config
        config = Config.from_env()
        ctx = QuoteContext(config)
        resp = ctx.quote(symbols)
    except Exception as e:
        return {"_error": str(e)}
    out = {}
    for q in (resp or []):
        last = None
        prev = None
        is_pre = False
        if q.pre_market_quote and getattr(q.pre_market_quote, "last_done", None) is not None:
            last = float(q.pre_market_quote.last_done)
            is_pre = True
        if last is None and getattr(q, "last_done", None) is not None:
            last = float(q.last_done)
        # 盘前：只用上一交易日收盘价（日 K）算涨跌幅，不用 quote.prev_close
        if is_pre:
            prev = _last_trading_day_close(ctx, q.symbol)
        if prev is None and getattr(q, "prev_close", None) is not None:
            try:
                prev = float(q.prev_close)
            except (TypeError, ValueError):
                pass
        if last is not None and prev is not None and prev > 0:
            pct = (last - prev) / prev * 100
        else:
            pct = None
        out[q.symbol] = {
            "last_done": last,
            "prev_close": prev,
            "pct": round(pct, 2) if pct is not None else None,
            "is_premarket": is_pre,
        }
    return out


@app.route("/api/quotes", methods=["POST"])
def api_quotes():
    """请求体 JSON: { "symbols": ["TSLA.US", "00700.HK", ...] }，返回各标的涨跌幅等。"""
    try:
        body = request.get_json(force=True, silent=True) or {}
        symbols = list(body.get("symbols") or [])
    except Exception:
        symbols = []
    if not symbols:
        return jsonify({"ok": False, "error": "请提供 symbols 数组", "quotes": {}}), 400
    # 去重且限制数量，避免单次请求过大
    symbols = list(dict.fromkeys(s.strip() for s in symbols if isinstance(s, str) and s.strip()))[:200]
    quotes = fetch_quotes(symbols)
    if "_error" in quotes:
        return jsonify({
            "ok": False,
            "error": quotes["_error"],
            "quotes": {},
            "api_updated_at": datetime.now(tz=timezone.utc).isoformat(),
        }), 500
    return jsonify({
        "ok": True,
        "quotes": quotes,
        "api_updated_at": datetime.now(tz=timezone.utc).isoformat(),
    })


@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    # macOS 上 5000 常被 AirPlay 占用，可改用 PORT=5001 python3 hotspot_monitor_api.py
    app.run(host="0.0.0.0", port=port, debug=True)
