#!/usr/bin/env python3
"""
从 .env 读取行情 API 凭证并请求盘前/盘后报价（LongPort）。
我运行时会自动读项目根目录的 .env，无需在终端 export。
"""
import os
import sys
from pathlib import Path

# 先加载 .env（脚本所在目录 或 当前工作目录）
from dotenv import load_dotenv
_script_dir = Path(__file__).resolve().parent
_env_file = _script_dir / ".env"
if not load_dotenv(_env_file):
    load_dotenv(Path.cwd() / ".env")

from longport.openapi import QuoteContext, Config, Period, AdjustType


def main():
    if not os.environ.get("LONGPORT_APP_KEY"):
        print("错误：未读到 LONGPORT_APP_KEY。请检查：", file=sys.stderr)
        print("  1. 项目目录下是否有 .env 文件（可复制 .env.example 为 .env）", file=sys.stderr)
        print("  2. .env 内是否填写了 LONGPORT_APP_KEY=、LONGPORT_APP_SECRET=、LONGPORT_ACCESS_TOKEN=", file=sys.stderr)
        print("  3. 等号两边不要空格，值不要加引号。示例：LONGPORT_APP_KEY=abc123", file=sys.stderr)
        print("  当前脚本所在目录：", _script_dir, file=sys.stderr)
        sys.exit(1)
    config = Config.from_env()
    ctx = QuoteContext(config)
    symbol = os.environ.get("QUOTE_SYMBOL", "TSLA.US")
    # 用日 K 取「最近一个已结束交易日」的收盘价作为昨收，与 LongBridge Pro 一致（北京时间「昨天」= 美股最近收盘日）
    try:
        daily = ctx.history_candlesticks_by_offset(symbol, Period.Day, AdjustType.NoAdjust, False, 2)
        last_close = float(daily[-1].close) if daily else None
        last_close_date = str(getattr(daily[-1], "timestamp", ""))[:10] if daily else ""
    except Exception:
        last_close = None
        last_close_date = ""
    resp = ctx.quote([symbol])
    if not resp:
        print("未获取到行情")
        return
    for q in resp:
        prev_close_display = f"{last_close:.2f}（日K {last_close_date}）" if last_close else q.prev_close
        print(f"标的: {q.symbol}  正股最新价: {q.last_done}  昨收: {prev_close_display}")
        if q.pre_market_quote:
            pm = q.pre_market_quote
            prev = last_close if last_close else (float(q.prev_close) if q.prev_close else None)
            if prev and prev > 0:
                pct = (float(pm.last_done) - prev) / prev * 100
                print(f"盘前: 最新价 {pm.last_done}  高 {pm.high} 低 {pm.low}  成交量 {pm.volume}  → 盘前涨幅 {pct:+.2f}%")
            else:
                print(f"盘前: 最新价 {pm.last_done}  高 {pm.high} 低 {pm.low}  成交量 {pm.volume}")
        else:
            print("盘前: 暂无数据")
        if q.post_market_quote:
            pm_post = q.post_market_quote
            prev = last_close if last_close else (float(q.prev_close) if q.prev_close else None)
            if prev and prev > 0:
                pct = (float(pm_post.last_done) - prev) / prev * 100
                print(f"盘后: 最新价 {pm_post.last_done}  高 {pm_post.high} 低 {pm_post.low}  成交量 {pm_post.volume}  → 盘后涨幅 {pct:+.2f}%")
            else:
                print(f"盘后: 最新价 {pm_post.last_done}  高 {pm_post.high} 低 {pm_post.low}  成交量 {pm_post.volume}")


if __name__ == "__main__":
    main()
