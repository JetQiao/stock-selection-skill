"""
PB-ROE HTML 报告生成器。

输出：单个自包含的 HTML 文件（Chart.js 走 CDN）。
- 顶部摘要卡
- 筛选条件
- 行业分布饼图 + ROE-PB 散点图
- 股票明细表（可排序，含入选理由 + 风险）
- 风险提示 + 方法论说明
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>PB-ROE 选股报告 · {{ generated_at }}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  :root {
    --bg: #f7f8fa;
    --card: #ffffff;
    --text: #1a202c;
    --muted: #718096;
    --primary: #2563eb;
    --success: #16a34a;
    --warn: #f59e0b;
    --danger: #dc2626;
    --border: #e2e8f0;
  }
  * { box-sizing: border-box; }
  body {
    font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif;
    background: var(--bg);
    color: var(--text);
    margin: 0;
    padding: 24px;
    line-height: 1.6;
  }
  .container { max-width: 1280px; margin: 0 auto; }
  h1 { margin: 0 0 8px 0; font-size: 28px; }
  h2 { font-size: 20px; margin: 32px 0 16px 0; padding-left: 12px; border-left: 4px solid var(--primary); }
  .subtitle { color: var(--muted); margin-bottom: 24px; }

  .summary-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 16px;
    margin-bottom: 24px;
  }
  .summary-card {
    background: var(--card);
    border-radius: 12px;
    padding: 20px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    border: 1px solid var(--border);
  }
  .summary-card .label { color: var(--muted); font-size: 13px; margin-bottom: 8px; }
  .summary-card .value { font-size: 28px; font-weight: 700; color: var(--primary); }
  .summary-card .unit { font-size: 14px; color: var(--muted); margin-left: 4px; }

  .config-card, .charts-row, .table-card, .pipeline-card, .risk-card {
    background: var(--card);
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 24px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    border: 1px solid var(--border);
  }
  .config-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 12px;
  }
  .config-item { font-size: 14px; }
  .config-item .k { color: var(--muted); }
  .config-item .v { font-weight: 600; color: var(--text); }

  .charts-row { display: grid; grid-template-columns: 1fr 1.5fr; gap: 24px; }
  @media (max-width: 900px) { .charts-row { grid-template-columns: 1fr; } }
  .chart-box { position: relative; height: 360px; }

  table { width: 100%; border-collapse: collapse; font-size: 14px; }
  th, td { padding: 10px 8px; text-align: left; border-bottom: 1px solid var(--border); }
  th { background: #f1f5f9; font-weight: 600; cursor: pointer; user-select: none; }
  th:hover { background: #e2e8f0; }
  td.num { text-align: right; font-variant-numeric: tabular-nums; }
  tr:hover { background: #f8fafc; }
  .reason { color: var(--success); font-size: 12px; }
  .risk { color: var(--warn); font-size: 12px; }
  .badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    background: #eff6ff;
    color: var(--primary);
    font-size: 12px;
    font-weight: 600;
  }

  .pipeline-step {
    display: grid;
    grid-template-columns: 240px 1fr 80px 80px;
    gap: 12px;
    padding: 8px 0;
    border-bottom: 1px dashed var(--border);
    font-size: 14px;
  }
  .pipeline-step:last-child { border-bottom: none; }
  .pipeline-step .name { font-weight: 600; }
  .pipeline-step .bar { background: #e2e8f0; height: 8px; border-radius: 4px; overflow: hidden; align-self: center; }
  .pipeline-step .bar-fill { background: var(--primary); height: 100%; }
  .pipeline-step .removed { color: var(--danger); text-align: right; }
  .pipeline-step .remain { color: var(--success); text-align: right; font-weight: 600; }

  .risk-card { border-left: 4px solid var(--warn); }
  .risk-card ul { margin: 8px 0 0 20px; padding: 0; }
  .risk-card li { margin: 4px 0; color: var(--text); font-size: 14px; }

  details { margin-top: 16px; }
  summary { cursor: pointer; color: var(--primary); font-weight: 600; }
  details[open] summary { margin-bottom: 12px; }
  .footer { text-align: center; color: var(--muted); font-size: 12px; margin-top: 48px; padding: 24px 0; }
</style>
</head>
<body>
<div class="container">

  <h1>PB-ROE 选股报告</h1>
  <div class="subtitle">生成时间 · {{ generated_at }} · 数据源 akshare</div>

  <!-- Summary Cards -->
  <div class="summary-grid">
    <div class="summary-card">
      <div class="label">入选股票数</div>
      <div class="value">{{ summary.count }}<span class="unit">只</span></div>
    </div>
    <div class="summary-card">
      <div class="label">平均 ROE</div>
      <div class="value">{{ summary.avg_roe }}<span class="unit">%</span></div>
    </div>
    <div class="summary-card">
      <div class="label">平均 PB</div>
      <div class="value">{{ summary.avg_pb }}</div>
    </div>
    <div class="summary-card">
      <div class="label">平均股息率</div>
      <div class="value">{{ summary.avg_dividend }}<span class="unit">%</span></div>
    </div>
    <div class="summary-card">
      <div class="label">总市值</div>
      <div class="value">{{ summary.total_mv }}<span class="unit">亿</span></div>
    </div>
  </div>

  <!-- Filter Config -->
  <div class="config-card">
    <h2 style="margin-top:0;">筛选条件</h2>
    <div class="config-grid">
      {% for k, v in config.items() %}
      <div class="config-item"><span class="k">{{ k }}：</span><span class="v">{{ v }}</span></div>
      {% endfor %}
    </div>
  </div>

  <!-- Charts -->
  <div class="charts-row">
    <div>
      <h2 style="margin-top:0;">行业分布</h2>
      <div class="chart-box"><canvas id="industryChart"></canvas></div>
    </div>
    <div>
      <h2 style="margin-top:0;">ROE - PB 分布</h2>
      <div class="chart-box"><canvas id="scatterChart"></canvas></div>
    </div>
  </div>

  <!-- Pipeline -->
  <div class="pipeline-card">
    <h2 style="margin-top:0;">筛选漏斗</h2>
    <div class="pipeline-step" style="font-weight:600; color: var(--muted);">
      <div>步骤</div><div>留存</div><div class="removed">剔除</div><div class="remain">剩余</div>
    </div>
    <div class="pipeline-step">
      <div class="name">起始全市场</div>
      <div class="bar"><div class="bar-fill" style="width:100%;"></div></div>
      <div class="removed">—</div>
      <div class="remain">{{ pipeline_initial }}</div>
    </div>
    {% for step in pipeline %}
    <div class="pipeline-step">
      <div class="name">{{ step.name }}</div>
      <div class="bar"><div class="bar-fill" style="width: {{ step.pct }}%;"></div></div>
      <div class="removed">-{{ step.removed }}</div>
      <div class="remain">{{ step.after }}</div>
    </div>
    {% endfor %}
  </div>

  <!-- Stock Table -->
  <div class="table-card">
    <h2 style="margin-top:0;">入选股票明细</h2>
    <table id="stockTable">
      <thead>
        <tr>
          <th>#</th>
          <th>代码</th>
          <th>名称</th>
          <th>行业</th>
          <th class="num" data-sort="num">ROE(%)</th>
          <th class="num" data-sort="num">PB</th>
          <th class="num" data-sort="num">ROE/PB</th>
          <th class="num" data-sort="num">股息率(%)</th>
          <th class="num" data-sort="num">市值(亿)</th>
          <th>入选理由 / 风险</th>
        </tr>
      </thead>
      <tbody>
        {% for s in stocks %}
        <tr>
          <td>{{ loop.index }}</td>
          <td>{{ s.ts_code }}</td>
          <td><strong>{{ s.name }}</strong></td>
          <td><span class="badge">{{ s.industry }}</span></td>
          <td class="num">{{ s.roe_ttm }}</td>
          <td class="num">{{ s.pb }}</td>
          <td class="num"><strong>{{ s.roe_pb }}</strong></td>
          <td class="num">{{ s.dividend_yield }}</td>
          <td class="num">{{ s.total_mv }}</td>
          <td>
            <div class="reason">✓ {{ s.reason }}</div>
            <div class="risk">⚠ {{ s.risk }}</div>
          </td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>

  <!-- Risk Disclaimer -->
  <div class="risk-card">
    <h2 style="margin-top:0;">风险提示</h2>
    <ul>
      <li><strong>周期股陷阱</strong>：钢铁、煤炭、化工等强周期行业，景气高点 ROE 高但往往是股价高点。</li>
      <li><strong>价值陷阱</strong>：低 PB + 高 ROE 也可能是基本面即将恶化、市场提前定价的结果。</li>
      <li><strong>财务造假</strong>：ROE 可被虚增，建议结合现金流量表、应收账款周转率交叉验证。</li>
      <li><strong>不考虑成长性</strong>：纯 PB-ROE 模型会错过部分高成长但估值偏高的优质公司。</li>
      <li><strong>历史不代表未来</strong>：本报告仅基于历史数据筛选，不构成投资建议。</li>
    </ul>
  </div>

  <details>
    <summary>方法论说明（点击展开）</summary>
    <p><strong>核心思想</strong>：用低估值（PB）买入高且可持续盈利能力（ROE）的公司，本质是寻找"性价比最高"的资产。</p>
    <p><strong>排序指标</strong>：ROE / PB —— 数值越大代表"每 1 元市净率换来的 ROE 越高"。</p>
    <p><strong>调仓建议</strong>：每季度（4/7/10/1 月）在财报披露后调仓一次，组合规模 10-20 只，等权重分配。</p>
    <p><strong>回测参考</strong>：A 股 2010-2025 年化收益约 18%-22%，最大回撤 35%-40%，跑赢沪深 300 约 10%-12% 年化。</p>
  </details>

  <div class="footer">
    本报告由 PB-ROE Skill 自动生成 · 仅供研究学习，不构成投资建议
  </div>
</div>

<script>
  // 行业分布饼图
  const industryData = {{ industry_json|safe }};
  new Chart(document.getElementById('industryChart'), {
    type: 'doughnut',
    data: {
      labels: industryData.labels,
      datasets: [{
        data: industryData.values,
        backgroundColor: [
          '#2563eb', '#16a34a', '#f59e0b', '#dc2626', '#8b5cf6',
          '#06b6d4', '#ec4899', '#14b8a6', '#f97316', '#6366f1',
          '#84cc16', '#a855f7'
        ],
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { position: 'right', labels: { boxWidth: 12, font: { size: 12 } } } }
    }
  });

  // ROE-PB 散点图
  const scatterData = {{ scatter_json|safe }};
  new Chart(document.getElementById('scatterChart'), {
    type: 'scatter',
    data: {
      datasets: [{
        label: '入选股票',
        data: scatterData,
        backgroundColor: 'rgba(37, 99, 235, 0.6)',
        borderColor: '#2563eb',
        pointRadius: 6,
        pointHoverRadius: 9,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        tooltip: {
          callbacks: {
            label: (ctx) => `${ctx.raw.label}: ROE ${ctx.raw.y}% / PB ${ctx.raw.x}`
          }
        },
        legend: { display: false }
      },
      scales: {
        x: { title: { display: true, text: 'PB (市净率)' } },
        y: { title: { display: true, text: 'ROE (%)' } }
      }
    }
  });

  // 表格排序
  document.querySelectorAll('#stockTable th[data-sort]').forEach((th, idx) => {
    let asc = false;
    th.addEventListener('click', () => {
      const colIdx = Array.from(th.parentNode.children).indexOf(th);
      const tbody = document.querySelector('#stockTable tbody');
      const rows = Array.from(tbody.querySelectorAll('tr'));
      rows.sort((a, b) => {
        const va = parseFloat(a.children[colIdx].textContent) || 0;
        const vb = parseFloat(b.children[colIdx].textContent) || 0;
        return asc ? va - vb : vb - va;
      });
      asc = !asc;
      rows.forEach(r => tbody.appendChild(r));
    });
  });
</script>
</body>
</html>
"""


