from __future__ import annotations

import html
import json
from pathlib import Path

from a64forge.schemas import HardwareInfo, OptimizationResult


def _metric(value: float | None, unit: str = "") -> str:
    return "Not measured yet" if value is None else f"{value:,.2f}{unit}"


def _improvement(before: float | None, after: float | None, lower: bool) -> str:
    if before is None or after is None or before == 0:
        return "Not measured yet"
    value = ((before - after) / before if lower else (after - before) / before) * 100
    return f"{value:+.1f}%"


def generate_report(
    result: OptimizationResult,
    hardware: HardwareInfo,
    destination: Path,
) -> list[Path]:
    report_dir = destination / result.run_id
    report_dir.mkdir(parents=True, exist_ok=True)
    baseline = {item.stage_id: item for item in result.baseline}
    rows = []
    experiments = []
    for selection in result.selections:
        before = baseline.get(selection.stage_id)
        after = selection.selected
        rows.append(
            "<tr>"
            f"<th>{html.escape(selection.stage_id)}</th>"
            f"<td>{html.escape(before.model if before else 'Not measured yet')}</td>"
            f"<td>{html.escape(after.model)} / {html.escape(after.quantization)}</td>"
            f"<td>{_metric(before.median_latency_ms if before else None, ' ms')}</td>"
            f"<td>{_metric(after.median_latency_ms, ' ms')}</td>"
            f"<td>{_improvement(before.median_latency_ms if before else None, after.median_latency_ms, True)}</td>"
            f"<td>{_metric(after.quality_score)}</td>"
            "</tr>"
        )
        experiments.append(
            "<article class='decision'>"
            f"<h3>{html.escape(selection.stage_id)}</h3>"
            f"<p class='selection'>{html.escape(after.model)} · {html.escape(after.quantization)} · "
            f"{after.threads} threads · batch {after.batch_size}</p>"
            f"<ul>{''.join(f'<li>{html.escape(reason)}</li>' for reason in selection.explanation)}</ul>"
            "</article>"
        )
    for rejection in result.rejections:
        before = baseline.get(rejection.stage_id)
        best = rejection.best_candidate
        rows.append(
            "<tr>"
            f"<th>{html.escape(rejection.stage_id)}</th>"
            f"<td>{html.escape(before.model if before else 'Not measured yet')}</td>"
            "<td>Not deployable</td>"
            f"<td>{_metric(before.median_latency_ms if before else None, ' ms')}</td>"
            f"<td>{_metric(best.median_latency_ms if best else None, ' ms')}</td>"
            "<td>Quality gate failed</td>"
            f"<td>{_metric(best.quality_score if best else None)}</td>"
            "</tr>"
        )
        experiments.append(
            "<article class='decision rejected'>"
            f"<h3>{html.escape(rejection.stage_id)}</h3>"
            "<p class='selection'>No route compiled</p>"
            f"<p>{html.escape(rejection.reason)}</p>"
            "</article>"
        )
    label_class = "verified" if result.run_label.value == "VERIFIED ARM64 RUN" else "unverified"
    status_class = "verified" if result.deployable else "unverified"
    status_summary = (
        "Every workflow stage has a candidate that passed its quality gate."
        if result.deployable
        else "Deployment was withheld because one or more stages had no qualifying candidate."
    )
    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>A64Forge report · {html.escape(result.run_id)}</title>
