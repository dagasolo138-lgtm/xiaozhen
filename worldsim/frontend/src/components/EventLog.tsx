import { useEffect } from 'react';
import { api } from '../api/client';
import { useWorldStore } from '../store/worldStore';

export default function EventLog(){
  const events=useWorldStore(s=>s.events);
  const refresh=useWorldStore(s=>s.refresh);

  useEffect(() => {
    const stream = api.eventStream();
    stream.addEventListener('ready', () => { void refresh(); });
    stream.addEventListener('heartbeat', () => { void refresh(); });
    stream.onerror = () => stream.close();
    return () => stream.close();
  }, [refresh]);

  return <div className="panel events"><h3>事件流</h3>{events.map(e=><p key={e.id}>#{e.tick_number} <b>{e.title}</b> {e.description}</p>)}</div>
}
