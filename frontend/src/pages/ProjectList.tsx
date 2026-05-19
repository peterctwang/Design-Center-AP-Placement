import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Projects, type Project } from '../api/client';

export default function ProjectList() {
  const nav = useNavigate();
  const [items, setItems] = useState<Project[]>([]);
  const [name, setName] = useState('');
  const [loading, setLoading] = useState(true);

  const refresh = () =>
    Projects.list().then(setItems).finally(() => setLoading(false));

  useEffect(() => { refresh(); }, []);

  async function onCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    const p = await Projects.create(name.trim());
    setName('');
    nav(`/project/${p.id}`);
  }

  async function onDelete(id: string) {
    if (!confirm('Delete this project?')) return;
    await Projects.remove(id);
    refresh();
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-2xl font-semibold mb-6">Projects</h1>

      <form onSubmit={onCreate} className="flex gap-2 mb-6">
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="New project name…"
          className="flex-1 border rounded px-3 py-2"
        />
        <button
          type="submit"
          className="bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded">
          Create
        </button>
      </form>

      {loading ? (
        <p className="text-slate-500">Loading…</p>
      ) : items.length === 0 ? (
        <p className="text-slate-500">No projects yet. Create one above to get started.</p>
      ) : (
        <ul className="divide-y border rounded bg-white">
          {items.map((p) => (
            <li key={p.id} className="flex items-center px-4 py-3">
              <Link to={`/project/${p.id}`} className="flex-1 hover:underline">
                <span className="font-medium">{p.name}</span>
                <span className="ml-2 text-xs text-slate-500">
                  {p.building_w_m && p.building_h_m
                    ? `${p.building_w_m}×${p.building_h_m}m`
                    : 'no floor plan yet'}
                </span>
              </Link>
              <button
                onClick={() => onDelete(p.id)}
                className="text-rose-600 text-sm hover:underline">
                Delete
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
