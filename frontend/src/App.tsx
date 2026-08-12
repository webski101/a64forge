import { lazy, Suspense, useEffect, useState } from "react";
import {
  Activity,
  BarChart3,
  Boxes,
  Braces,
  Check,
  ChevronRight,
  CircleDot,
  Cpu,
  FileText,
  FlaskConical,
  Gauge,
  Menu,
  Play,
  RefreshCw,
  ShieldAlert,
  X
} from "lucide-react";
import { action, loadDashboard, subscribe } from "./api";
import type { BenchmarkRecord, Hardware, ModelSpec, Optimization, ProgressEvent, Workflow } from "./types";

type Page = "Overview" | "Workflows" | "Optimization Lab" | "Benchmarks" | "Arm System" | "Reports";

const navigation: Array<{ label: Page; icon: typeof Activity }> = [
  { label: "Overview", icon: Gauge },
  { label: "Workflows", icon: Boxes },
  { label: "Optimization Lab", icon: FlaskConical },
  { label: "Benchmarks", icon: BarChart3 },
  { label: "Arm System", icon: Cpu },
  { label: "Reports", icon: FileText }
];

const BenchmarkChart = lazy(() => import("./BenchmarkChart"));

const emptyHardware: Hardware = {
  architecture: "unknown", cpu_model: "Not detected yet", logical_cores: 0, physical_cores: null,
  memory_gb: 0, available_memory_gb: 0, os: "unknown", hostname: "unknown", arm64: false,
  neon: "unknown", sve: "unknown", sve2: "unknown", arm_fma: "unknown", matmul_int8: "unknown",
  llama_cpp: false, llama_server: false, llama_bench: false, performix: false, llama_version: null,
  disk_free_gb: 0, dev_mode: true
};

function fmt(value: number | null | undefined, unit = "") {
  return value == null ? "Not measured yet" : `${value.toLocaleString(undefined, { maximumFractionDigits: 2 })}${unit}`;
}

function StateMark({ ok, label }: { ok: boolean; label: string }) {
  return <span className={`state-mark ${ok ? "state-mark--ok" : "state-mark--off"}`}><CircleDot size={14} />{label}</span>;
}

function RunLabel({ label }: { label?: BenchmarkRecord["run_label"] }) {
  const text = label ?? "NO VERIFIED ARM BENCHMARK";
  return <span className={`run-label ${text === "VERIFIED ARM64 RUN" ? "run-label--verified" : "run-label--warning"}`}>
    {text === "VERIFIED ARM64 RUN" ? <Check size={14} /> : <ShieldAlert size={14} />}{text}
  </span>;
}

function OptimizationState({ result }: { result?: Optimization }) {
  if (!result) return null;
  const deployable = result.status === "DEPLOYABLE";
  return <span className={`run-label ${deployable ? "run-label--verified" : "run-label--warning"}`}>
    {deployable ? <Check size={14} /> : <ShieldAlert size={14} />}{result.status}
  </span>;
}

function WorkflowGraph({ workflow, optimization }: { workflow?: Workflow; optimization?: Optimization }) {
  const selected = new Map(optimization?.selections.map((item) => [item.stage_id, item.selected]));
  const rejected = new Set(optimization?.rejections.map((item) => item.stage_id));
  return <div className="workflow-graph" aria-label="Stage routing graph">
    {(workflow?.stages ?? []).map((stage, index, stages) => {
      const route = selected.get(stage.id);
      return <div className="workflow-fragment" key={stage.id}>
        <article className={`workflow-node ${route ? "workflow-node--selected" : ""} ${rejected.has(stage.id) ? "workflow-node--rejected" : ""}`}>
          <div className="workflow-node__head"><Braces size={17} /><span>{stage.type.replace("_", " ")}</span></div>
          <strong>{stage.id}</strong>
          <dl>
            <div><dt>model</dt><dd>{route?.model ?? "Not selected"}</dd></div>
            <div><dt>quant</dt><dd>{route?.quantization ?? "—"}</dd></div>
            <div><dt>threads</dt><dd>{route?.threads ?? "—"}</dd></div>
          </dl>
        </article>
        {index < stages.length - 1 && <ChevronRight className="workflow-arrow" aria-hidden="true" />}
      </div>;
    })}
  </div>;
}

