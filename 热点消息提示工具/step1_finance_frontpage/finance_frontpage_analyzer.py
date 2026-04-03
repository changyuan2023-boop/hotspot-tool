#!/usr/bin/env python3
from __future__ import annotations
"""
财经新闻头版分析工具
从多个财经网站首页抓取头版/要闻，按重要性排序：
- 头版/首屏信息最重要
- 多站同时出现的信息非常重要
- 与股票或对股市影响大的偏重要
"""

import re
import json
import argparse
import subprocess
from pathlib import Path
from urllib.parse import urlparse
from dataclasses import dataclass, field

import requests
from bs4 import BeautifulSoup

# 默认置顶站点（简中、繁中、英文各约2个）
DEFAULT_SITES = [
    ("Yahoo Finance (EN)", "https://finance.yahoo.com/"),
    ("Benzinga (EN)", "https://www.benzinga.com/"),
    ("华尔街见闻 (简中)", "https://wallstreetcn.com/"),
    ("SCMP (EN/中)", "https://www.scmp.com/"),
    ("经济通 (繁中)", "https://www.etnetchina.cn/"),
    ("智通财经 (简中)", "https://www.zhitongcaijing.com/"),
]

# 主题关键词：英文与简中/繁中，用于跨站聚合
THEME_KEYWORDS = {
    "iran_war": ["iran", "iran war", "us-iran", "tehran", "以色列", "伊朗", "中东", "霍尔木兹", "波斯湾"],
    "tariffs": ["tariff", "15%", "trump tariff", "关税", "贝森特", "bessent"],
    "oil_energy": ["oil", "crude", "hormuz", "strait", "oil price", "油价", "美油", "石油", "天然气"],
    "crypto": ["bitcoin", "crypto", "btc", "coinbase", "加密货币", "比特币"],
    "jobs_economy": ["adp", "jobs", "employment", "非农", "就业", "ism"],
    "gold_commodity": ["gold", "silver", "gold price", "黄金", "白银", "伦铝", "铝"],
    "fed_rates": ["fed", "rate cut", "miran", "降息", "美联储"],
    "tech_stocks": ["apple", "aapl", "macbook", "meta", "moderna", "mrna", "broadcom", "nvda", "ai"],
    "china_eu": ["china", "eu", "欧盟", "industrial", "制造"],
    "china_policy": ["两会", "人大", "政协", "政府工作报告", "two sessions", "npc", "李强", "十五五",
                     "央行", "pboc", "证监会", "csrc", "发改委", "财政部", "创业板", "chinext"],
}

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


@dataclass
class SiteResult:
    name: str
    url: str
    title: str
    headlines: list[str]  # 头版/首屏
    other_items: list[str]  # 首页其他
    fetch_ok: bool
    error: str = ""


def fetch_text(url: str, timeout: int = 15) -> tuple[str, bool, str]:
    try:
        r = requests.get(url, timeout=timeout, headers={"User-Agent": USER_AGENT})
        r.raise_for_status()
        return r.text, True, ""
    except requests.RequestException as e:
        # WAF 拦截（如智通财经 Tengine 405）时 fallback 到 curl（TLS 指纹不同，不会被拦截）
        if "405" in str(e) or "403" in str(e):
            return _fetch_via_curl(url, timeout)
        return "", False, str(e)


def _fetch_via_curl(url: str, timeout: int = 15) -> tuple[str, bool, str]:
    """Fallback: 用 curl 抓取，绕过 WAF 的 TLS 指纹检测"""
    try:
        result = subprocess.run(
            ["curl", "-s", "-m", str(timeout),
             "-H", f"User-Agent: {USER_AGENT}",
             "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
             "-H", "Accept-Language: zh-CN,zh;q=0.9,en;q=0.8",
             url],
            capture_output=True, text=True, timeout=timeout + 5,
        )
        if result.returncode == 0 and len(result.stdout) > 500:
            return result.stdout, True, ""
        return "", False, f"curl exit {result.returncode}, len={len(result.stdout)}"
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return "", False, f"curl fallback failed: {e}"


