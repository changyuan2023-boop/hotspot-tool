# 热点消息提示工具

财经新闻头版分析 + 热点摘要流程，用于生成可发给模型的 prompt（早/晚摘要等）。

## 目录与文件

- **step2_总结摘要用Prompt.md**：Step 2 总结摘要用 prompt 模板（工作流会把抓取到的资讯填入占位符后发给模型）
- **step1_finance_frontpage/**：Step 1 财经头版 Agent（抓取多站头版、生成 step1_output.md 与 step2_input.txt）
- **run_hotspot_workflow.py**：全流程入口（Step 1 抓取 → Step 2 填入 prompt 模板 → Step 3 总结摘要）

**Step 1 产出**（在 `step1_finance_frontpage/`）：
- **step1_output.md** — 人类可读的头版分析报告
- **step2_input.txt** — 多站头版整理成的「资讯来源」块，供 Step 2 填入模板

**Step 2 产出**（在根目录）：
- **step3_input.txt** — 把 step2_总结摘要用Prompt.md 占位符替换为抓取内容后的完整 prompt，可复制给模型或由 Step 3 用 `--llm` 发送

**Step 3 产出**（在根目录）：
- **step3_output.txt** — 固定格式的摘要输出（标题行 + 「正文」+ 摘要内容），每次跑 Step 3 都会覆盖，适合推送或快速浏览：
  ```
  热点消息提示工具-2026030516
  正文

  （晚间/早间关注摘要内容，或提示你粘贴/使用 --llm）
  ```

---

## 文件说明（每个文件的作用）

| 文件 / 目录 | 作用 |
|-------------|------|
| **run_hotspot_workflow.py** | 工作流入口。Step 1 抓取 → Step 2 填入 prompt 模板 → Step 3 总结摘要（可 `--llm`）。支持 `--step 1/2/3`、`--llm`、`--dry-run`。 |
| **step2_总结摘要用Prompt.md** | 总结摘要用 **prompt 模板**，中间 `<!-- 资讯来源开始/结束 -->` 占位；Step 2 填入抓取内容后得到 step3_input.txt。 |
| **.env.example** | 环境变量示例。复制为 `.env` 填入 `OPENAI_API_KEY` 等，供本地 `--llm` 或 GitHub Actions 使用。 |
| **.gitignore** | 忽略 `.env`、`__pycache__/`、`.DS_Store` 等。 |
| **.github/workflows/hotspot.yml** | GitHub Actions 定时任务，自动跑工作流并提交 step1_output.md、step2_input.txt、step3_input.txt、step3_output.txt，可选推 Slack。 |
| **step1_finance_frontpage/finance_frontpage_agent.py** | Step 1 入口，拉取多站头版并写出 step1_output.md、step2_input.txt。 |
| **step1_finance_frontpage/finance_frontpage_analyzer.py** | 头版抓取与解析（含智通财经 curl 兜底）。 |
| **step1_finance_frontpage/step1_output.md** | Step 1 产出：头版分析报告。 |
| **step1_finance_frontpage/step2_input.txt** | Step 1 产出：资讯来源块，供 Step 2 填入模板。 |
| **step3_input.txt** | Step 2 产出：已填入资讯的完整 prompt，可复制给模型或由 Step 3 `--llm` 发送。 |
| **step3_output.txt** | Step 3 产出：带标题的摘要（标题 + 正文 + 内容），适合推送或浏览。 |

> `step1_finance_frontpage/__pycache__/` 为 Python 字节码缓存，可忽略。

## 用法（在本目录执行）

```bash
# 全流程
python3 run_hotspot_workflow.py

# 仅 Step 1：抓取财经头版 → 生成 step1_output.md、step2_input.txt
python3 run_hotspot_workflow.py --step 1

# 仅 Step 2：将 step2_input.txt 填入 step2_总结摘要用Prompt.md → step3_input.txt
python3 run_hotspot_workflow.py --step 2

# 仅 Step 3：读取 step3_input.txt，写 step3_output.txt（加 --llm 会调模型生成摘要）
python3 run_hotspot_workflow.py --step 3

# 只重新跑第三步并用 LLM 生成摘要（不重新抓取、不重新填入）
python3 run_hotspot_workflow.py --step 3 --llm
```

**本地运行**：进入本目录后执行 `python3 run_hotspot_workflow.py`。本目录已自包含，无需上层项目。

---

## 只推送本文件夹到 GitHub

若希望 GitHub 上只存在「热点消息提示工具」这一个仓库（不包含上层 `coding` 其他项目），可按以下方式之一操作。

**方式一：用本文件夹单独建一个 Git 仓库并推送**

1. 在终端执行（将 `你的用户名/hotspot-tool` 换成你的仓库地址）：
   ```bash
   cd 热点消息提示工具
   git init
   git add -A
   git commit -m "init"
   git remote add origin https://github.com/你的用户名/hotspot-tool.git
   git branch -M main
   git push -u origin main
   ```
2. 在 GitHub 仓库 Settings → Secrets and variables → Actions 中配置 `OPENAI_API_KEY`、`OPENAI_API_BASE`、`OPENAI_MODEL`（以及可选的 `SLACK_WEBHOOK_URL`）。
3. 在 Actions 里手动 Run workflow 试跑一次。

**方式二：保留现有 hotspot-tool 仓库，只更新为本文件夹内容**

若当前 GitHub 仓库里是整份 `coding` 项目，想改成「仓库根目录 = 本文件夹内容」：

1. 克隆一份到临时目录，用本文件夹内容覆盖后强制推送（操作前请备份或确认无需保留仓库内其他文件）：
   ```bash
   git clone https://github.com/changyuan2023-boop/hotspot-tool.git hotspot-tool-tmp
   cd hotspot-tool-tmp
   rm -rf .git
   # 把 热点消息提示工具 里的所有文件（含 .github）复制到当前目录，覆盖
   # 然后重新 init 并 force push（会清空远程其它文件，慎用）
   ```

日常只需在本目录内改代码，在**本目录**的 Git 里 commit 并 push 即可。

---

## 为什么会没有 LLM？怎么接 LLM？

**为什么默认不调 LLM？**  
- 调用会消耗 API 额度（按 token 计费），不适合在未配置时自动跑。  
- 有人更习惯把 `prompt_已填入_可直接发给模型.txt` 复制到网页/客户端里自己发，所以设计成「可选」。  
- 需要自动出摘要时，请**显式加 `--llm`** 并配好 Key。

**怎么接 LLM（自动出摘要）？**

1. **安装依赖**（若尚未安装）  
   ```bash
   pip install openai python-dotenv
   ```

2. **配置 API Key（任一大模型均可）**  
   在 **`热点消息提示工具/.env`**（或项目根目录的 `.env`）里增加：
   ```bash
   OPENAI_API_KEY=sk-xxxxxxxx   # 任一大模型 Key（OpenAI / DeepSeek / 国内中转等）
   # 可选：默认用 OpenAI 官方；其它服务需填兼容接口地址
   # OPENAI_API_BASE=https://api.openai.com/v1
   # OPENAI_API_BASE=https://api.deepseek.com   # 示例：DeepSeek
   OPENAI_MODEL=gpt-4o-mini     # 换成该服务支持的模型名，如 deepseek-chat
   ```
   只要提供方是 **OpenAI 兼容的 chat 接口**，用它的 Key 并设好 `OPENAI_API_BASE` 和对应 `OPENAI_MODEL` 即可。

3. **运行并启用 LLM**  
   ```bash
   cd 热点消息提示工具
   python3 run_hotspot_workflow.py --llm
   ```
   或只跑 Step 3 并调 LLM：  
   `python3 run_hotspot_workflow.py --step 3 --llm`

4. **结果**  
   摘要会写入 `hotspot/热点消息提示_简要版.txt` 的「正文」段，并另存一份到 `hotspot/热点摘要_输出.md`。

---

## Longbridge OpenAPI 和「LLM」的关系

Longbridge 文档里的 [LLM 组件](https://open.longbridge.com/zh-CN/docs/llm) **不是**一个可调用的「对话/摘要 API」：

- **llms.txt**：给 AI 看的 OpenAPI 文档（上下文），方便生成调用行情/交易的代码。
- **MCP**：在 Cursor / Cherry Studio 里接上 Longbridge 后，AI 可以调行情、查持仓、下单等。

也就是说：Longbridge 提供的是**数据和交易接口**，不提供「你发一段 prompt、它返回一段摘要」的接口。  
热点摘要里的**正文**必须由**任一大模型**（OpenAI / DeepSeek / 国内中转等）根据 prompt 生成，所以需要你配置 `OPENAI_API_KEY`（或兼容接口的 Key + `OPENAI_API_BASE`）。

你项目里已有的 **LONGPORT_APP_KEY / LONGPORT_APP_SECRET / LONGPORT_ACCESS_TOKEN** 是给**行情、交易**用的（如 `quote_premarket.py`、热点监控等），和「谁来做摘要」是两件事：

- **摘要由谁做**：用你配置的 `OPENAI_API_KEY`（或兼容 API）在 Step 3 加 `--llm` 时调用。
- **数据从哪来**：当前是财经头版多站抓取；若以后要在 prompt 里加 Longbridge 行情（如恒指/标普点位），可以在本工作流里用 longport SDK 拉数据拼进 prompt，再交给上面同一套 LLM 生成摘要，即「Longbridge 数据 + 你选的 LLM」一起接入。
