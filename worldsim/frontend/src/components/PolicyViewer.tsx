import { useWorldStore } from '../store/worldStore';
export default function PolicyViewer(){ const policies=useWorldStore(s=>s.policies); return <div className="panel events"><h3>政策</h3>{policies.map(p=><p key={p.id}>#{p.tick_number} {p.nation_id}: {p.policy_key} [{p.status}]</p>)}</div> }