def extract_yahoo(html: str) -> tuple[list[str], list[str]]:
    soup = BeautifulSoup(html, "html.parser")
    headlines, other = [], []
    for tag in soup.find_all(["h2", "h3"]):
        t = (tag.get_text() or "").strip()
        if not t or len(t) < 5 or t in ("LIVE", "View More", "Latest"):
            continue
        if tag.name == "h2" and not headlines:
            headlines.append(t)
        elif tag.name == "h3" and len(headlines) < 12:
            headlines.append(t)
        elif t and t not in headlines and t not in other:
            other.append(t)
    return headlines[:15], other[:20]


def extract_benzinga(html: str) -> tuple[list[str], list[str]]:
    soup = BeautifulSoup(html, "html.parser")
    headlines, other = [], []
    for tag in soup.find_all("h2"):
        t = (tag.get_text() or "").strip()
        if t and len(t) > 10 and t not in headlines:
            headlines.append(t)
    for tag in soup.find_all("h3"):
        t = (tag.get_text() or "").strip()
        if t and len(t) > 8 and t not in headlines and t not in other:
            if len(headlines) < 10:
                headlines.append(t)
            else:
                other.append(t)
    return headlines[:15], other[:20]


def extract_zhitongcaijing(html: str) -> tuple[list[str], list[str]]:
    """智通财经：轮播头条 + 小图标题 + 列表标题。"""
    soup = BeautifulSoup(html, "html.parser")
    headlines, other = [], []
    # 轮播头条
    for tag in soup.select(".banner-swipe-text-content"):
        t = (tag.get_text() or "").strip()
        if t and len(t) > 4 and t not in headlines:
            headlines.append(t)
    # 小图区标题（首屏右侧）
    for tag in soup.select(".small-image-item .show-text div"):
        t = (tag.get_text() or "").strip()
        if t and len(t) > 4 and t not in headlines:
            headlines.append(t)
    # 列表项标题
    for tag in soup.select(".info-item-content-title a"):
        t = (tag.get_text() or "").strip()
        if t and len(t) > 4 and t not in headlines and t not in other:
            other.append(t)
    return headlines[:15], other[:25]


def fetch_wallstreetcn_lives(timeout: int = 15, hours_back: int = 12) -> tuple[list[str], list[str], str]:
    """华尔街见闻为 SPA，首页无 HTML 正文；改调快讯 API 取头条。返回 (headlines, other, error)。"""
    import time as _time
    api = "https://api-prod.wallstreetcn.com/apiv1/content/lives/pc?limit=100"
    try:
        r = requests.get(api, timeout=timeout, headers={"User-Agent": USER_AGENT})
        r.raise_for_status()
        data = r.json()
    except requests.RequestException as e:
        return [], [], str(e)
    except (ValueError, KeyError) as e:
        return [], [], f"JSON error: {e}"
    raw = data.get("data")
    if not isinstance(raw, dict):
        return [], [], "no data in response"
    cutoff = _time.time() - hours_back * 3600
    # API 按频道返回：us_stock 优先，再 global / a_stock 等
    items = []
    for ch in ("us_stock", "global", "a_stock", "commodity", "forex"):
        sub = raw.get(ch)
        if isinstance(sub, dict) and isinstance(sub.get("items"), list):
            for item in sub["items"]:
                if not isinstance(item, dict):
                    continue
                ts = item.get("created_at") or item.get("display_time") or 0
                if ts and isinstance(ts, (int, float)) and ts < cutoff:
                    continue
                items.append(item)
    seen = set()
    headlines, other = [], []
    for item in items:
        title = (item.get("title") or (item.get("content_text") or "")[:120] or "").strip()
        if not title or len(title) < 2 or title in seen:
            continue
        seen.add(title)
        if len(headlines) < 40:
            headlines.append(title)
        elif len(other) < 60:
            other.append(title)
    return headlines, other, ""


