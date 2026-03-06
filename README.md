# coding

本地小任务合集，按业务分目录。

## 目录说明

| 目录 | 说明 |
|------|------|
| **热点消息提示工具/** | 财经头版分析 + 热点摘要流程：抓取多站头版 → 填入流程测试版 → 生成可发给模型的 prompt；内含 `finance_frontpage` 与 `run_hotspot_workflow.py` |
| **hotspot/** | 社区热点模块：社区热点 prompt 与前置经验（话题命名、三语标题等） |
| **hotspot_monitor/** | 热点监控：监控页面与 API（LongPort 涨跌幅）、部署与使用说明 |
| **quote/** | 行情/盘前：LongPort 盘前报价、涨幅榜等（依赖根目录 `.env` 中的 LongPort 凭证） |
| **data/** | 数据文件（如站内交易排行等） |

## 根目录保留

- `.env` / `.env.example`：环境变量（LongPort 等），不提交。
- `requirements.txt`：依赖。
- `剪贴板_书签.html`：个人书签等。

## 常用命令（在项目根执行）

```bash
# 热点消息提示工具：摘要全流程（Step 1 抓取头版 → Step 2 填入 → Step 3 生成 prompt）
python3 热点消息提示工具/run_hotspot_workflow.py

# 只跑 Step 1（抓取财经头版）
python3 热点消息提示工具/run_hotspot_workflow.py --step 1

# 热点监控后端（需 .env）
python3 hotspot_monitor/hotspot_monitor_api.py

# 盘前单标的
python3 quote/quote_premarket.py

# 盘前涨幅榜
python3 quote/premarket_top_gainers.py
```
