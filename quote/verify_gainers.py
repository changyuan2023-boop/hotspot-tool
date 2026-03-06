#!/usr/bin/env python3
"""
用 LongPort 拉取多只标的的现价与涨跌幅，用于核对文案中的涨跌数据。
盘前一律用日 K 上一交易日收盘价算涨跌幅（与 longport-quote 规则一致）。
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
_script_dir = Path(__file__).resolve().parent
if not load_dotenv(_script_dir / ".env"):
    load_dotenv(Path.cwd() / ".env")

from longport.openapi import QuoteContext, Config, Period, AdjustType


def last_trading_day_close(ctx, symbol):
    try:
        daily = ctx.history_candlesticks_by_offset(symbol, Period.Day, AdjustType.NoAdjust, False, 2)
        if daily:
            return float(daily[-1].close)
    except Exception:
        pass
    return None


def main():
    if not os.environ.get("LONGPORT_APP_KEY"):
        print("错误：未读到 LONGPORT_APP_KEY，请检查 .env", file=sys.stderr)
        sys.exit(1)

    # 用户要核对的标的：Robinhood, Coinbase, Strategy(MSTR), Circle, Bitmine(BMNR), SharpLink(SBET)
    symbols = ["HOOD.US", "COIN.US", "MSTR.US", "CRCL.US", "BMNR.US", "SBET.US"]
    names = {
        "HOOD.US": "Robinhood",
        "COIN.US": "Coinbase",
        "MSTR.US": "Strategy",
        "CRCL.US": "Circle",
        "BMNR.US": "Bitmine Immersion Technologies",
        "SBET.US": "SharpLink",
    }
    # 用户给出的跌幅（正数表示跌）
    expected_drop = {
        "HOOD.US": 4,
        "COIN.US": 4,
        "MSTR.US": 4,
        "CRCL.US": 3,
        "BMNR.US": 3.9,
        "SBET.US": 4,
    }

    config = Config.from_env()
    ctx = QuoteContext(config)
    resp = ctx.quote(symbols)
    if not resp:
        print("未获取到行情")
        return

    print("=" * 80)
    print("LongPort 实时/盘前数据核对（盘前涨跌幅按上一交易日收盘价计算）")
    print("=" * 80)

    for q in resp:
        sym = q.symbol
        name = names.get(sym, sym)
        last = None
        is_pre = False
        if q.pre_market_quote and getattr(q.pre_market_quote, "last_done", None) is not None:
            last = float(q.pre_market_quote.last_done)
            is_pre = True
        if last is None and getattr(q, "last_done", None) is not None:
            last = float(q.last_done)
        prev = last_trading_day_close(ctx, sym) if is_pre else None
        if prev is None and getattr(q, "prev_close", None) is not None:
            try:
                prev = float(q.prev_close)
            except (TypeError, ValueError):
                pass
        if last is not None and prev is not None and prev > 0:
            pct = (last - prev) / prev * 100
        else:
            pct = None
        expected = expected_drop.get(sym)
        match = ""
        if pct is not None and expected is not None:
            # 用户写的是「跌超 4%」即 <= -4
            if pct <= -expected:
                match = "✓ 符合「跌超 {}%」".format(expected)
            else:
                match = "✗ 当前跌幅 {:.2f}% 未达「跌超 {}%」".format(-pct if pct < 0 else pct, expected)
        mode = "盘前" if is_pre else "盘中"
        prev_str = "{:.2f}".format(prev) if prev is not None else "—"
        last_str = "{:.2f}".format(last) if last is not None else "—"
        pct_str = "{:+.2f}%".format(pct) if pct is not None else "—"
        print("{:<35} {}  现价: {}  昨收: {}  涨跌幅: {}  {}".format(
            name + " (" + sym + ")", mode, last_str, prev_str, pct_str, match))
        print()

    print("=" * 80)


if __name__ == "__main__":
    main()
