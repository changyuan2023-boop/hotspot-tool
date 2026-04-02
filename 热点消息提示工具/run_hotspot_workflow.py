#!/usr/bin/env python3
"""
热点摘要工作流：抓取 → 填入总结摘要 Prompt 模板 → 总结摘要
每步产出可单独检验；支持只跑某一步或全流程自动执行。
用法：
  python3 run_hotspot_workflow.py              # 执行全部三步
  python3 run_hotspot_workflow.py --step 1    # 只执行第 1 步（抓取）
  python3 run_hotspot_workflow.py --step 2    # 只执行第 2 步（填入 prompt 模板）
  python3 run_hotspot_workflow.py --step 3    # 只执行第 3 步（摘要，需先执行 Step 2）
  python3 run_hotspot_workflow.py --dry-run   # 打印将执行步骤，不写文件
"""

import argparse
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# 默认路径：本目录即「热点消息提示工具」；Step1 在 step1_finance_frontpage，Step2/3 产出在根目录
ROOT = Path(__file__).resolve().parent
STEP1_DIR = ROOT / "step1_finance_frontpage"
AGENT_SCRIPT = STEP1_DIR / "finance_frontpage_agent.py"
PROMPT_INPUT_FILE = STEP1_DIR / "step2_input.txt"
REPORT_FILE = STEP1_DIR / "step1_output.md"
PROMPT_TEMPLATE_FILE = ROOT / "step2_总结摘要用Prompt.md"
PROMPT_READY_FILE = ROOT / "step3_input.txt"
STEP3_OUTPUT_FILE = ROOT / "step3_output.txt"

MARKER_START = "<!-- 资讯来源开始 -->"
MARKER_END = "<!-- 资讯来源结束 -->"


