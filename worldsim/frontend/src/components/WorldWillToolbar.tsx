import { useWorldStore } from '../store/worldStore';
const tools=['IRON','STONE','TIMBER','FERTILE_SOIL','SPRING'];
export default function WorldWillToolbar(){ const {selectedTool,setTool}=useWorldStore(); return <div className="panel toolbar"><h3>世界意志 权限1</h3>{tools.map(t=><button key={t} className={selectedTool===t?'active':''} onClick={()=>setTool(t)}>{t}</button>)}</div> }