function MetricStrip({ latest }: { latest?: Optimization }) {
  const before = latest?.baseline ?? [];
  const after = latest?.selections.map((item) => item.selected) ?? [];
  const median = (items: BenchmarkRecord[], key: keyof BenchmarkRecord) => {
    const values = items.map((item) => item[key]).filter((value): value is number => typeof value === "number");
    return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null;
  };
  const metrics = [
    ["Median latency", median(before, "median_latency_ms"), median(after, "median_latency_ms"), " ms"],
    ["Peak memory", median(before, "peak_memory_mb"), median(after, "peak_memory_mb"), " MB"],
    ["Throughput", median(before, "requests_per_minute"), median(after, "requests_per_minute"), " req/min"],
    ["Quality", median(before, "quality_score"), median(after, "quality_score"), ""]
  ] as const;
  return <div className="metric-strip">
    {metrics.map(([label, base, optimized, unit]) => <div key={label}>
      <span>{label}</span><strong>{fmt(optimized, unit)}</strong><small>baseline {fmt(base, unit)}</small>
    </div>)}
  </div>;
}

function Overview({ hardware, models, records, workflow, latest, onNavigate }: {
  hardware: Hardware; models: ModelSpec[]; records: BenchmarkRecord[]; workflow?: Workflow; latest?: Optimization; onNavigate: (page: Page) => void;
}) {
  return <>
    <section className="hero">
      <div>
        <p className="machine-line">$ a64forge inspect --workflow research-ops</p>
        <h1>Compile agents for the CPU beneath them.</h1>
        <p>A64Forge benchmarks each workflow stage against local GGUF models, protects quality, then emits the routing and evidence needed to deploy on Arm64.</p>
        <div className="actions"><button className="button button--primary" onClick={() => onNavigate("Workflows")}><Boxes size={17} />Analyze agent</button><button className="button" onClick={() => onNavigate("Optimization Lab")}><FlaskConical size={17} />Open lab</button></div>
      </div>
      <div className="hero-proof">
        <span>HOST TARGET</span><strong>{hardware.arm64 ? "ARM64 / AARCH64" : hardware.architecture.toUpperCase()}</strong>
        <p>{hardware.cpu_model}</p><RunLabel label={latest?.run_label} /><OptimizationState result={latest} />
      </div>
    </section>
    <MetricStrip latest={latest} />
    <section className="overview-grid">
      <div className="overview-main"><div className="section-head"><div><h2>Stage routing</h2><p>{latest ? (latest.status === "DEPLOYABLE" ? "Latest compiled selection" : "Deployment withheld by quality gates") : "Awaiting measured candidates"}</p></div><button className="text-button" onClick={() => onNavigate("Optimization Lab")}>Inspect frontier <ChevronRight size={16} /></button></div><WorkflowGraph workflow={workflow} optimization={latest} /></div>
      <aside className="inventory"><h2>Inventory</h2><dl><div><dt>Candidate models</dt><dd>{models.length}</dd></div><div><dt>Measured records</dt><dd>{records.length}</dd></div><div><dt>Workflow stages</dt><dd>{workflow?.stages.length ?? 0}</dd></div><div><dt>llama-server</dt><dd>{hardware.llama_server ? "ready" : "unavailable"}</dd></div></dl></aside>
    </section>
  </>;
}

function Workflows({ workflow }: { workflow?: Workflow }) {
  return <section><div className="page-head"><h1>ResearchOps workflow</h1><p>A deterministic five-stage workload with stage-specific quality metrics.</p></div><WorkflowGraph workflow={workflow} />
    <div className="spec-table">{workflow?.stages.map((stage) => <div className="spec-row" key={stage.id}><strong>{stage.id}</strong><span>{stage.type}</span><code>{stage.quality_metric}</code><span>{stage.max_tokens} max tokens</span></div>)}</div></section>;
}