def extract_generic(html: str) -> tuple[list[str], list[str]]:
    soup = BeautifulSoup(html, "html.parser")
    headlines, other = [], []
    for tag in soup.find_all(["h1", "h2", "h3"]):
        t = (tag.get_text() or "").strip()
        if not t or len(t) < 4:
            continue
        if tag.name == "h1" or (tag.name == "h2" and len(headlines) < 8):
            if t not in headlines:
                headlines.append(t)
        else:
            if t not in headlines and t not in other:
                other.append(t)
    return headlines[:15], other[:25]


def extract_site(name: str, url: str, html: str) -> SiteResult:
    domain = urlparse(url).netloc.lower()
    if "yahoo" in domain:
        head, other = extract_yahoo(html)
    elif "benzinga" in domain:
        head, other = extract_benzinga(html)
    elif "zhitongcaijing" in domain:
        head, other = extract_zhitongcaijing(html)
    else:
        head, other = extract_generic(html)
    title = ""
    try:
        soup = BeautifulSoup(html, "html.parser")
        t = soup.find("title")
        if t:
            title = (t.get_text() or "").strip()
    except Exception:
        pass
    return SiteResult(
        name=name,
        url=url,
        title=title,
        headlines=head,
        other_items=other,
        fetch_ok=True,
    )


def match_theme(text: str) -> list[str]:
    text_lower = (text or "").lower()
    themes = []
    for theme_id, keywords in THEME_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text_lower or kw in text:
                themes.append(theme_id)
                break
    return themes


def analyze(sites: list[tuple[str, str]], timeout: int = 15, hours_back: int = 12) -> tuple[list[SiteResult], dict]:
    results = []
    theme_to_sources = {t: [] for t in THEME_KEYWORDS}

    for name, url in sites:
        domain = urlparse(url).netloc.lower()
        # 华尔街见闻：SPA 无首屏 HTML，改用快讯 API
        if "wallstreetcn" in domain:
            head, other, err = fetch_wallstreetcn_lives(timeout=timeout, hours_back=hours_back)
            if err and not head:
                results.append(SiteResult(name=name, url=url, title="华尔街见闻", headlines=[], other_items=[], fetch_ok=False, error=err))
            else:
                sr = SiteResult(name=name, url=url, title="华尔街见闻", headlines=head, other_items=other, fetch_ok=True)
                results.append(sr)
                for line in sr.headlines + sr.other_items:
                    for theme in match_theme(line):
                        if sr.name not in theme_to_sources[theme]:
                            theme_to_sources[theme].append(sr.name)
            continue

        html, ok, err = fetch_text(url, timeout=timeout)
        if not ok:
            results.append(SiteResult(name=name, url=url, title="", headlines=[], other_items=[], fetch_ok=False, error=err))
            continue
        sr = extract_site(name, url, html)
        results.append(sr)
        for line in sr.headlines + sr.other_items:
            for theme in match_theme(line):
                if sr.name not in theme_to_sources[theme]:
                    theme_to_sources[theme].append(sr.name)
    return results, theme_to_sources


