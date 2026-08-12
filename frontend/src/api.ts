import type { BenchmarkRecord, Hardware, ModelSpec, Optimization, ProgressEvent, Workflow } from "./types";

async function get<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`${url}: ${response.status}`);
  return response.json() as Promise<T>;
}

export async function loadDashboard() {
  const [hardware, models, workflows, benchmarks, optimizations] = await Promise.all([
    get<Hardware>("/system"),
    get<ModelSpec[]>("/models"),
    get<Workflow[]>("/workflows"),
    get<{ records: BenchmarkRecord[] }>("/benchmarks"),
    get<{ items: Optimization[] }>("/optimizations")
  ]);
  return { hardware, models, workflows, records: benchmarks.records, optimizations: optimizations.items };
}

export async function action(name: "benchmark" | "optimize" | "compile" | "report") {
  const response = await fetch(`/actions/${name}`, { method: "POST" });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.detail ?? `Action failed: ${name}`);
  return payload;
}

export function subscribe(onEvent: (event: ProgressEvent) => void) {
  const source = new EventSource("/events");
  for (const name of ["start", "candidate_start", "measure", "candidate_end", "progress", "complete", "error"]) {
    source.addEventListener(name, (raw) => onEvent(JSON.parse((raw as MessageEvent).data) as ProgressEvent));
  }
  return () => source.close();
}