def step1_fetch(timeout: int = 25, dry_run: bool = False) -> bool:
    """步骤 1：运行 finance_frontpage_agent，生成 step2_input.txt 与 step1_output.md"""
    print("[Step 1] 抓取财经头版 → 生成 step1_finance_frontpage/step2_input.txt、step1_output.md")
    if dry_run:
        print("  (dry-run) 将执行: python3", AGENT_SCRIPT, "-o", REPORT_FILE)
        return True
    ret = subprocess.run(
        [sys.executable, str(AGENT_SCRIPT), "--timeout", str(timeout), "-o", "step1_output.md"],
        cwd=str(STEP1_DIR),
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
    """步骤 2：将 step2_input.txt 填入 step2_总结摘要用Prompt.md 占位符，输出 step3_input.txt"""
    print("[Step 2] 将 step2_input.txt 填入总结摘要 Prompt 模板 → step3_input.txt")
    if not PROMPT_INPUT_FILE.exists():
        print("[Step 2] 失败：缺少", PROMPT_INPUT_FILE, "请先执行 Step 1")
        return False
    if not PROMPT_TEMPLATE_FILE.exists():
        print("[Step 2] 失败：缺少", PROMPT_TEMPLATE_FILE, "（Step 2 总结摘要用 prompt 模板）")
        return False
    content = PROMPT_INPUT_FILE.read_text(encoding="utf-8")
    template_text = PROMPT_TEMPLATE_FILE.read_text(encoding="utf-8")
    if MARKER_START not in template_text or MARKER_END not in template_text:
        print("[Step 2] 失败：模板中未找到占位符", MARKER_START, "/", MARKER_END)
        return False
    if dry_run:
        print("  (dry-run) 将替换占位符之间的内容，写入", PROMPT_READY_FILE)
        return True
    pattern = re.compile(
        re.escape(MARKER_START) + r"\n.*?" + re.escape(MARKER_END),
        re.DOTALL,
    )
    new_block = MARKER_START + "\n" + content.strip() + "\n" + MARKER_END
    prompt_body = pattern.sub(new_block, template_text)
    if prompt_body == template_text:
        print("[Step 2] 警告：未替换到任何内容，请检查占位符")
    PROMPT_READY_FILE.write_text(prompt_body, encoding="utf-8")
    print("[Step 2] 完成。可检验:", PROMPT_READY_FILE)
    return True


def _write_step3_output(body: str, dry_run: bool = False) -> None:
    """写入 Step 3 产出 step3_output.txt，格式：热点消息提示工具-YYYYMMDDHH + 正文 + 摘要"""
    ts = datetime.now().strftime("%Y%m%d%H")
    lines = [f"热点消息提示工具-{ts}", "正文", "", body.strip()]
    text = "\n".join(lines)
    if dry_run:
        print("  (dry-run) 将写入", STEP3_OUTPUT_FILE)
        return
    STEP3_OUTPUT_FILE.write_text(text, encoding="utf-8")
    print("[Step 3] 已写入:", STEP3_OUTPUT_FILE)


def step3_summary(use_llm: bool = False, dry_run: bool = False) -> bool:
    """步骤 3：读取 step3_input.txt，调用 LLM 生成摘要，写入 step3_output.txt"""
    print("[Step 3] 总结摘要：读取 step3_input.txt，生成摘要并写入 step3_output.txt")
    if not PROMPT_READY_FILE.exists():
        print("[Step 3] 失败：缺少", PROMPT_READY_FILE, "请先执行 Step 2")
        return False
    prompt_body = PROMPT_READY_FILE.read_text(encoding="utf-8")
    if dry_run:
        print("  (dry-run) 将读取", PROMPT_READY_FILE, "（约", len(prompt_body), "字）")
        if use_llm:
            print("  (dry-run) 将调用 LLM 并写入", STEP3_OUTPUT_FILE)
        return True
    print("[Step 3] 已使用 prompt:", PROMPT_READY_FILE)

    summary_text = ""
    if use_llm:
        summary_text = _call_llm_for_summary(prompt_body)
        if not summary_text:
            summary_text = "（未生成：请配置 OPENAI_API_KEY 后使用 --llm 重跑，或将 step3_input.txt 发给模型，把回复粘贴到本文件「正文」下方。）"
            print("[Step 3] LLM 未返回内容，请检查 API 配置或手动复制", PROMPT_READY_FILE, "到模型")
    else:
        summary_text = "（未生成：运行 python3 run_hotspot_workflow.py --llm 自动出摘要，或将 step3_input.txt 发给模型，把回复粘贴到本文件「正文」下方。）"
        print("[Step 3] 未启用 LLM。将", PROMPT_READY_FILE, "内容复制到模型即可得到晚间/早间关注摘要。")

    _write_step3_output(summary_text, dry_run=False)
    return True


def _call_llm_for_summary(prompt: str) -> str:
    """调用 OpenAI 兼容 API 生成摘要。先试 OPENAI_API_KEY，失败则用 OPENAI_API_KEY_BACKUP。"""
    import os
    try:
        from openai import OpenAI
    except ImportError:
        print("[Step 3] 未安装 openai。请执行: pip install openai python-dotenv")
        return ""
    primary = os.getenv("OPENAI_API_KEY", "").strip()
    backup = os.getenv("OPENAI_API_KEY_BACKUP", "").strip()
    if not primary and not backup:
        print("[Step 3] 未读到 OPENAI_API_KEY / OPENAI_API_KEY_BACKUP。请在 .env 或 Secrets 中配置")
        return ""
    base_url = os.getenv("OPENAI_API_BASE", "").strip() or None
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    for label, api_key in [("主 Key", primary), ("备用 Key", backup)]:
        if not api_key:
            continue
        print("[Step 3] 正在用 %s 调用 LLM（%s）..." % (label, model))
        out = _call_llm_once(OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key), model, prompt)
        if out:
            print("[Step 3] LLM 返回成功，字数:", len(out))
            return out
        print("[Step 3] %s 未返回有效内容，尝试备用 Key" % label)
    return ""


def _call_llm_once(client, model: str, prompt: str) -> str:
    """单次调用 LLM，失败或无效返回空字符串。"""
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
            max_tokens=800,
        )
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
        if out and (out.lstrip().lower().startswith("<!") or "<html" in out[:200].lower() or "<body" in out[:500].lower()):
            print("[Step 3] LLM 返回了 HTML 页面而非摘要，请检查 API 地址与 Key")
            return ""
        return out
    except Exception as e:
        print("[Step 3] LLM 调用失败:", type(e).__name__, str(e))
        return ""


def main():
    # 加载本目录 .env，保证 OPENAI_API_KEY 等能被读到（本地与 GitHub Actions 均可用）
    env_path = (ROOT / ".env").resolve()
    try:
        from dotenv import load_dotenv
        load_dotenv(str(env_path))
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
    print("工作流执行完毕。可依次检验：step1_finance_frontpage/step1_output.md → step3_input.txt → step3_output.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