function OptimizationLab({ workflow, latest, events, busy, onRun }: { workflow?: Workflow; latest?: Optimization; events: ProgressEvent[]; busy: boolean; onRun: () => void }) {
  return <section><div className="lab-head"><div><h1>Optimization Lab</h1><p>The workflow transforms only when a candidate passes its quality gate.</p></div><button className="button button--primary" disabled={busy} aria-busy={busy} onClick={onRun}>{busy ? <RefreshCw size={17} /> : <Play size={17} />}{busy ? "Benchmarking" : "Optimize for Arm64"}</button></div>
    <div className="result-labels"><RunLabel label={latest?.run_label} /><OptimizationState result={latest} /></div>
    <div className="lab-grid"><div className="lab-canvas"><h2>{latest ? (latest.status === "DEPLOYABLE" ? "Compiled routing" : "Quality-gated result") : "Baseline topology"}</h2><WorkflowGraph workflow={workflow} optimization={latest} /></div><aside className="event-log" aria-live="polite"><div className="event-log__head"><Activity size={16} />Live compiler log</div>{events.length ? events.slice(-12).reverse().map((event, index) => <div className="event-line" key={`${event.timestamp}-${index}`}><span>{event.stage_id ?? "system"}</span><p>{event.message}</p></div>) : <div className="empty"><p>No optimization is running.</p><span>Start a benchmark to stream real progress.</span></div>}</aside></div>
    {latest && <div className="decisions"><h2>Optimization decisions</h2>{latest.selections.map((selection) => <article key={selection.stage_id}><h3>{selection.stage_id}</h3><p>{selection.selected.model} / {selection.selected.quantization} / {selection.selected.threads} threads</p><ul>{selection.explanation.map((reason) => <li key={reason}>{reason}</li>)}</ul></article>)}{latest.rejections.map((rejection) => <article className="decision--rejected" key={rejection.stage_id}><h3>{rejection.stage_id}</h3><p>No route compiled</p><ul><li>{rejection.reason}</li></ul></article>)}</div>}
  </section>;
}

function Benchmarks({ records }: { records: BenchmarkRecord[] }) {
  const chart = records.filter((item) => item.peak_memory_mb != null && item.quality_score != null && !item.error).map((item) => ({ memory: item.peak_memory_mb, quality: item.quality_score, stage: item.stage_id, model: item.model }));
  return <section><div className="page-head"><h1>Benchmark evidence</h1><p>Every row maps to a stored experiment artifact. Missing metrics remain missing.</p></div>{chart.length > 0 && <Suspense fallback={<div className="chart">Loading evidence chart…</div>}><BenchmarkChart records={records} /></Suspense>}
    <div className="benchmark-list">{records.length ? records.map((record, index) => <article key={`${record.run_id}-${index}`}><div><RunLabel label={record.run_label} /><h3>{record.stage_id} · {record.model}</h3><p>{record.quantization} · {record.threads} threads · batch {record.batch_size} · ctx {record.context_size}</p></div><dl><div><dt>median</dt><dd>{fmt(record.median_latency_ms, " ms")}</dd></div><div><dt>p95</dt><dd>{fmt(record.p95_latency_ms, " ms")}</dd></div><div><dt>memory</dt><dd>{fmt(record.peak_memory_mb, " MB")}</dd></div><div><dt>quality</dt><dd>{fmt(record.quality_score)}</dd></div></dl></article>) : <div className="empty empty--large"><BarChart3 size={28} /><h2>Not measured yet</h2><p>Run the benchmark matrix on a configured llama-server. A64Forge will not invent chart data.</p></div>}</div></section>;
}

function ArmSystem({ hardware }: { hardware: Hardware }) {
  const facts = [["Architecture", hardware.architecture], ["CPU", hardware.cpu_model], ["Logical cores", hardware.logical_cores], ["Physical cores", hardware.physical_cores ?? "unknown"], ["Memory", `${hardware.memory_gb} GB`], ["Free disk", `${hardware.disk_free_gb} GB`], ["Runtime", hardware.llama_version ?? "unavailable"]];
  return <section><div className="page-head"><h1>Arm system evidence</h1><p>Raw host and runtime detection. Nothing here is inferred from a cloud-provider label.</p></div><RunLabel label={hardware.arm64 && !hardware.dev_mode ? "VERIFIED ARM64 RUN" : undefined} /><div className="system-grid"><div className="system-facts">{facts.map(([key, value]) => <div key={key}><span>{key}</span><strong>{value}</strong></div>)}</div><div className="capabilities"><h2>CPU capabilities</h2><StateMark ok={hardware.neon === "detected"} label={`NEON · ${hardware.neon}`} /><StateMark ok={hardware.sve === "detected"} label={`SVE · ${hardware.sve}`} /><StateMark ok={hardware.sve2 === "detected"} label={`SVE2 · ${hardware.sve2}`} /><StateMark ok={hardware.matmul_int8 === "detected"} label={`MATMUL_INT8 · ${hardware.matmul_int8}`} /><StateMark ok={hardware.llama_server} label={`llama-server · ${hardware.llama_server ? "available" : "unavailable"}`} /><StateMark ok={hardware.performix} label={`Performix · ${hardware.performix ? "available" : "unavailable"}`} /></div></div></section>;
}

