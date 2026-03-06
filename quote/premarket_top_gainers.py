#!/usr/bin/env python3
"""
用 LongPort API 拉取一批美股的盘前报价，按盘前涨幅排序，输出 Top 10。
单次请求最多 500 个标的，此处使用常见流动性较好的美股列表。
注：盘前涨幅使用 quote 返回的 prev_close；与 LongBridge Pro 的「昨收」口径可能不同
（Pro 为最近一个已结束交易日，即北京时间「昨天」= 美股最近收盘日）。单标的请用 quote_premarket.py，该脚本已按日 K 昨收计算。
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
_script_dir = Path(__file__).resolve().parent
if not load_dotenv(_script_dir / ".env"):
    load_dotenv(Path.cwd() / ".env")

from longport.openapi import QuoteContext, Config

# 常见美股标的（流动性较好，便于覆盖盘前有成交的）
US_SYMBOLS = [
    "AAPL.US", "MSFT.US", "GOOGL.US", "GOOG.US", "AMZN.US", "NVDA.US", "META.US", "TSLA.US",
    "BRK-B.US", "JPM.US", "JNJ.US", "V.US", "UNH.US", "HD.US", "PG.US", "MA.US", "DIS.US",
    "PYPL.US", "NFLX.US", "ADBE.US", "CRM.US", "CSCO.US", "INTC.US", "AMD.US", "QCOM.US",
    "PEP.US", "KO.US", "WMT.US", "MCD.US", "ABBV.US", "TMO.US", "COST.US", "NKE.US",
    "DHR.US", "ACN.US", "NEE.US", "TXN.US", "PM.US", "BMY.US", "UNP.US", "RTX.US",
    "HON.US", "UPS.US", "LOW.US", "INTC.US", "AMGN.US", "CAT.US", "BA.US", "GE.US",
    "DE.US", "IBM.US", "ORCL.US", "NOW.US", "INTU.US", "AMAT.US", "AVGO.US", "MU.US",
    "LRCX.US", "KLAC.US", "MRVL.US", "PANW.US", "SNPS.US", "CDNS.US", "CRWD.US",
    "TEAM.US", "ZM.US", "SNOW.US", "MDB.US", "DDOG.US", "NET.US", "PLTR.US",
    "SOFI.US", "RIVN.US", "LCID.US", "NIO.US", "XPEV.US", "LI.US", "BABA.US",
    "JD.US", "PDD.US", "BIDU.US", "TME.US", "VIPS.US", "CRSP.US", "MRNA.US",
    "BNTX.US", "SHOP.US", "SQ.US", "COIN.US", "HOOD.US", "RBLX.US", "U.US",
    "PATH.US", "DOCU.US", "AI.US", "SMCI.US", "ARM.US", "CRCL.US", "GME.US", "AMC.US",
]


def main():
    if not os.environ.get("LONGPORT_APP_KEY"):
        print("错误：未读到 LONGPORT_APP_KEY，请配置 .env", file=sys.stderr)
        sys.exit(1)
    config = Config.from_env()
    ctx = QuoteContext(config)
    resp = ctx.quote(US_SYMBOLS)
    if not resp:
        print("未获取到行情")
        return
    rows = []
    for q in resp:
        if not q.pre_market_quote or not q.prev_close:
            continue
        pm = q.pre_market_quote
        try:
            prev = float(q.prev_close)
            last = float(pm.last_done)
        except (TypeError, ValueError):
            continue
        if prev <= 0:
            continue
        pct = (last - prev) / prev * 100
        rows.append((q.symbol, prev, last, pct))
    rows.sort(key=lambda x: -x[3])
    top10 = rows[:10]
    if not top10:
        print("当前无盘前报价数据（可能非盘前时段或标的无盘前成交）")
        return
    print("今日美股盘前涨幅 Top 10（LongPort API）\n")
    print(f"{'序号':<4} {'标的':<14} {'昨收':<12} {'盘前价':<12} {'盘前涨幅':<10}")
    print("-" * 52)
    for i, (sym, prev, last, pct) in enumerate(top10, 1):
        print(f"{i:<4} {sym:<14} {prev:<12.2f} {last:<12.2f} {pct:>+8.2f}%")


if __name__ == "__main__":
    main()
