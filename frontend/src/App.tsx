import { Routes, Route, Link, Navigate } from 'react-router-dom';
import ProjectList from './pages/ProjectList';
import Editor from './pages/Editor';

export default function App() {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-slate-900 text-white px-6 py-3 flex items-center gap-4">
        <Link to="/" className="text-lg font-bold">AI Wall Design</Link>
        <span className="text-xs opacity-70">
          WiFi AP placement · GA + auto wall detection
        </span>
        <span className="ml-auto text-xs opacity-50">v0.1 demo</span>
      </header>

      <main className="flex-1">
        <Routes>
          <Route path="/" element={<ProjectList />} />
          <Route path="/project/:id" element={<Editor />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}
