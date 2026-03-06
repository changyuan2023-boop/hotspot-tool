#!/usr/bin/env python3
"""
检查 LongPort SDK 是否支持新闻/资讯内容 API（以 TSLA.US 为例）。
从项目根目录 .env 读取 LONGPORT_APP_KEY / LONGPORT_APP_SECRET / LONGPORT_ACCESS_TOKEN。
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
_root = Path(__file__).resolve().parent.parent
load_dotenv(_root / ".env")

def main():
    from longport.openapi import QuoteContext, Config

    if not os.environ.get("LONGPORT_APP_KEY"):
        print("未配置 .env，请设置 LONGPORT_APP_KEY / LONGPORT_APP_SECRET / LONGPORT_ACCESS_TOKEN", file=sys.stderr)
        sys.exit(1)

    config = Config.from_env()
    ctx = QuoteContext(config)

    # 1) 列出 QuoteContext 中与 news/content 相关的方法
    news_like = [m for m in dir(ctx) if not m.startswith("_") and ("news" in m.lower() or "content" in m.lower())]
    print("QuoteContext 中与 news/content 相关的方法:", news_like or "(无)")

    # 2) 尝试常见可能的接口名（若 SDK 已加但文档未更新）
    symbol = "TSLA.US"
    for method_name in ["company_news", "news", "get_news", "news_content", "security_news"]:
        if hasattr(ctx, method_name):
            print(f"\n发现方法: {method_name}")
            try:
                fn = getattr(ctx, method_name)
                # 常见签名: (symbol) 或 (symbols, ...)
                if callable(fn):
                    result = fn([symbol]) if "news" in method_name else fn(symbol)
                    print("  返回:", result)
            except Exception as e:
                print("  调用异常:", e)
        else:
            print(f"无此方法: {method_name}")

    # 3) 确认当前 SDK 版本
    try:
        import longport
        print("\n当前 longport 版本:", getattr(longport, "__version__", "未知"))
    except Exception:
        pass

    print("\n结论: 若上面「与 news/content 相关的方法」为空且所有尝试方法均为「无此方法」，")
    print("则当前 LongPort OpenAPI 官方文档与 Python SDK 中尚未提供新闻内容接口。")
    print("可关注 https://open.longportapp.com/zh-CN/docs/changelog 或联系 LongPort 确认是否/何时开放。")

if __name__ == "__main__":
    main()
