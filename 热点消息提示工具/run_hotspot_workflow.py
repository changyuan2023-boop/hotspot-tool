#!/usr/bin/env python3
"""
热点摘要工作流：抓取 → 填入流程测试版 → 总结摘要
每步产出可单独检验；支持只跑某一步或全流程自动执行。
用法：
  python3 run_hotspot_workflow.py              # 执行全部三步
  python3 run_hotspot_workflow.py --step 1    # 只执行第 1 步（抓取）
  python3 run_hotspot_workflow.py --step 2    # 只执行第 2 步（填入）
  python3 run_hotspot_workflow.py --step 3    # 只执行第 3 步（摘要，需先有已填入版）
  python3 run_hotspot_workflow.py --dry-run   # 打印将执行步骤，不写文件
"""

import argparse
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# 默认路径：财经头版在本目录 finance_frontpage；热点摘要流程与产出在项目 hotspot/ 目录
ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
HOTSPOT_DIR = PROJECT_ROOT / "hotspot"
FINANCE_DIR = ROOT / "finance_frontpage"
AGENT_SCRIPT = FINANCE_DIR / "finance_frontpage_agent.py"
PROMPT_INPUT_FILE = FINANCE_DIR / "agent_prompt_input.txt"
REPORT_FILE = FINANCE_DIR / "agent_report.md"
FLOW_MD = HOTSPOT_DIR / "热点摘要_流程测试版.md"
FLOW_FILLED_MD = HOTSPOT_DIR / "热点摘要_流程测试版_已填入.md"
PROMPT_READY_FILE = HOTSPOT_DIR / "prompt_已填入_可直接发给模型.txt"
SUMMARY_OUTPUT_FILE = HOTSPOT_DIR / "热点摘要_输出.md"
# 简要版摘要（固定格式：标题行 + 正文），始终输出到此文件
BRIEF_OUTPUT_FILE = HOTSPOT_DIR / "热点消息提示_简要版.txt"

MARKER_START = "<!-- 资讯来源开始 -->"
MARKER_END = "<!-- 资讯来源结束 -->"


def step1_fetch(timeout: int = 25, dry_run: bool = False) -> bool:
    """步骤 1：运行 finance_frontpage_agent，生成 agent_prompt_input.txt 与 agent_report.md"""
    print("[Step 1] 抓取财经头版 → 生成 agent_prompt_input.txt / agent_report.md")
    if dry_run:
        print("  (dry-run) 将执行: python3", AGENT_SCRIPT, "-o", REPORT_FILE)
        return True
    ret = subprocess.run(
        [sys.executable, str(AGENT_SCRIPT), "--timeout", str(timeout), "-o", str(REPORT_FILE)],
        cwd=str(ROOT),
        capture_output=False,
    )
    if ret.returncode != 0:
        print("[Step 1] 失败，returncode:", ret.returncode)
        return False
    if not PROMPT_INPUT_FILE.exists() or PROMPT_INPUT_FILE.stat().st_size == 0:
        print("[Step 1] 失败：未生成或为空", PROMPT_INPUT_FILE)
        return False
    print("[Step 1] 完成。可检验:", REPORT_FILE, "|", PROMPT_INPUT_FILE)
    return True


def step2_fill(dry_run: bool = False) -> bool:
    """步骤 2：将 agent_prompt_input.txt 填入流程测试版中占位符，输出到 _已填入.md"""
    print("[Step 2] 将 agent_prompt_input.txt 填入流程测试版 → 热点摘要_流程测试版_已填入.md")
    if not PROMPT_INPUT_FILE.exists():
        print("[Step 2] 失败：缺少", PROMPT_INPUT_FILE, "请先执行 Step 1")
        return False
    if not FLOW_MD.exists():
        print("[Step 2] 失败：缺少", FLOW_MD)
        return False
    content = PROMPT_INPUT_FILE.read_text(encoding="utf-8")
    flow_text = FLOW_MD.read_text(encoding="utf-8")
    if MARKER_START not in flow_text or MARKER_END not in flow_text:
        print("[Step 2] 失败：流程测试版中未找到占位符", MARKER_START, "/", MARKER_END)
        return False
    if dry_run:
        print("  (dry-run) 将替换占位符之间的内容，写入", FLOW_FILLED_MD)
        return True
    # 替换两标记之间的内容（保留两标记行）
    pattern = re.compile(
        re.escape(MARKER_START) + r"\n.*?" + re.escape(MARKER_END),
        re.DOTALL,
    )
    new_block = MARKER_START + "\n" + content.strip() + "\n" + MARKER_END
    new_flow = pattern.sub(new_block, flow_text)
    if new_flow == flow_text:
        print("[Step 2] 警告：未替换到任何内容，请检查占位符")
    FLOW_FILLED_MD.write_text(new_flow, encoding="utf-8")
    print("[Step 2] 完成。可检验:", FLOW_FILLED_MD)
    return True


