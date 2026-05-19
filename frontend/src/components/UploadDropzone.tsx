import { useRef, useState } from 'react';
import { Projects } from '../api/client';

interface Props {
  projectId: string;
  onUploaded: () => void;
}

export default function UploadDropzone({ projectId, onUploaded }: Props) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [drag, setDrag] = useState(false);

  async function handle(files: FileList | null) {
    if (!files || !files[0]) return;
    setBusy(true);
    try {
      await Projects.upload(projectId, files[0]);
      onUploaded();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
      onDragLeave={() => setDrag(false)}
      onDrop={(e) => {
        e.preventDefault(); setDrag(false);
        handle(e.dataTransfer.files);
      }}
      onClick={() => fileRef.current?.click()}
      className={`border-2 border-dashed rounded p-8 text-center cursor-pointer transition ${
        drag ? 'border-emerald-500 bg-emerald-50' : 'border-slate-300 bg-slate-50'
      }`}
    >
      <input
        ref={fileRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={(e) => handle(e.target.files)}
      />
      {busy ? (
        <p className="text-slate-600">Uploading…</p>
      ) : (
        <>
          <p className="text-slate-700 font-medium">
            Drop floor plan image here, or click to browse
          </p>
          <p className="text-xs text-slate-500 mt-1">
            Tip: name your file like <code>office_30x20m.png</code> for auto-scale.
          </p>
        </>
      )}
    </div>
  );
}
