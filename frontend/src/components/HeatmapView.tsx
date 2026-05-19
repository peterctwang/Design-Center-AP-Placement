import { useEffect, useState } from 'react';
import Plot from 'react-plotly.js';
import { Heatmap, type HeatmapData } from '../api/client';

const MODES = [
  { id: 'signal_strength', label: 'Signal Strength' },
  { id: 'coverage',        label: 'Coverage' },
  { id: 'interference',    label: 'Interference' },
  { id: 'sinr',            label: 'SINR' },
] as const;

const COLORSCALE = 'RdYlGn';

const VRANGE: Record<string, [number, number]> = {
  signal_strength: [-90, -40],
  coverage:        [0, 1],
  interference:    [-90, -45],
  sinr:            [0, 35],
};

const LABEL: Record<string, string> = {
  signal_strength: 'RSSI (dBm)',
  coverage:        'Covered (1) / Not (0)',
  interference:    '2nd-best RSSI (dBm)',
  sinr:            'SINR (dB)',
};

export default function HeatmapView({ projectId }: { projectId: string }) {
  const [mode, setMode] = useState<string>('signal_strength');
  const [data, setData] = useState<HeatmapData | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function load(m: string) {
    setBusy(true); setErr(null);
    try {
      const d = await Heatmap.get(projectId, m, 80);
      setData(d);
    } catch (e: any) {
      setErr(e?.response?.data?.detail ?? 'Failed');
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => { load(mode); }, [mode, projectId]);

  return (
    <div className="bg-white border rounded p-4">
      <div className="flex items-center gap-2 mb-3">
        <h3 className="font-semibold">Heatmap</h3>
        <select
          value={mode}
          onChange={(e) => setMode(e.target.value)}
          className="border rounded px-2 py-1 text-sm">
          {MODES.map((m) => (
            <option key={m.id} value={m.id}>{m.label}</option>
          ))}
        </select>
        {busy && <span className="text-sm text-slate-500">Computing…</span>}
        {err && <span className="text-sm text-rose-600">{err}</span>}
      </div>

      {data && (
        <>
          <Plot
            data={[{
              z: data.grid,
              type: 'heatmap',
              colorscale: COLORSCALE,
              zmin: VRANGE[mode][0],
              zmax: VRANGE[mode][1],
              colorbar: { title: { text: LABEL[mode] } as any },
              x: linspace(data.bounds[0], data.bounds[2], data.resolution),
              y: linspace(data.bounds[1], data.bounds[3], data.resolution),
            }] as any}
            layout={{
              autosize: true,
              height: 480,
              margin: { l: 50, r: 30, t: 40, b: 50 },
              yaxis: { autorange: 'reversed', title: { text: 'Y (m)' } as any },
              xaxis: { title: { text: 'X (m)' } as any },
              title: { text:
                `Coverage ≥-65dBm: ${data.covered_pct.toFixed(1)}%  |  ` +
                `Avg: ${data.avg_rssi.toFixed(1)} dBm` } as any,
            }}
            style={{ width: '100%' }}
            useResizeHandler
          />
          <div className="text-xs text-slate-500 mt-2">
            Coverage <b>{data.covered_pct.toFixed(1)}%</b> ·
            Avg <b>{data.avg_rssi.toFixed(1)} dBm</b> ·
            Worst <b>{data.min_rssi.toFixed(1)} dBm</b>
          </div>
        </>
      )}
    </div>
  );
}

function linspace(a: number, b: number, n: number): number[] {
  const out = new Array(n);
  const step = (b - a) / (n - 1);
  for (let i = 0; i < n; i++) out[i] = a + i * step;
  return out;
}