function Reports({ latest, onGenerate }: { latest?: Optimization; onGenerate: () => void }) {
  return <section><div className="page-head"><h1>Portable evidence</h1><p>HTML, JSON, and deployment manifests share one benchmark run identifier.</p></div>{latest ? <div className="report-sheet"><div className="result-labels"><RunLabel label={latest.run_label} /><OptimizationState result={latest} /></div><h2>{latest.workflow}</h2><p>Run {latest.run_id} · optimization {latest.optimization_id} · target {latest.target}</p><button className="button button--primary" onClick={onGenerate}><FileText size={17} />Generate report</button></div> : <div className="empty empty--large"><FileText size={28} /><h2>Not measured yet</h2><p>An optimization result is required before a report can be generated.</p></div>}</section>;
}

export default function App() {
  const [page, setPage] = useState<Page>("Overview");
  const [menuOpen, setMenuOpen] = useState(false);
  const [hardware, setHardware] = useState<Hardware>(emptyHardware);
  const [models, setModels] = useState<ModelSpec[]>([]);
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [records, setRecords] = useState<BenchmarkRecord[]>([]);
  const [optimizations, setOptimizations] = useState<Optimization[]>([]);
  const [events, setEvents] = useState<ProgressEvent[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = () => loadDashboard().then((data) => { setHardware(data.hardware); setModels(data.models); setWorkflows(data.workflows); setRecords(data.records); setOptimizations(data.optimizations); setError(null); }).catch((reason: Error) => setError(reason.message));
  useEffect(() => { void refresh(); return subscribe((event) => { setEvents((items) => [...items.slice(-49), event]); if (event.event === "complete" || event.event === "error") { setBusy(false); void refresh(); } }); }, []);
  const latest = optimizations[0];
  const workflow = workflows[0];
  const route = (next: Page) => { setPage(next); setMenuOpen(false); };
  const run = async () => { setBusy(true); setError(null); try { await action("benchmark"); } catch (reason) { setBusy(false); setError((reason as Error).message); } };
  const optimize = async () => { setError(null); try { await action("optimize"); await refresh(); } catch (reason) { setError((reason as Error).message); } };
  const generated = async () => { setError(null); try { await action("report"); await refresh(); } catch (reason) { setError((reason as Error).message); } };
  const pageContent = (() => {
    if (page === "Overview") return <Overview hardware={hardware} models={models} records={records} workflow={workflow} latest={latest} onNavigate={route} />;
    if (page === "Workflows") return <Workflows workflow={workflow} />;
    if (page === "Optimization Lab") return <OptimizationLab workflow={workflow} latest={latest} events={events} busy={busy} onRun={records.length ? optimize : run} />;
    if (page === "Benchmarks") return <Benchmarks records={records} />;
    if (page === "Arm System") return <ArmSystem hardware={hardware} />;
    return <Reports latest={latest} onGenerate={generated} />;
  })();

  return <div className="app-shell">
    <header className="mobile-header"><button className="icon-button" aria-label={menuOpen ? "Close navigation" : "Open navigation"} aria-expanded={menuOpen} onClick={() => setMenuOpen(!menuOpen)}>{menuOpen ? <X /> : <Menu />}</button><strong>A64FORGE</strong><span>v0.1</span></header>
    <aside className={`side-rail ${menuOpen ? "side-rail--open" : ""}`}>
      <div className="brand"><span className="brand-mark">A64</span><div><strong>A64FORGE</strong><small>ARM OPTIMIZER</small></div></div>
      <nav aria-label="Primary navigation">{navigation.map(({ label, icon: Icon }) => <button key={label} className={page === label ? "nav-item nav-item--active" : "nav-item"} aria-current={page === label ? "page" : undefined} onClick={() => route(label)}><Icon size={18} /><span>{label}</span></button>)}</nav>
      <div className="rail-status"><StateMark ok={hardware.arm64} label={hardware.arm64 ? "ARM64 detected" : "Non-Arm host"} /><StateMark ok={hardware.llama_server} label={hardware.llama_server ? "Runtime ready" : "Runtime missing"} /></div>
    </aside>
    <main className="workspace">{hardware.dev_mode && <div className="dev-banner"><ShieldAlert size={16} /><strong>DEVELOPMENT MODE</strong><span>NO VERIFIED ARM BENCHMARK</span></div>}{error && <div className="error-banner" role="alert"><span>{error}</span><button onClick={() => setError(null)} aria-label="Dismiss error"><X size={16} /></button></div>}{pageContent}<footer><span>A64Forge · Apache-2.0</span><span>Measurements require a real local runtime.</span></footer></main>
  </div>;
}
