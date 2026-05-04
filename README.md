# PB-ROE 选股 Skill

A 股 PB-ROE 价值选股 Claude Code Skill。装完跟 Claude 说一句话，自动出可视化 HTML 报告。

- **零代码**：一行 `npx` 安装，对话触发
- **数据免费**：基于 akshare，无需 token
- **结果可解释**：每只股票标注入选理由 + 风险点

---

> ## ⚠️ 必读：只能在本地 Claude Code 跑
>
> 本 skill 只能在你电脑上的 **Claude Code（CLI / Desktop / IDE 扩展）** 中运行，**不能在 claude.ai 网页或托管沙箱中运行**：
> - akshare 要直连 Eastmoney / 新浪 / 雪球，托管沙箱网络白名单只放行 npm/pypi/github，会被 403 拦截
> - 沙箱不持久化文件，装完即丢
>
> 请在本机装 [Claude Code](https://claude.com/claude-code) 之后再用本 skill。

---

## 安装

```bash
npx -y github:JetQiao/stock-selection-skill install
```

锁版本：`npx -y github:JetQiao/stock-selection-skill#v0.1.1 install`

全局安装（`pb-roe` 命令永驻）：`npm install -g github:JetQiao/stock-selection-skill`

> 前置：Python 3.9+ 和 Node.js 14+。首次会装 akshare（~50MB），需 1-3 分钟。

---

## 使用

**对话触发**（在 Claude Code 中）：

> "帮我跑 PB-ROE 选股"
> "PB-ROE 选股，宽松一点"
> "只看食品饮料行业的 PB-ROE 选股"

**命令行**：

```bash
pb-roe                              # 默认 strict 模式
pb-roe --mode loose --top-n 10
pb-roe --industry 食品
pb-roe --help
```

| 参数 | 说明 | 默认 |
|------|------|------|
| `--mode` | strict / loose | strict |
| `--min-roe` | 最低 ROE(TTM) % | 15 (strict) / 12 (loose) |
| `--max-debt` | 最高资产负债率 % | 60 |
| `--min-dividend` | 最低股息率 % | 1 (strict) / 0.5 (loose) |
| `--top-n` | 输出股票数量 | 20 |
| `--industry` | 行业模糊匹配 | 全部 |
| `--output` | HTML 输出路径 | `~/pb_roe_report.html` |
| `--skip-history` | 跳过 5 年历史 ROE 检查（快 5-10 倍） | off |
| `--clear-cache` | 清空缓存重跑 | off |
| `--no-open` | 跑完不自动打开浏览器 | off |

---

## 模型逻辑

**基础过滤**：剔除 ST/退市、上市不满 1 年、金融/地产、净资产为负、亏损公司。

**核心条件（strict）**：
- 扣非 ROE(TTM) ≥ 15%；过去 3 年均 ≥ 12%；5 年均值 ≥ 15%
- PB ≤ 行业 PB 中位数

**进阶条件**：负债率 ≤ 60%、经营现金流/净利润 ≥ 0.8、股息率 ≥ 1%、3 年净利润复合增速 ≥ 10%

**排序**：按 `ROE / PB` 降序取前 N 只。

详细设计思路见 [SKILL.md](SKILL.md)。

---

## 常见问题

**入选 0 只？** 加 `--mode loose`，或 `--clear-cache` 排除缓存过期。

**跑得很慢？** 加 `--skip-history`（默认会拉每只股票的 5 年历史 ROE）。

**数据多新？** 行情当日最新，财务取最近一期定期报告。本地缓存 12 小时，`--clear-cache` 强制刷新。

**能直接拿来买吗？** **不能**。仅规则化筛选，不构成投资建议。务必读报告底部的风险提示。

---

## 卸载

```bash
npx -y github:JetQiao/stock-selection-skill uninstall   # 清 Skill + 缓存
npm uninstall -g pb-roe-skill                           # 仅全局安装时
```

---

MIT License
