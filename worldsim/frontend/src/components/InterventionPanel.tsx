import { useWorldStore } from '../store/worldStore';
export default function InterventionPanel(){ const {selectedHex, selectedTool, intervene}=useWorldStore(); return <div className="panel"><h3>干预</h3><p>工具：{selectedTool}</p><p>格子：{selectedHex || '请点击地图'}</p><button disabled={!selectedHex} onClick={intervene}>同步执行</button></div> }
