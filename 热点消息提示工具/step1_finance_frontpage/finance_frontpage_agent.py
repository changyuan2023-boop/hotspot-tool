#!/usr/bin/env python3
"""
财经头版 Agent：跑头版分析 → 输出可直接粘贴到《热点摘要》全面版 Prompt 的输入块。
用法：python3 finance_frontpage_agent.py [--out 报告路径] [--prompt-only]
"""

import argparse
from datetime import datetime
from pathlib import Path

from finance_frontpage_analyzer import (
    DEFAULT_SITES,
    analyze,
    build_report,
)


def main():
    ap = argparse.ArgumentParser(description="财经头版 Agent：分析 + 生成可喂给早/晚摘要的输入")
    ap.add_argument("--timeout", type=int, default=20, help="抓取超时秒数")
    ap.add_argument("--out", "-o", default="", help="完整报告写入路径（默认 agent_report.md）")
    ap.add_argument("--prompt-only", action="store_true", help="只打印「资讯来源」粘贴块，不打印完整报告")
    ap.add_argument("--hours-back", type=int, default=12, help="抓取最近 N 小时内的快讯（默认 12）")
    args = ap.parse_args()

    sites = DEFAULT_SITES
    print("Agent 抓取站点:", [s[0] for s in sites])
    results, theme_to_sources = analyze(sites, timeout=args.timeout, hours_back=args.hours_back)

    # 完整报告
    report_path = args.out or "agent_report.md"
    report = build_report(results, theme_to_sources, out_path=report_path)
    if not args.prompt_only:
        print(report)
        print(f"\n已写入: {report_path}")

    # 供《热点摘要》全面版 Prompt 使用的「资讯来源/粘贴内容」块
    fetch_time = datetime.now().strftime("%Y%m%d%H")  # 精确到小时，如 2026030515
    paste_block = [
        "--- 以下可直接粘贴到《热点摘要》全面版 Prompt 的「资讯来源/粘贴内容」---",
        "",
        "【财经头版多站汇总】",
        f"抓取时间: {fetch_time}",
        "",
    ]
    for r in results:
        paste_block.append(f"## {r.name}")
        if not r.fetch_ok:
            paste_block.append(f"（抓取失败: {r.error}）")
        else:
            if r.headlines:
                paste_block.append("头版/首屏 (信息来自头版首屏，优先级最高，仅标题无摘要):")
                for h in r.headlines[:12]:
                    paste_block.append(f"- {h}")
            if r.other_items:
                paste_block.append("其他 (首页其他位置，按重要性排序，仅标题无摘要):")
                for o in r.other_items[:10]:
                    paste_block.append(f"- {o}")
        paste_block.append("")

    paste_block.append("--- 跨站重点主题（多站出现=更重要）---")
    theme_labels = {
        "iran_war": "伊朗/中东", "tariffs": "美国关税", "oil_energy": "油价/霍尔木兹",
        "crypto": "加密货币", "jobs_economy": "就业数据", "gold_commodity": "黄金/大宗",
        "fed_rates": "美联储", "tech_stocks": "科技/个股", "china_eu": "中国/欧盟",
        "china_policy": "中国政策/两会",
    }
    for theme_id, srcs in sorted(
        [(t, s) for t, s in theme_to_sources.items() if s],
        key=lambda x: -len(x[1]),
    ):
        label = theme_labels.get(theme_id, theme_id)
        paste_block.append(f"- {label}: {', '.join(srcs)}")
    paste_block.append("")
    paste_block.append("--- 粘贴结束 ---")

    paste_text = "\n".join(paste_block)
    if args.prompt_only:
        print(paste_text)
    else:
        # 同时写入「可粘贴」文件，方便直接复制
        prompt_input_path = Path(report_path).parent / "step2_input.txt"
        Path(prompt_input_path).write_text(paste_text, encoding="utf-8")
        print("\n" + paste_text)
        print(f"\n已写入可粘贴块: {prompt_input_path}")


if __name__ == "__main__":
    main()