def _extract_prompt_from_filled_md(text: str) -> str:
    """从已填入的流程测试版中抽出「七、Prompt 占位」代码块内的完整 prompt（供 Step 3 使用）"""
    lines = text.splitlines()
    in_block = False
    collected = []
    for line in lines:
        if line.strip() == "```":
            if in_block:
                block = "\n".join(collected)
                if "早间" in block or "晚间" in block:
                    return block
                collected = []
                in_block = False
            else:
                in_block = True
            continue
        if in_block:
            collected.append(line)
    return "\n".join(collected) if collected else ""


def _write_brief_output(body: str, dry_run: bool = False) -> None:
    """写入简要版摘要文件，格式：热点消息提示工具-YYYYMMDDHH + 正文"""
    ts = datetime.now().strftime("%Y%m%d%H")
    lines = [f"热点消息提示工具-{ts}", "正文", "", body.strip()]
    text = "\n".join(lines)
    if dry_run:
        print("  (dry-run) 将写入", BRIEF_OUTPUT_FILE)
        return
    BRIEF_OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    BRIEF_OUTPUT_FILE.write_text(text, encoding="utf-8")
    print("[Step 3] 已写入简要版摘要:", BRIEF_OUTPUT_FILE)


def step3_summary(use_llm: bool = False, dry_run: bool = False) -> bool:
    """步骤 3：基于已填入版生成「可直接发给模型」的 prompt；写简要版摘要到 hotspot/热点消息提示_简要版.txt"""
    print("[Step 3] 总结摘要：生成可发给模型的 prompt；写入简要版摘要（热点消息提示_简要版.txt）")
    if not FLOW_FILLED_MD.exists():
        print("[Step 3] 失败：缺少", FLOW_FILLED_MD, "请先执行 Step 2")
        return False
    flow_filled = FLOW_FILLED_MD.read_text(encoding="utf-8")
    prompt_body = _extract_prompt_from_filled_md(flow_filled)
    if not prompt_body.strip():
        print("[Step 3] 警告：未从已填入版中解析出 prompt 代码块，将整份已填入版作为 prompt 输出")
        prompt_body = flow_filled
    if dry_run:
        print("  (dry-run) 将写入", PROMPT_READY_FILE, "（约", len(prompt_body), "字）")
        print("  (dry-run) 将写入", BRIEF_OUTPUT_FILE)
        if use_llm:
            print("  (dry-run) 将调用 LLM 并写入", SUMMARY_OUTPUT_FILE)
        return True
    PROMPT_READY_FILE.write_text(prompt_body, encoding="utf-8")
    print("[Step 3] 已写入完整 prompt:", PROMPT_READY_FILE)

    summary_text = ""
    if use_llm:
        summary_text = _call_llm_for_summary(prompt_body)
        if summary_text:
            SUMMARY_OUTPUT_FILE.write_text(summary_text, encoding="utf-8")
            print("[Step 3] 已写入摘要:", SUMMARY_OUTPUT_FILE)
        else:
            summary_text = "（未生成：请配置 OPENAI_API_KEY 后使用 --llm 重跑，或将 hotspot/prompt_已填入_可直接发给模型.txt 发给模型，把回复粘贴到本文件「正文」下方。）"
            print("[Step 3] LLM 未返回内容，请检查 API 配置或手动复制", PROMPT_READY_FILE, "到模型")
    else:
        summary_text = "（未生成：运行 python3 run_hotspot_workflow.py --llm 自动出摘要，或将 hotspot/prompt_已填入_可直接发给模型.txt 发给模型，把回复粘贴到本文件「正文」下方。）"
        print("[Step 3] 未启用 LLM。将", PROMPT_READY_FILE, "内容复制到模型即可得到晚间/早间关注摘要。")

    _write_brief_output(summary_text, dry_run=False)
    return True


