import json
from typing import Any, Dict


class DashboardCodeService:
    @staticmethod
    def generate_chartjs_dashboard_html(*, dataset_id: int, dataset_name: str, charts: list[Dict[str, Any]]) -> str:
        """
        Generate a standalone HTML dashboard that renders charts via the existing
        DataLens endpoint: /dataset/<dataset_id>/auto_chart_data?chart_id=...

        This keeps the generated code simple and avoids introducing new Python
        visualization dependencies.
        """
        charts_json = json.dumps(charts, ensure_ascii=False)

        # Simple layout: one card per chart (no CSS grid positioning to keep it portable).
        chart_cards = "\n".join(
            [
                f"""
                <div class="chart-card" data-chart-id="{c.get('id','')}">
                  <div class="chart-card__header">
                    <div class="chart-title">{c.get('title','Chart')}</div>
                    <button class="btn" onclick="refreshChart('{c.get('id','')}')">Refresh</button>
                  </div>
                  <div class="chart-card__body" id="chart-{c.get('id','')}">
                    <div class="loading">Loading...</div>
                  </div>
                </div>
                """.strip()
                for c in charts
            ]
        )

        return f"""<!doctype html>
<html lang="fr">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Auto Dashboard - {dataset_name}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
      body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin: 0; background:#f1f5f9; color:#0f172a; }}
      .wrap {{ max-width: 1200px; margin: 0 auto; padding: 24px; }}
      .header {{ display:flex; justify-content:space-between; align-items:flex-start; gap:16px; }}
      .title h1 {{ margin:0; font-size:20px; }}
      .title p {{ margin:6px 0 0; color:#475569; font-size:13px; }}
      .note {{ background:#fff; border:1px solid #e2e8f0; border-radius:12px; padding:12px 14px; font-size:13px; color:#334155; }}
      .grid {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 14px; margin-top: 16px; }}
      .chart-card {{ background:#fff; border:1px solid #e2e8f0; border-radius:12px; overflow:hidden; }}
      .chart-card__header {{ display:flex; justify-content:space-between; align-items:center; padding:12px 14px; border-bottom:1px solid #e2e8f0; }}
      .chart-title {{ font-weight:600; font-size:13px; }}
      .chart-card__body {{ height: 260px; padding: 10px 12px; }}
      .loading {{ color:#64748b; font-size:13px; }}
      .btn {{ background:#e2e8f0; border:1px solid #cbd5e1; padding:6px 10px; border-radius:8px; cursor:pointer; }}
      .btn:hover {{ background:#cbd5e1; }}
      canvas {{ width: 100% !important; height: 100% !important; }}
      .error {{ color:#b91c1c; font-size:13px; }}
      .summary {{ font-size:13px; color:#334155; display:grid; grid-template-columns: repeat(2, 1fr); gap: 8px; }}
      .summary div {{ background:#f8fafc; border:1px solid #e2e8f0; border-radius:10px; padding:8px; }}
      .summary span {{ color:#64748b; }}
    </style>
  </head>
  <body>
    <div class="wrap">
      <div class="header">
        <div class="title">
          <h1>Auto Dashboard - {dataset_name}</h1>
          <p>Dataset id: {dataset_id}</p>
        </div>
        <div class="note">
          Ce dashboard utilise ton serveur DataLens pour charger les données.<br/>
          Il appelle <code>/dataset/{dataset_id}/auto_chart_data?chart_id=...</code>
        </div>
      </div>

      <div class="grid" id="grid">
        {chart_cards}
      </div>
    </div>

    <script>
      const datasetId = {dataset_id};
      const charts = {charts_json};
      const chartInstances = {{}};

      document.addEventListener('DOMContentLoaded', () => {{
        charts.forEach(c => loadChart(c.id));
      }});

      function refreshChart(chartId) {{
        loadChart(chartId);
      }}

      function loadChart(chartId) {{
        const el = document.getElementById(`chart-${{chartId}}`);
        const chart = charts.find(c => c.id === chartId);
        if (!el || !chart) return;

        el.innerHTML = '<div class="loading">Loading...</div>';

        fetch(`/dataset/${{datasetId}}/auto_chart_data?chart_id=${{encodeURIComponent(chartId)}}`)
          .then(r => r.json())
          .then(data => {{
            if (data.error) {{
              el.innerHTML = `<div class="error">Error: ${{data.error}}</div>`;
              return;
            }}
            renderChart(chart, el, data);
          }})
          .catch(err => {{
            el.innerHTML = `<div class="error">Failed to load chart: ${{err.message}}</div>`;
          }});
      }}

      function renderChart(chart, el, data) {{
        const chartId = chart.id;
        if (chartInstances[chartId]) {{
          chartInstances[chartId].destroy();
          delete chartInstances[chartId];
        }}

        if (chart.type === 'summary') {{
          el.innerHTML = `
            <div class="summary">
              <div><span>Total rows</span><br/><strong>${{data.total_rows}}</strong></div>
              <div><span>Total columns</span><br/><strong>${{data.total_columns}}</strong></div>
              <div><span>Numeric</span><br/><strong>${{data.numeric_columns}}</strong></div>
              <div><span>Categorical</span><br/><strong>${{data.categorical_columns}}</strong></div>
            </div>
          `;
          return;
        }}

        if (chart.type === 'heatmap' || chart.type === 'boxplot') {{
          // Keep it simple in exported code: show JSON.
          el.innerHTML = `<pre style="white-space:pre-wrap; font-size:12px; margin:0;">${{JSON.stringify(data, null, 2)}}</pre>`;
          return;
        }}

        el.innerHTML = '<canvas></canvas>';
        const ctx = el.querySelector('canvas').getContext('2d');

        const cfg = {{
          type: chart.type === 'histogram' ? 'bar' : chart.type,
          data: {{}},
          options: {{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{
              legend: {{ display: chart.type === 'pie' }}
            }}
          }}
        }};

        if (chart.type === 'scatter') {{
          cfg.data = {{ datasets: data.datasets }};
          cfg.options.scales = {{
            x: {{ type: 'linear', position: 'bottom' }},
            y: {{ beginAtZero: true }}
          }};
        }} else if (chart.type === 'pie') {{
          cfg.data = {{
            labels: data.labels,
            datasets: [{{
              data: data.data,
              backgroundColor: ['#FF6384','#36A2EB','#FFCE56','#4BC0C0','#9966FF','#FF9F40','#C9CBCF']
            }}]
          }};
        }} else {{
          cfg.data = {{
            labels: data.labels,
            datasets: [{{
              label: 'Data',
              data: data.data,
              backgroundColor: 'rgba(54, 162, 235, 0.6)',
              borderColor: 'rgba(54, 162, 235, 1)',
              borderWidth: 2
            }}]
          }};
          if (chart.type !== 'histogram') {{
            cfg.options.scales = {{ y: {{ beginAtZero: true }} }};
          }}
        }}

        chartInstances[chartId] = new Chart(ctx, cfg);
      }}
    </script>
  </body>
</html>"""

