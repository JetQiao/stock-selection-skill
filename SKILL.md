---
name: pb-roe-stock-selection
description: A股 PB-ROE 价值选股模型。当用户提到"PB-ROE 选股"、"价值选股"、"低估值高ROE"、"PB ROE 模型"、"选股回测"、"A股价值股筛选"时使用。一键运行筛选并生成可视化 HTML 报告。
---

# PB-ROE 选股 Skill

## ⚠️ 运行环境前提（Claude 必读）

本 skill **只在本地 Claude Code（CLI / Desktop / IDE 扩展）中可用**。

如果你（Claude）在以下环境读到这份 SKILL.md，请**直接告知用户无法运行**，不要尝试执行：
- claude.ai 网页聊天 / 托管沙箱
- 任何无法访问 `eastmoney.com` / `sina.com.cn` / `xueqiu.com` 等中国财经域名的环境

原因：
1. **网络白名单**：akshare 数据源需要直连中国财经 API，托管沙箱通常只通 npm/pypi/github，会被 403 拦截
2. **沙箱不持久化**：装到 `~/.claude/skills/` 的文件每个任务后会被清掉
3. **报告无法查看**：HTML 输出依赖 `open` / `xdg-open` 在用户浏览器中打开，沙箱里看不到

正确做法：让用户在自己电脑上装 [Claude Code](https://claude.com/claude-code)，然后再用本 skill。

---

## 触发关键词

PB-ROE、PB ROE 选股、价值选股、低估值高ROE、净资产收益率筛选、市净率筛选、
A股价值股、价值投资模型、ROE PB 模型、选股报告、HTML 选股报告

---

## 这个 Skill 做什么

基于经典的 PB-ROE 价值投资模型，从全 A 股中筛选**低估值 + 高且可持续盈利能力**的公司，输出一份可视化的 HTML 报告（图表 + 表格 + 风险提示）。

核心逻辑：
- **ROE 高且持续** → 公司能持续为股东创造价值
- **PB 相对低** → 当前市场没给到合理溢价，存在均值回归机会
- **排除陷阱** → 剔除金融、地产、ST、新股、高杠杆、亏损公司

---

## 用户怎么用（不需要懂代码）

用户只需说一句话即可触发，例如：

- "帮我跑一遍 PB-ROE 选股"
- "用 PB-ROE 模型选 A 股"
- "我想看现在有哪些低估值高 ROE 的股票"
- "PB-ROE 选股，宽松一点的阈值"
- "只看消费行业的 PB-ROE 选股"

---

## 执行步骤（Claude 收到请求后按此执行）

### 1. 检查环境

运行 `python -c "import akshare, pandas, jinja2"`，如果缺包则提示用户运行：
```bash
bash ~/.claude/skills/pb-roe-stock-selection/install.sh
```

### 2. 解析用户参数

从用户消息提取以下可选参数（都可省略，使用默认值）：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `min_roe` | 15 | 最低扣非 ROE(%) |
| `max_pb_pct` | 0.5 | PB 历史分位上限（0~1）|
| `max_debt` | 60 | 最高资产负债率(%) |
| `min_dividend` | 1 | 最低股息率(%) |
| `top_n` | 20 | 输出股票数量 |
| `industry` | 全部 | 限定行业（可选）|
| `mode` | strict | strict / loose / custom |

### 3. 运行选股脚本

```bash
python ~/.claude/skills/pb-roe-stock-selection/scripts/run_pb_roe.py \
  --min-roe 15 --top-n 20 --output ~/pb_roe_report.html
```

脚本会：
1. 用 akshare 拉取全 A 股基础信息、财务指标、最新行情
2. 应用筛选规则（基础过滤 → 核心条件 → 进阶条件）
3. 按 ROE/PB 排序取 Top N
4. 生成 HTML 报告（标题卡 + 行业分布饼图 + ROE-PB 散点图 + 详细表格 + 风险提示）

### 4. 展示结果

脚本完成后：
1. 在终端打印报告路径，例如 `/Users/xxx/pb_roe_report.html`
2. 用 `open <path>`（macOS）或 `xdg-open <path>`（Linux）自动在浏览器打开
3. 在对话中向用户**简要总结**：选出几只、行业分布、平均 ROE/PB，并给出报告路径链接

---

## 关键设计原则

1. **零门槛**：用户不需要 Tushare token、不需要数据库、不需要任何配置
2. **数据源稳定**：使用 akshare（开源免费）+ 本地缓存，避免接口限流
3. **失败可恢复**：单只股票数据获取失败时跳过并记录，不影响整体运行
4. **结果可解释**：HTML 报告标注每只股票"为什么入选"和"风险点"
5. **可重复运行**：每次跑完都覆盖同一个 HTML 文件（除非用户指定 `--output`）

---

## 默认筛选规则（与用户文档一致）

### 基础过滤
- 剔除 ST、*ST、退市股
- 剔除上市不满 1 年
- 剔除金融（银行/保险/证券）、房地产
- 剔除净资产为负
- 剔除最近一年净利润为负

### 核心条件
- 最新扣非 ROE(TTM) ≥ 15%
- 过去 3 年扣非 ROE 均 ≥ 12%
- 过去 5 年扣非 ROE 均值 ≥ 15%
- 最新 PB ≤ 行业 PB 中位数
- 最新 PB ≤ 自身历史 PB(5年) 50% 分位

### 进阶条件（提升胜率）
- 资产负债率 ≤ 60%
- 经营现金流/净利润 ≥ 0.8
- 股息率 ≥ 1%
- 近 3 年净利润复合增长率 ≥ 10%

### 排序
按 **ROE / PB** 降序，取前 N 只。

---

## HTML 报告内容

1. **顶部摘要卡**：选出股票数 / 平均 ROE / 平均 PB / 平均股息率 / 总市值
2. **筛选条件展示**：让用户知道用了哪些阈值
3. **行业分布饼图**（Chart.js）
4. **ROE-PB 散点图**（Chart.js，每只股票一个点）
5. **股票明细表**：代码 / 名称 / 行业 / ROE / PB / ROE-PB 比 / 股息率 / 市值 / 入选理由
6. **风险提示**：周期股、价值陷阱、财务造假等通用提醒
7. **方法论说明**（折叠区）

---

## 模块映射

```
pb-roe-stock-selection/
├── SKILL.md                    本文件
├── README.md                   用户安装/使用说明
├── install.sh                  一键安装脚本
├── requirements.txt            Python 依赖
└── scripts/
    ├── run_pb_roe.py           主入口（CLI）
    ├── data_source.py          akshare 数据获取 + 本地缓存
    ├── pb_roe_filter.py        筛选逻辑
    └── html_report.py          HTML 报告生成（Jinja2 + Chart.js）
```

---

## 安装

详见 [README.md](README.md)。一行命令：

```bash
git clone https://github.com/<user>/stock-selection-skill ~/.claude/skills/pb-roe-stock-selection && \
  bash ~/.claude/skills/pb-roe-stock-selection/install.sh
```

---

## 模型局限性（必须告知用户）

- 对周期性行业不友好（钢铁、煤炭、化工高景气时 ROE 高但已在高点）
- 容易踩"价值陷阱"（基本面恶化的低 PB 高 ROE 股票）
- 不考虑成长性（错过高成长但估值稍高的优质公司）
- ROE 可被财务造假虚增

报告底部会自动加上这些风险提示。
