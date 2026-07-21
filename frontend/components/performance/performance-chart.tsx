"use client";

import {
  Area,
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { PerformancePoint } from "@/lib/api";

const dateFormatter = new Intl.DateTimeFormat("en", {
  month: "short",
  day: "numeric",
});

function displayDate(value: string) {
  return dateFormatter.format(new Date(`${value}T00:00:00`));
}

export function PerformanceChart({ points }: { points: PerformancePoint[] }) {
  return (
    <div data-testid="performance-chart" className="h-[22rem] w-full sm:h-[28rem]">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart
          data={points}
          margin={{ top: 16, right: 8, bottom: 4, left: -16 }}
          accessibilityLayer
        >
          <defs>
            <linearGradient id="tsb-fill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#c7ff2e" stopOpacity={0.45} />
              <stop offset="100%" stopColor="#c7ff2e" stopOpacity={0.04} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="#dce3d9" strokeDasharray="3 5" vertical={false} />
          <XAxis
            dataKey="date"
            tickFormatter={displayDate}
            tick={{ fill: "#607064", fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            minTickGap={30}
          />
          <YAxis
            yAxisId="load"
            tick={{ fill: "#607064", fontSize: 11 }}
            tickLine={false}
            axisLine={false}
          />
          <YAxis yAxisId="tss" orientation="right" hide />
          <Tooltip
            labelFormatter={(label) => displayDate(String(label))}
            formatter={(value, name) => [Number(value).toFixed(1), name]}
            contentStyle={{
              border: 0,
              borderRadius: 16,
              boxShadow: "0 16px 40px rgba(17, 21, 16, .14)",
            }}
          />
          <Legend iconType="circle" wrapperStyle={{ fontSize: 12, paddingTop: 12 }} />
          <Bar
            yAxisId="tss"
            dataKey="daily_tss"
            name="Daily TSS"
            fill="#b8c0b9"
            opacity={0.42}
            radius={[3, 3, 0, 0]}
          />
          <Area
            yAxisId="load"
            type="monotone"
            dataKey="tsb"
            name="TSB"
            stroke="#86a800"
            fill="url(#tsb-fill)"
            strokeWidth={2}
          />
          <Line
            yAxisId="load"
            type="monotone"
            dataKey="ctl"
            name="CTL"
            stroke="#111510"
            strokeWidth={3}
            dot={false}
            activeDot={{ r: 4 }}
          />
          <Line
            yAxisId="load"
            type="monotone"
            dataKey="atl"
            name="ATL"
            stroke="#df6b3e"
            strokeWidth={2.5}
            dot={false}
            activeDot={{ r: 4 }}
          />
        </ComposedChart>
      </ResponsiveContainer>
      <table className="sr-only">
        <caption>Daily performance chart values</caption>
        <thead>
          <tr><th>Date</th><th>Daily TSS</th><th>CTL</th><th>ATL</th><th>TSB</th></tr>
        </thead>
        <tbody>
          {points.map((point) => (
            <tr key={point.date}>
              <td>{point.date}</td><td>{point.daily_tss}</td><td>{point.ctl}</td>
              <td>{point.atl}</td><td>{point.tsb}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
