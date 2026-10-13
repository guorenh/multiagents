# 多智能体市场调研系统

基于 **LangGraph + MCP + FastAPI + React** 的多智能体市场调研助手。
输入一个调研主题，系统自动完成「检索 → 分析 → 撰写 → 审校 → 改写」，输出一份带引用的 Markdown 调研报告。

## 目录

- [工作原理](#工作原理)
- [核心特性](#核心特性)
- [环境要求](#环境要求)
- [快速开始](#快速开始)
- [配置说明](#配置说明)
- [API 接口](#api-接口)
- [目录结构](#目录结构)
- [质量控制机制](#质量控制机制)
- [已知限制](#已知限制)

## 工作原理

整条链路是一个 LangGraph 状态机，所有专家节点执行完都回到 `supervisor` 决策下一步：

```
                    ┌──────────────┐
        START ─────▶│  supervisor  │◀────────────────────┐
                    └──────┬───────┘                     │
                           │ 按 next_step 条件路由         │
          ┌────────────┬───┴────────┬────────────┐       │
          ▼            ▼            ▼            ▼       │
     ┌────────┐  ┌─────────┐  ┌──────────┐  ┌────────┐   │
     │searcher│  │ analyst │  │ reporter │  │reviewer│   │
     └───┬────┘  └────┬────┘  └────┬─────┘  └───┬────┘   │
         │            │            │            │        │
         └────────────┴────────────┴────────────┴────────┘
                           │
                        finish ──▶ END
```

| 节点 | 职责 |
|---|---|
| **supervisor** | 用 LLM 把主题拆成 ≤3 条检索关键词（写入 `plan`），并按优先级做确定性路由 |
| **searcher** | 按 `plan` 逐条调用 MCP 搜索工具，聚合原始数据（单条失败不影响整体，全部失败才报错） |
| **analyst** | 从原始数据提炼结构化 JSON：市场规模 / 主要参与者 / 趋势 / 机会 / 风险 |
| **reporter** | 生成 Markdown 报告；若是改写轮次则带上上一版和审查意见 |
| **reviewer** | 给报告打分（0-100）并检测是否跑题，不达标则触发改写或整链重做 |

`supervisor` 的路由顺序即优先级，保证流程一定收敛：

```
无 raw_data            → search
无 analysis            → analyze
无 draft               → report
有 draft 但无评分       → review
评分 < min_score 且还有额度 → report（改写）
否则                    → finish
```

## 核心特性

- **MCP 工具接入**：搜索能力以 MCP stdio 服务提供，通过 `mcp_tools` 适配成 LangChain Tool，新增工具只需注册一个 MCP server
- **LLM 规划检索**：检索关键词由模型按主题拆解，而非直接把主题丢给搜索引擎（实测检索覆盖面从 1 条提升到 3 条，原始数据从几千字符提升到约 2 万字符）
- **审校回环**：报告经 LLM 评分，不达标自动改写；跑题则丢弃整条链路结果从头重做，有界终止
- **跑题兜底检测**：除模型判断外，额外用「主题覆盖度」确定性信号拦截跑题报告（见[质量控制机制](#质量控制机制)）
- **配置热更新**：API Key、base_url、模型名都能在前端设置页修改并立即生效，无需重启
- **会话级配置隔离**：所有凭证只存本地 `data/credentials.json`，不上传任何服务器

## 环境要求

| 依赖 | 版本（已验证） |
|---|---|
| Python | 3.12 |
| Node.js | 24.x |
| 操作系统 | Windows / macOS / Linux |

## 快速开始

### 1. 安装后端依赖

```bash
pip install -r requirements.txt
```

### 2. 准备 API Key

需要两个 Key：

| Key | 用途 | 获取地址 |
|---|---|---|
| `OPENAI_API_KEY` | 调用大模型（兼容 OpenAI 格式，DeepSeek / 通义 / Kimi 均可） | https://platform.deepseek.com |
| `TAVILY_API_KEY` | 网络搜索 | https://tavily.com |

有三种配置方式，任选其一：

**方式 A：前端设置页（推荐）**
启动服务后打开 http://127.0.0.1:8000/settings 直接填写，保存即生效。
若 Key 未配置，前端会自动跳转到该页面。

**方式 B：`.env` 文件**
在项目根目录创建 `.env`，首次启动会自动迁移到 `data/credentials.json`：

```dotenv
OPENAI_API_KEY=sk-xxxxxxxx
OPENAI_BASE_URL=https://api.deepseek.com
TAVILY_API_KEY=tvly-xxxxxxxx
```

**方式 C：直接编辑 `data/credentials.json`**

### 3. 构建前端

```bash
cd frontend
npm install
npm run build
```

### 4. 启动

```bash
python api/main.py
```

打开 http://127.0.0.1:8000 即可使用。`/docs` 是自动生成的 OpenAPI 文档。

> 服务默认只监听 `127.0.0.1`。**接口没有任何鉴权**，如需从其他机器访问，务必先自行加上认证再改绑地址。

### 前端开发模式

如果需要改前端，用 vite 热更新（已配好 `/api` 代理到 8000 端口）：

```bash
cd frontend
npm run dev      # http://localhost:5173
```

### 命令行方式

不启动 Web 服务，直接在终端跑一次调研：

```bash
python main.py
```

### 连通性自检

```bash
python test_mcp.py        # 验证 MCP 搜索服务能正常启动和调用
```

## 配置说明

### `config.yaml`

```yaml
llm:
  model_name: "deepseek-v4-flash"   # 默认模型（可被前端设置覆盖）
  base_url: "https://api.deepseek.com"
  temperature: 0.3

quality:
  min_score: 75            # 报告评分低于该值时触发改写
  max_iterations: 2        # 最大改写/重做次数，防止无限循环
  max_search_queries: 3    # supervisor 最多规划几条检索关键词
```

### 模型选择

设置页的「LLM 模型」是一个**可搜索下拉 + 允许自由输入**的输入框。

生效优先级：`前端设置(credentials.json)` → `config.yaml` 的 `model_name`。
**留空保存即回落到 `config.yaml`**。

内置建议项（均实测可用）：

```
deepseek-v4-flash
deepseek-v4-pro
deepseek-flash
deepseek-chat
deepseek-reasoner
deepseek-v4-flash-vision-exp
```

> 注意：不要用服务商的 `GET /models` 接口生成下拉列表。实测该接口只返回 2 个模型，且不包含 `deepseek-v4-flash`，会把你正在用的模型排除掉。任意模型名都可以直接手输。

### 凭证存储

- 位置：`data/credentials.json`（已加入 `.gitignore`，**不会**被提交）
- 必填项（`OPENAI_API_KEY` / `OPENAI_BASE_URL` / `TAVILY_API_KEY`）不允许被清空
- 非必填项（`LLM_MODEL`）清空后回落到 `config.yaml` 默认值

## API 接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/health` | 健康检查 |
| POST | `/research` | 创建调研任务，body `{"topic": "..."}`，返回 `{"task_id", "status"}` |
| GET | `/research/{task_id}` | 查询任务状态：`running` / `completed` / `failed` |
| GET | `/research/{task_id}/report` | 获取报告（未完成时返回 400） |
| GET | `/mcp/servers` | 列出已注册的 MCP 服务及其状态 |
| GET | `/config/keys` | 列出可配置项（**只返回是否已配置，不返回密钥明文**） |
| POST | `/config/keys` | 批量保存配置，body `{"keys": {"LLM_MODEL": "..."}}`，保存后统一重建一次 |
| GET | `/config/status` | 返回 `{"ready", "missing_keys", "model"}` |

调研任务异步执行：`POST /research` 立即返回 `task_id`，前端每 3 秒轮询状态（最多 100 次，5 分钟超时）。

## 目录结构

```
multiagents/
├── main.py                     # 命令行入口
├── runtime.py                  # 共享运行时：MCP + 工具 + LLM + 图（CLI/API 共用）
├── config.yaml                 # 模型、人设、质量控制阈值
├── requirements.txt
├── test_mcp.py                 # MCP 连通性自检
│
├── graph/                      # LangGraph 定义
│   ├── state.py                # ResearchState 状态定义
│   └── builder.py              # 图构建与条件路由
│
├── agents/                     # 各智能体节点
│   ├── supervisor.py           # 规划检索 + 路由决策
│   ├── searcher.py             # 多查询聚合检索
│   ├── analyst.py              # 结构化分析
│   ├── reporter.py             # 报告撰写 / 改写
│   └── reviewer.py             # 评分 + 跑题检测
│
├── mcp_tools/                  # MCP 接入层
│   ├── registry.py             # 服务注册表（单例，落盘 mcp_server.yaml）
│   ├── client.py               # 会话管理（串行 worker + 子进程生命周期）
│   ├── adapters.py             # MCP 工具 → LangChain Tool
│   └── servers/search_server.py# Tavily 搜索 MCP 服务
│
├── api/                        # FastAPI 服务
│   ├── main.py                 # 应用入口（CORS / 静态托管 / lifespan）
│   ├── routes/                 # research / config / mcp 路由
│   └── services/research_service.py  # 任务表与后台执行
│
├── utils/
│   ├── llm.py                  # LLM 实例（带缓存与回退链）
│   ├── key_store.py            # 凭证读写与环境变量同步
│   └── config_loader.py        # config.yaml 读取
│
├── data/credentials.json       # 本地凭证（gitignore）
└── frontend/                   # React + Vite + Ant Design
    └── src/pages/              # 调研 / MCP 服务 / 设置
```

## 质量控制机制

### 审校回环

`reviewer` 节点给报告打 0-100 分，`supervisor` 据此决策：

- **评分 ≥ `min_score`** → 通过，结束
- **评分 < `min_score` 且 `iteration < max_iterations`** → 退回 `reporter` 改写（带上上一版 + 审查意见）
- **额度用尽** → 结束并保留当前最佳版本

### 跑题检测

长篇报告最容易出的问题是「内容看起来专业，但讲的完全是另一个行业」。`reviewer` 用两路信号判断，**两者都通过才算切题**：

1. **模型判断**：要求 LLM 返回 `on_topic` 布尔值（主信号）
2. **确定性兜底**：计算主题在报告中的「最长连续覆盖比例」（`topic_coverage`），低于 `0.6` 一律判跑题，不采信模型判断

跑题时会**丢弃整条链路的结果**（`plan` / `raw_data` / `analysis` / `draft`）从头重做——因为跑题往往源于分析阶段就与主题脱节，只重写报告是没用的。

无论如何，迭代次数都有硬上限，图一定收敛。

## 已知限制

- **无自动化测试**：当前验证均为手工执行，尚未建立 `tests/` 与 CI
- **无鉴权**：接口不做身份校验，因此默认只监听回环地址。`POST /config/keys` 可覆盖配置，`POST /research` 会消耗 API 额度
- **任务状态存内存**：重启服务后历史任务丢失，无持久化
- **跑题兜底是启发式**：`topic_coverage` 阈值 0.6 对「标题完全不含主题原词」的正常报告可能误判（代价是多跑一轮）
- **前端未做代码分割**：打包产物约 1.2 MB，vite 会提示超过 500 kB
- **仅实现 stdio 传输**：MCP 注册表支持声明 `http` / `sse`，但客户端只实现了 `stdio`，其余会明确报错

## 安全提示

- `data/credentials.json` 与 `.env` 均已加入 `.gitignore`，**提交前请确认 `git status` 中没有它们**
- 若怀疑 Key 泄露，立即到对应平台轮换
