import { useEffect } from 'react';
import HexMap from './components/HexMap';
import NationPanel from './components/NationPanel';
import EventLog from './components/EventLog';
import TickControl from './components/TickControl';
import PolicyViewer from './components/PolicyViewer';
import WorldWillToolbar from './components/WorldWillToolbar';
import InterventionPanel from './components/InterventionPanel';
import InterventionTimeline from './components/InterventionTimeline';
import { useWorldStore } from './store/worldStore';
export default function App(){ const refresh=useWorldStore(s=>s.refresh); useEffect(()=>{refresh().catch(()=>undefined)},[refresh]); return <div className="app"><main><HexMap /></main><aside><TickControl/><WorldWillToolbar/><InterventionPanel/><InterventionTimeline/><NationPanel/><PolicyViewer/><EventLog/></aside></div> }
