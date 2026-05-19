import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import UploadDropzone from '../components/UploadDropzone';
import FloorPlanCanvas from '../components/FloorPlanCanvas';
import HeatmapView from '../components/HeatmapView';
import { useTaskWS } from '../hooks/useTaskWS';
import {
  Projects, Walls, Optimize, Report,
  type Project, type Wall, type AP,
} from '../api/client';

export default function Editor() {
  const { id } = useParams<{ id: string }>();
  const projectId = id!;
  const [project, setProject] = useState<Project | null>(null);
  const [walls, setWalls] = useState<Wall[]>([]);
  const [aps, setAps] = useState<AP[]>([]);

  // GA controls
  const [numAps, setNumAps] = useState(0);      // 0 = auto
  const [targetCov, setTargetCov] = useState(0.9);
  const [sqmPerAp, setSqmPerAp] = useState(120);

  // Visualization toggle
  const [showWalls, setShowWalls] = useState(true);

  // Task tracking
  const [taskId, setTaskId] = useState<string | null>(null);
  const { status: taskStatus, update: taskUpdate } = useTaskWS(taskId);

  async function refresh() {
    const p = await Projects.get(projectId);
    setProject(p);
    setWalls(await Walls.list(projectId));
    setAps(await Optimize.listAPs(projectId));
  }
  useEffect(() => { refresh(); }, [projectId]);

  // On task done, reload APs
  useEffect(() => {
    if (taskStatus === 'done') refresh();
  }, [taskStatus]);

  async function onDetect() {
    const w = await Walls.detect(projectId);
    setWalls(w);
  }
  async function onOptimize() {
    const res = await Optimize.start(projectId, {
      algorithm: 'ga',
      target_coverage: targetCov,
      num_aps: numAps,
      sqm_per_ap: sqmPerAp,
    });
    setTaskId(res.task_id);
  }

  if (!project) return <div className="p-6 text-slate-500">Loading project…</div>;

  // Cache-bust by appending updated_at so a Replace Image refreshes the bitmap
  const imageUrl = project.image_path
    ? `/uploads/${project.image_path.split(/[\\/]/).pop()}?t=${
        encodeURIComponent(project.updated_at)
      }`
    : null;

  return (
    <div className="p-4 grid grid-cols-1 lg:grid-cols-[1fr_500px] gap-4">
      {/* LEFT: Floor plan + controls */}
      <div className="space-y-4">
        <div className="bg-white border rounded p-3 flex items-center gap-3">
          <h2 className="font-semibold">{project.name}</h2>
          <span className="text-xs text-slate-500">
            {project.building_w_m && project.building_h_m
              ? `${project.building_w_m}×${project.building_h_m}m`
              : '— no scale —'}
          </span>
          <a
            href={Report.url(projectId)}
            className="ml-auto text-sm text-blue-600 hover:underline"
            target="_blank" rel="noreferrer">
            📄 Download PDF
          </a>
        </div>

        {!project.image_path ? (
          <UploadDropzone projectId={projectId} onUploaded={refresh} />
        ) : (
          <FloorPlanCanvas
            imageUrl={imageUrl}
            buildingW={project.building_w_m ?? 30}
            buildingH={project.building_h_m ?? 20}
            walls={walls}
            aps={aps}
            showWalls={showWalls}
          />
        )}

        {project.image_path && (
          <div className="bg-white border rounded p-3 space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <button onClick={onDetect}
                className="bg-orange-500 hover:bg-orange-600 text-white px-3 py-2 rounded text-sm">
                ★ Auto Detect Walls
              </button>
              <UploadAgainButton id={projectId} onDone={refresh} />
              <WallBadges walls={walls} />
              <span className="text-xs text-slate-500">
                · {aps.length} APs
              </span>
              <label className="ml-auto text-xs flex items-center gap-1 cursor-pointer">
                <input
                  type="checkbox"
                  checked={showWalls}
                  onChange={(e) => setShowWalls(e.target.checked)}
                />
                Show wall overlay
              </label>
            </div>

            <div className="flex flex-wrap items-center gap-3 pt-2 border-t">
              <label className="text-sm">
                # APs (0=auto):
                <input type="number" value={numAps} min={0} max={50}
                  onChange={(e) => setNumAps(Number(e.target.value))}
                  className="ml-2 w-16 border rounded px-2 py-1 text-sm" />
              </label>
              <label className="text-sm">
                Target coverage:
                <input type="number" value={targetCov} step="0.05" min={0.5} max={1}
                  onChange={(e) => setTargetCov(Number(e.target.value))}
                  className="ml-2 w-20 border rounded px-2 py-1 text-sm" />
              </label>
              <label className="text-sm">
                m²/AP:
                <input type="number" value={sqmPerAp} step="10" min={30} max={500}
                  onChange={(e) => setSqmPerAp(Number(e.target.value))}
                  className="ml-2 w-20 border rounded px-2 py-1 text-sm" />
              </label>
              <button onClick={onOptimize}
                className="bg-emerald-600 hover:bg-emerald-700 text-white px-3 py-2 rounded text-sm">
                ▶ Run GA Optimizer
              </button>
            </div>

            {taskId && (
              <div className="pt-2 border-t">
                <div className="h-2 bg-slate-200 rounded overflow-hidden">
                  <div
                    className="h-full bg-emerald-500 transition-all"
                    style={{ width: `${taskUpdate?.progress ?? 0}%` }}
                  />
                </div>
                <div className="text-xs text-slate-600 mt-1">
                  {taskStatus === 'done'
                    ? `✓ Done — ${taskUpdate?.result?.num_aps} APs, coverage ${(taskUpdate?.result?.coverage * 100).toFixed(1)}%`
                    : taskStatus === 'error'
                    ? `✗ Error: ${taskUpdate?.error}`
                    : taskUpdate?.stage ?? 'Starting…'}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* RIGHT: Heatmap */}
      <div className="space-y-4">
        {aps.length > 0 ? (
          <HeatmapView projectId={projectId} />
        ) : (
          <div className="bg-white border rounded p-4 text-center text-slate-500">
            <p className="font-medium mb-2">Heatmap will appear here</p>
            <ol className="text-sm text-left list-decimal pl-5 space-y-1">
              <li>Upload a floor plan</li>
              <li>Click Auto Detect Walls</li>
              <li>Click Run GA Optimizer</li>
            </ol>
          </div>
        )}
      </div>
    </div>
  );
}


const MAT_COLOR: Record<string, string> = {
  concrete: '#000000', brick: '#8B4513', glass: '#00CED1',
  wood: '#D2691E', drywall: '#A9A9A9', metal: '#4B4B4B', door: '#00B050',
};

function WallBadges({ walls }: { walls: Wall[] }) {
  const counts = walls.reduce<Record<string, number>>((acc, w) => {
    acc[w.material] = (acc[w.material] ?? 0) + 1;
    return acc;
  }, {});
  if (walls.length === 0) return <span className="text-xs text-slate-500">0 walls</span>;
  return (
    <span className="text-xs text-slate-700 flex items-center gap-1 flex-wrap">
      <span className="font-semibold">{walls.length} walls:</span>
      {Object.entries(counts).map(([mat, n]) => (
        <span key={mat}
              className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded
                         border bg-slate-50">
          <span className="inline-block w-2 h-2 rounded-full"
                style={{ background: MAT_COLOR[mat] ?? '#000' }} />
          {mat}:{n}
        </span>
      ))}
    </span>
  );
}

function UploadAgainButton(
  { id, onDone }: { id: string; onDone: () => void },
) {
  const [busy, setBusy] = useState(false);
  return (
    <label className={`px-3 py-2 rounded text-sm cursor-pointer ${
        busy ? 'bg-slate-300' : 'bg-slate-100 hover:bg-slate-200'
      }`}>
      {busy ? 'Uploading…' : '↻ Replace image'}
      <input type="file" accept="image/*" className="hidden"
        onChange={async (e) => {
          const f = e.target.files?.[0]; if (!f) return;
          setBusy(true);
          try { await Projects.upload(id, f); onDone(); }
          finally { setBusy(false); }
        }} />
    </label>
  );
}
