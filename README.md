# PB-ROE 选股 Skill

一个开箱即用的 A 股 **PB-ROE 价值选股** Claude Code Skill。
- ✅ **零代码门槛**：装完直接跟 Claude 说"帮我跑 PB-ROE 选股"即可
- ✅ **数据免费**：基于 akshare，无需 Tushare token、无需付费数据源
- ✅ **可视化 HTML 报告**：摘要卡 + 行业饼图 + ROE-PB 散点图 + 明细表 + 风险提示
- ✅ **结果可解释**：每只股票都标注"为什么入选"和"风险点"

---

## 一、快速安装（30 秒）

### 方法 A：克隆 + 一键安装（推荐）

```bash
git clone <本仓库地址> ~/.claude/skills/pb-roe-stock-selection
bash ~/.claude/skills/pb-roe-stock-selection/install.sh
```

### 方法 B：本地已有代码

```bash
cd <仓库目录>
bash install.sh
```

安装脚本会自动：
1. 检查 Python 3
2. 复制到 `~/.claude/skills/pb-roe-stock-selection/`
3. 安装 Python 依赖（akshare、pandas、jinja2 等）
4. 验证安装

> **首次安装** akshare 包较大（约 50MB+），需要 1-3 分钟。

---

## 二、怎么用（不需要写代码）

### 在 Claude Code 中直接说话

打开 Claude Code，对它说任意一句：

- "帮我跑一遍 PB-ROE 选股"
- "用 PB-ROE 模型选 A 股"
- "我想看现在有哪些低估值高 ROE 的股票"
- "PB-ROE 选股，宽松一点的阈值"
- "只看食品饮料行业的 PB-ROE 选股"
- "PB-ROE 选股，给我前 10 只"

Claude 会自动调用此 Skill，跑完后：
1. 终端显示进度
2. 浏览器**自动打开** HTML 报告
3. Claude 在对话里给一段简明总结

### 命令行直接运行

```bash
python3 ~/.claude/skills/pb-roe-stock-selection/scripts/run_pb_roe.py
```

---

## 三、常用参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `--mode` | strict / loose（宽松版阈值） | `--mode loose` |
| `--min-roe` | 最低 ROE(TTM)（%） | `--min-roe 12` |
| `--max-debt` | 最高资产负债率（%） | `--max-debt 50` |
| `--min-dividend` | 最低股息率（%） | `--min-dividend 2` |
| `--top-n` | 输出股票数量 | `--top-n 10` |
| `--industry` | 限定行业（模糊匹配） | `--industry 食品` |
| `--output` | HTML 输出路径 | `--output ~/my.html` |
| `--skip-history` | 跳过历史 ROE 检查（更快） | `--skip-history` |
| `--clear-cache` | 清空缓存后重跑 | `--clear-cache` |
| `--no-open` | 跑完不自动打开浏览器 | `--no-open` |

---

## 四、HTML 报告长什么样

报告包含：

1. **顶部摘要卡** —— 入选数 / 平均 ROE / 平均 PB / 平均股息率 / 总市值
2. **筛选条件展示** —— 这次用了哪些阈值，一目了然
3. **行业分布饼图** —— 入选股票的行业分散度
4. **ROE-PB 散点图** —— 每只股票一个点，悬停看详情
5. **筛选漏斗** —— 从全市场到入选的每一步剔除多少
6. **股票明细表** —— 代码 / 名称 / 行业 / ROE / PB / ROE-PB 比 / 股息率 / 市值
   - 每行下方标注 ✓ 入选理由 + ⚠ 风险点
   - 表头可点击排序
7. **风险提示** —— 周期股陷阱、价值陷阱、财务造假等通用风险
8. **方法论说明**（可折叠）

---

## 五、模型逻辑（参考）

### 基础过滤
- 剔除 ST、*ST、退市股
- 剔除上市不满 1 年
- 剔除金融（银行/保险/证券）、房地产
- 剔除净资产为负、亏损公司

### 核心条件（strict 模式）
- 最新扣非 ROE(TTM) ≥ **15%**
- 过去 3 年扣非 ROE 均 ≥ **12%**
- 过去 5 年扣非 ROE 均值 ≥ **15%**
- 最新 PB ≤ 行业 PB 中位数

### 进阶条件
- 资产负债率 ≤ **60%**
- 经营现金流/净利润 ≥ **0.8**
- 股息率 ≥ **1%**
- 近 3 年净利润复合增长率 ≥ **10%**

### 排序
按 **ROE / PB** 降序，取前 N 只。

> 详细设计思路见 [SKILL.md](SKILL.md)。

---

## 六、常见问题

**Q：报告显示"入选 0 只"怎么办？**
A：默认 strict 模式比较严格，可加 `--mode loose` 试宽松版；或检查是否数据缓存过期，加 `--clear-cache`。

**Q：跑得很慢怎么办？**
A：默认会检查每只股票的 5 年历史 ROE，加 `--skip-history` 可跳过这一步，速度提升 5-10 倍。

**Q：数据是实时的吗？**
A：行情数据是当日最新，财务数据来自最近一期定期报告。本地缓存 12 小时，加 `--clear-cache` 强制刷新。

**Q：能否回测？**
A：当前版本只做"实时选股"。回测功能在路线图里。

**Q：可靠吗？能直接拿来买吗？**
A：**不可以**。本工具仅做规则化筛选，不构成投资建议。报告底部的"风险提示"务必通读。

---

## 七、目录结构

```
pb-roe-stock-selection/
├── SKILL.md              Skill 元信息（被 Claude 识别）
├── README.md             本文件
├── install.sh            一键安装脚本
├── requirements.txt      Python 依赖
└── scripts/
    ├── __init__.py
    ├── run_pb_roe.py     主入口（CLI）
    ├── data_source.py    akshare 数据获取 + 本地缓存
    ├── pb_roe_filter.py  筛选逻辑
    └── html_report.py    HTML 报告生成
```

---

## 八、卸载

```bash
rm -rf ~/.claude/skills/pb-roe-stock-selection
rm -rf ~/.cache/pb_roe_skill   # 本地数据缓存
```

---

## License

MIT
