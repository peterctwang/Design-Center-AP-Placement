import { useEffect, useRef, useState } from 'react';

export interface TaskUpdate {
  stage?: string;
  progress?: number;
  coverage?: number;
  done?: boolean;
  error?: string;
  result?: any;
}

/** Subscribe to a backend Task WebSocket and surface progress + completion. */
export function useTaskWS(taskId: string | null) {
  const [status, setStatus] = useState<'idle'|'open'|'done'|'error'>('idle');
  const [update, setUpdate] = useState<TaskUpdate | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!taskId) return;
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    const ws = new WebSocket(`${proto}://${location.host}/ws/tasks/${taskId}`);
    wsRef.current = ws;
    ws.onopen = () => setStatus('open');
    ws.onmessage = (ev) => {
      try {
        const msg: TaskUpdate = JSON.parse(ev.data);
        setUpdate(msg);
        if (msg.done) setStatus('done');
        if (msg.error) setStatus('error');
      } catch { /* ignore */ }
    };
    ws.onerror = () => setStatus('error');
    return () => { ws.close(); };
  }, [taskId]);

  return { status, update };
}
