import { useWorldStore } from '../store/worldStore';
export default function TickControl(){ const {init,tick,refresh,loading}=useWorldStore(); return <div className="panel"><button disabled={loading} onClick={init}>初始化世界</button><button disabled={loading} onClick={tick}>推进一月</button><button onClick={refresh}>刷新</button></div> }
