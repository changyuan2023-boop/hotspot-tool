# 热点消息提示工具

财经新闻头版分析 + 热点摘要流程，用于生成可发给模型的 prompt（早/晚摘要等）。

## 目录与文件

- **finance_frontpage/**：财经头版 Agent（抓取多站头版、生成报告与可粘贴块）
- **run_hotspot_workflow.py**：全流程入口（抓取 → 填入流程测试版 → 生成 prompt）

流程与产出去 **项目 `hotspot/` 目录** 读写。**摘要结果**统一输出到：

- **`hotspot/热点消息提示_简要版.txt`** — 每次运行 Step 3 都会生成，格式固定为：
  ```
  热点消息提示工具-2026030516
  正文

  （晚间/早间关注摘要内容，或提示你粘贴/使用 --llm）
  ```
  时间戳为生成时的「年月日时」（YYYYMMDDHH）。使用 `--llm` 时正文为模型生成的摘要；未使用时可手动将 prompt 发给模型后，把回复粘贴到该文件「正文」下方。

其他产出：`热点摘要_流程测试版.md`、`热点摘要_流程测试版_已填入.md`、`prompt_已填入_可直接发给模型.txt`、`热点摘要_输出.md`（仅 `--llm` 时写入）。

## 用法（在项目根或本目录执行）

```bash
# 全流程
python3 run_hotspot_workflow.py

# 仅 Step 1：抓取财经头版 → 生成 agent_prompt_input.txt / agent_report.md
python3 run_hotspot_workflow.py --step 1

# 仅 Step 2：将 agent_prompt_input.txt 填入流程测试版
python3 run_hotspot_workflow.py --step 2

# 仅 Step 3：从已填入版抽出 prompt 并写入 prompt_已填入_可直接发给模型.txt
python3 run_hotspot_workflow.py --step 3

# 只重新跑第三步并用 LLM 生成摘要（不重新抓取、不重新填入）
python3 run_hotspot_workflow.py --step 3 --llm
```

从项目根执行时：`python3 热点消息提示工具/run_hotspot_workflow.py`。

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