<style>
:root{{--paper:#0d1210;--surface:#151c18;--ink:#edf5ef;--muted:#9eb0a4;--rule:#33453a;--accent:#85e695;--warn:#e8c777;}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--paper);color:var(--ink);font:16px/1.55 ui-sans-serif,system-ui,sans-serif}}
main{{width:min(1180px,calc(100% - 32px));margin:auto;padding:56px 0 80px}} h1,h2,h3{{line-height:1.1;margin:0}} h1{{font-size:clamp(2.4rem,7vw,5rem);letter-spacing:-.05em;max-width:12ch}}
.meta{{color:var(--muted);font-family:ui-monospace,monospace}} .label{{display:inline-block;margin:24px 0;padding:7px 10px;border:1px solid var(--rule)}}
.verified{{color:var(--accent)}} .unverified{{color:var(--warn)}} section{{margin-top:64px}} table{{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums}}
th,td{{border-bottom:1px solid var(--rule);padding:14px 10px;text-align:left;vertical-align:top}} th{{font-weight:600}} .decisions{{display:grid;grid-template-columns:1.35fr .9fr;gap:24px}}
.decision{{border-top:1px solid var(--rule);padding-top:18px}} .selection{{color:var(--accent);font-family:ui-monospace,monospace}} ul{{padding-left:20px;color:var(--muted)}}
.hardware{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:1px;background:var(--rule)}} .hardware div{{background:var(--surface);padding:18px}}
.hardware b{{display:block;font-size:1.2rem}} .hardware span{{color:var(--muted)}} @media(max-width:760px){{.decisions{{grid-template-columns:1fr}}.table-wrap{{overflow:auto}}}}
</style></head><body><main>
<p class="meta">A64FORGE / {html.escape(result.target.upper())} / {result.timestamp.isoformat()}</p>
<h1>Measured workflow compilation.</h1>
<p class="label {label_class}">{html.escape(result.run_label.value)}</p>
<p class="label {status_class}">{html.escape(result.status.value)}</p>
<p>{html.escape(status_summary)}</p>
<p>Run <code>{html.escape(result.run_id)}</code> · commit <code>{html.escape(result.baseline[0].git_commit if result.baseline else 'unknown')}</code></p>
<section><h2>Arm system evidence</h2><div class="hardware">
<div><span>Architecture</span><b>{html.escape(hardware.architecture)}</b></div><div><span>CPU</span><b>{html.escape(hardware.cpu_model)}</b></div>
<div><span>Cores</span><b>{hardware.logical_cores}</b></div><div><span>Memory</span><b>{hardware.memory_gb:.2f} GB</b></div>
<div><span>NEON</span><b>{hardware.neon.value}</b></div><div><span>SVE</span><b>{hardware.sve.value}</b></div>
<div><span>MATMUL_INT8</span><b>{hardware.matmul_int8.value}</b></div><div><span>Performix</span><b>{'available' if hardware.performix else 'unavailable'}</b></div>
</div></section>
<section><h2>Before vs compiled routing</h2><div class="table-wrap"><table><thead><tr><th>Stage</th><th>Baseline</th><th>A64Forge</th><th>Baseline median</th><th>Compiled median</th><th>Change</th><th>Quality</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div></section>
<section><h2>Optimization decisions</h2><div class="decisions">{''.join(experiments)}</div></section>
<section><h2>Method</h2><p>All candidates used the stage dataset hash stored in results.json. Each record stores warm-up count, measured count, model hash, host, architecture, configuration, median and p95 latency, process resource observations, and quality. Missing fields remain “Not measured yet.” Development fixtures are never verified.</p></section>
</main></body></html>"""
    report_path = report_dir / "report.html"
    results_path = report_dir / "results.json"
    manifest_path = report_dir / "manifest.json"
    report_path.write_text(document, encoding="utf-8")
    results_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    manifest_path.write_text(
        json.dumps(
            {
                "version": "1",
                "run_id": result.run_id,
                "optimization_id": result.optimization_id,
                "workflow": result.workflow,
                "status": result.status.value,
                "deployable": result.deployable,
                "rejected_stages": [item.stage_id for item in result.rejections],
                "run_label": result.run_label.value,
                "architecture": hardware.architecture,
                "cpu": hardware.cpu_model,
                "git_commit": result.baseline[0].git_commit if result.baseline else "unknown",
                "generated_at": result.timestamp.isoformat(),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return [report_path, results_path, manifest_path]
