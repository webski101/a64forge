import {
  CartesianGrid,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import type { BenchmarkRecord } from "./types";

export default function BenchmarkChart({ records }: { records: BenchmarkRecord[] }) {
  const chart = records
    .filter(
      (item) =>
        item.peak_memory_mb != null && item.quality_score != null && !item.error
    )
    .map((item) => ({
      memory: item.peak_memory_mb,
      quality: item.quality_score,
      stage: item.stage_id,
      model: item.model
    }));

  return (
    <div className="chart">
      <h2>Memory vs quality</h2>
      <ResponsiveContainer width="100%" height={300}>
        <ScatterChart margin={{ top: 20, right: 20, bottom: 10, left: 0 }}>
          <CartesianGrid stroke="var(--color-rule)" />
          <XAxis
            type="number"
            dataKey="memory"
            name="Peak memory"
            unit=" MB"
            stroke="var(--color-muted)"
          />
          <YAxis
            type="number"
            dataKey="quality"
            name="Quality"
            domain={[0, 1]}
            stroke="var(--color-muted)"
          />
          <Tooltip
            cursor={{ strokeDasharray: "3 3" }}
            contentStyle={{
              background: "var(--color-panel)",
              border: "1px solid var(--color-rule)",
              color: "var(--color-ink)"
            }}
          />
          <Scatter data={chart} fill="var(--color-accent)" />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}
