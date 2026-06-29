import { useWorldStore } from '../store/worldStore';

export default function InterventionTimeline(){
  const rec=useWorldStore(s=>s.lastIntervention);
  const chain=useWorldStore(s=>s.interventionChain);
  return <div className="panel timeline">
    <h3>因果时间轴</h3>
    {rec ? <p>{rec.id}: {rec.tool_type} → {rec.hex_id}</p> : <p>暂无干预</p>}
    {chain.length > 0 && <ol>{chain.map(link => <li key={link.id}>#{link.sequence} {link.link_type}: {link.target_type}/{link.target_id}<br/><small>{link.description}</small></li>)}</ol>}
  </div>
}