def build_report(results: list[SiteResult], theme_to_sources: dict, out_path: str | None = None) -> str:
    lines = [
        "# 财经头版重要性分析",
        "",
        "## 一、各站抓取情况",
        "",
    ]
    for r in results:
        status = "✓" if r.fetch_ok else f"✗ ({r.error})"
        lines.append(f"- **{r.name}** {status}")
        if r.headlines:
            lines.append("  - 头版/首屏: " + " | ".join(r.headlines[:8]))
        if r.other_items and r.fetch_ok:
            lines.append("  - 其他: " + " | ".join(r.other_items[:5]))
        lines.append("")

    lines.extend([
        "## 二、跨站主题（多站出现 = 更重要）",
        "",
    ])
    # 按出现站点数排序
    sorted_themes = sorted(
        [(t, srcs) for t, srcs in theme_to_sources.items() if srcs],
        key=lambda x: -len(x[1]),
    )
    theme_labels = {
        "iran_war": "伊朗/中东局势",
        "tariffs": "美国关税（15%等）",
        "oil_energy": "油价/能源/霍尔木兹",
        "crypto": "加密货币",
        "jobs_economy": "就业/经济数据",
        "gold_commodity": "黄金/大宗商品",
        "fed_rates": "美联储/利率",
        "tech_stocks": "科技股/个股",
        "china_eu": "中国/欧盟",
        "china_policy": "中国重大政策/两会",
    }
    for theme_id, srcs in sorted_themes:
        label = theme_labels.get(theme_id, theme_id)
        lines.append(f"- **{label}** — 出现于: {', '.join(srcs)} ({len(srcs)} 站)")
    lines.append("")

    lines.extend([
        "## 三、重要性结论（综合头版+多站+股市相关）",
        "",
        "### 非常重要（多站头版且影响股市）",
        "",
    ])
    # 根据主题与关键词生成结论
    high = []
    if theme_to_sources.get("iran_war"):
        high.append("**伊朗/中东局势**：影响油价、避险资产、全球风险偏好，多站头版。")
    if theme_to_sources.get("tariffs"):
        high.append("**美国 15% 全球关税**：财长称本周或落地，影响贸易与通胀预期。")
    if theme_to_sources.get("oil_energy"):
        high.append("**油价/霍尔木兹海峡**：特朗普护航表态后美油转跌，航运与能源股敏感。")
    if theme_to_sources.get("crypto"):
        high.append("**加密货币**：比特币破 7 万、Coinbase 等个股大涨，多站提及。")
    if theme_to_sources.get("jobs_economy"):
        high.append("**就业数据**：ADP 等超预期，支撑美股与利率预期。")
    for h in high:
        lines.append("- " + h)
    lines.append("")

    lines.append("### 重要（头版或单站重点）")
    lines.append("")
    mid = []
    if theme_to_sources.get("gold_commodity"):
        mid.append("黄金/白银、伦铝等大宗商品波动。")
    if theme_to_sources.get("fed_rates"):
        mid.append("美联储表态（如米兰：伊朗风险不阻碍继续降息）。")
    if theme_to_sources.get("tech_stocks"):
        mid.append("苹果 MacBook Neo、Moderna 和解、Meta 与新闻集团合作等个股与科技新闻。")
    if theme_to_sources.get("china_eu"):
        mid.append("中国/欧盟产业政策与贸易关系。")
    if theme_to_sources.get("china_policy"):
        high.append("**中国重大政策/两会**：人大/政协会议、政府工作报告、央行/证监会表态等，影响港股及中概股走势。")
    for m in mid:
        lines.append("- " + m)
    if not mid:
        lines.append("- （由上方主题与各站头版自行判断）")
    lines.append("")

    report = "\n".join(lines)
    if out_path:
        Path(out_path).write_text(report, encoding="utf-8")
    return report


def main():
    ap = argparse.ArgumentParser(description="财经新闻头版分析")
    ap.add_argument("--sites", nargs="*", help="自定义站点，格式为 名称:URL，不传则用内置6站")
    ap.add_argument("--timeout", type=int, default=15, help="请求超时秒数")
    ap.add_argument("--out", "-o", default="", help="输出 Markdown 报告路径")
    ap.add_argument("--json", action="store_true", help="同时输出 JSON 摘要")
    args = ap.parse_args()

    if args.sites:
        sites = []
        for s in args.sites:
            if ":" in s:
                name, url = s.split(":", 1)
                sites.append((name.strip(), url.strip()))
            else:
                sites.append((s, s))
        if not sites:
            sites = DEFAULT_SITES
    else:
        sites = DEFAULT_SITES

    print("抓取站点:", [s[0] for s in sites])
    results, theme_to_sources = analyze(sites, timeout=args.timeout)
    report = build_report(results, theme_to_sources, out_path=args.out or None)
    print(report)

    if args.out:
        Path(args.out).write_text(report, encoding="utf-8")
        print(f"\n已写入: {args.out}")

    if args.json:
        j = {
            "sites": [{"name": r.name, "ok": r.fetch_ok, "headlines_count": len(r.headlines)} for r in results],
            "themes": {k: v for k, v in theme_to_sources.items() if v},
        }
        jpath = (args.out or "frontpage_report").replace(".md", "") + ".json"
        Path(jpath).write_text(json.dumps(j, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"JSON: {jpath}")


if __name__ == "__main__":
    main()