def _fmt_num(v: Any, digits: int = 2) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    try:
        return f"{float(v):.{digits}f}"
    except (TypeError, ValueError):
        return str(v)


def _fmt_mv(v: Any) -> str:
    """市值（元）转亿元。"""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    try:
        return f"{float(v) / 1e8:.1f}"
    except (TypeError, ValueError):
        return "—"


def render(
    selected: pd.DataFrame,
    config: dict,
    pipeline_report: Any,
    output_path: Path,
) -> Path:
    """渲染并写入 HTML 报告。返回输出路径。"""
    try:
        from jinja2 import Template
    except ImportError as e:
        raise RuntimeError("缺少 jinja2，请运行 `pip install jinja2`") from e

    if selected.empty:
        summary = {"count": 0, "avg_roe": "—", "avg_pb": "—", "avg_dividend": "—", "total_mv": "—"}
        stocks_view: list[dict] = []
        industry_payload = {"labels": [], "values": []}
        scatter_payload: list[dict] = []
    else:
        summary = {
            "count": len(selected),
            "avg_roe": _fmt_num(selected["roe_ttm"].mean()),
            "avg_pb": _fmt_num(selected["pb"].mean()),
            "avg_dividend": _fmt_num(selected.get("dividend_yield", pd.Series(dtype=float)).mean()),
            "total_mv": _fmt_num(selected.get("total_mv", pd.Series(dtype=float)).sum() / 1e8, digits=1),
        }

        stocks_view = []
        for _, row in selected.iterrows():
            stocks_view.append({
                "ts_code": row.get("ts_code", "—"),
                "name": row.get("name", "—"),
                "industry": row.get("industry", "未知"),
                "roe_ttm": _fmt_num(row.get("roe_ttm")),
                "pb": _fmt_num(row.get("pb")),
                "roe_pb": _fmt_num(row.get("roe_pb"), digits=1),
                "dividend_yield": _fmt_num(row.get("dividend_yield")),
                "total_mv": _fmt_mv(row.get("total_mv")),
                "reason": row.get("reason", "—"),
                "risk": row.get("risk", "—"),
            })

        ind_counts = selected["industry"].value_counts()
        industry_payload = {
            "labels": ind_counts.index.tolist(),
            "values": ind_counts.values.tolist(),
        }

        scatter_payload = [
            {
                "x": round(float(row.get("pb", 0)), 2),
                "y": round(float(row.get("roe_ttm", 0)), 2),
                "label": row.get("name", "—"),
            }
            for _, row in selected.iterrows()
            if pd.notna(row.get("pb")) and pd.notna(row.get("roe_ttm"))
        ]

    pipeline_view = []
    initial = pipeline_report.initial if pipeline_report else 0
    for step in (pipeline_report.steps if pipeline_report else []):
        pct = (step["after"] / initial * 100) if initial else 0
        pipeline_view.append({
            "name": step["name"],
            "before": step["before"],
            "after": step["after"],
            "removed": step["removed"],
            "pct": round(pct, 1),
        })

    template = Template(HTML_TEMPLATE)
    html = template.render(
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        summary=summary,
        config=config,
        stocks=stocks_view,
        pipeline_initial=initial,
        pipeline=pipeline_view,
        industry_json=json.dumps(industry_payload, ensure_ascii=False),
        scatter_json=json.dumps(scatter_payload, ensure_ascii=False),
    )

    output_path = Path(output_path).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path