def _call_llm_for_summary(prompt: str) -> str:
    """可选：调用 OpenAI 兼容 API 生成摘要。需环境变量 OPENAI_API_KEY 或 .env"""
    import os
    try:
        from openai import OpenAI
    except ImportError:
        print("[Step 3] 未安装 openai。请执行: pip install openai python-dotenv")
        return ""
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        print("[Step 3] 未读到 OPENAI_API_KEY。请确认项目根目录 .env 中有 OPENAI_API_KEY=sk-xxx（与 LONGPORT 等在同一 .env）")
        return ""
    base_url = os.getenv("OPENAI_API_BASE", "").strip() or None
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    print("[Step 3] 正在调用 LLM（%s）生成摘要..." % (model))
    client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)
    try:
        r = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": (
                    "你是港美股市场的晚间热点编辑，只输出「晚间关注」摘要，不输出其他解释。\n"
                    "注意：中国两会/人大/政协、政府工作报告、央行与监管部委重大表态等政策事件，"
                    "对港股和中概股影响极大，若资讯中出现必须在摘要中单独体现，不可省略或合并到其他条目中。"
                )},
                {"role": "user", "content": prompt},
            ],
            max_tokens=2000,
        )
        # 兼容 OpenAI 格式 与 部分接口直接返回 str / dict
        if isinstance(r, str):
            out = r.strip()
        elif hasattr(r, "choices") and r.choices:
            out = (r.choices[0].message.content or "").strip()
        elif isinstance(r, dict):
            choices = r.get("choices") or []
            if choices and isinstance(choices[0], dict):
                msg = choices[0].get("message") or {}
                out = (msg.get("content") or "").strip()
            else:
                out = (r.get("content") or r.get("text") or "").strip()
        else:
            out = ""
        # 若返回的是 HTML 页面（错误页/登录页等），视为无效
        if out and (out.lstrip().lower().startswith("<!") or "<html" in out[:200].lower() or "<body" in out[:500].lower()):
            print("[Step 3] LLM 返回了 HTML 页面而非摘要，请检查 API 地址与 Key 是否指向正确的聊天接口")
            return ""
        if out:
            print("[Step 3] LLM 返回成功，字数:", len(out))
        return out
    except Exception as e:
        print("[Step 3] LLM 调用失败:", type(e).__name__, str(e))
        return ""


def main():
    # 启动时先加载项目根 .env（绝对路径），保证 OPENAI_API_KEY 等能被读到
    env_path = (PROJECT_ROOT / ".env").resolve()
    try:
        from dotenv import load_dotenv
        loaded = load_dotenv(str(env_path))
        load_dotenv(str((ROOT / ".env").resolve()))
    except ImportError:
        loaded = False

    ap = argparse.ArgumentParser(description="热点摘要工作流：抓取 → 填入 → 摘要")
    ap.add_argument("--step", type=int, choices=[1, 2, 3], default=0, help="只执行指定步骤（默认 0=全部）")
    ap.add_argument("--timeout", type=int, default=25, help="Step 1 抓取超时秒数")
    ap.add_argument("--llm", action="store_true", help="Step 3 调用 LLM 自动写摘要（需 OPENAI_API_KEY）")
    ap.add_argument("--dry-run", action="store_true", help="只打印将执行的操作，不写文件")
    args = ap.parse_args()

    # 若启用 LLM，先确认能读到 Key（便于排查「未生成」）
    if args.llm:
        import os
        key = os.getenv("OPENAI_API_KEY", "").strip()
        if not key:
            print("[提示] 未读到 OPENAI_API_KEY。已尝试从以下路径加载 .env：", env_path)
            print("       请确认该文件存在且包含 OPENAI_API_KEY=sk-xxx（DeepSeek 等）")
        else:
            print("[提示] 已从 .env 读到 OPENAI_API_KEY（前 8 位: %s...）" % key[:8])

    steps = [args.step] if args.step else [1, 2, 3]
    ok = True
    for s in steps:
        if s == 1:
            ok = step1_fetch(timeout=args.timeout, dry_run=args.dry_run)
        elif s == 2:
            ok = step2_fill(dry_run=args.dry_run)
        elif s == 3:
            ok = step3_summary(use_llm=args.llm, dry_run=args.dry_run)
        if not ok and not args.dry_run:
            print("工作流在 Step", s, "终止")
            return 1
    print("工作流执行完毕。可依次检验：agent_report.md → 流程测试版_已填入.md → prompt_已填入_可直接发给模型.txt → hotspot/热点消息提示_简要版.txt [→ 热点摘要_输出.md]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
