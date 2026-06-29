import { create } from 'zustand';
import { api, CausalLink, HexCell, InterventionRecord, Nation, PolicyAction, WorldEvent } from '../api/client';

type Store = {
  cells:HexCell[];
  nations:Nation[];
  events:WorldEvent[];
  policies:PolicyAction[];
  selectedTool:string;
  selectedHex?:string;
  lastIntervention?:InterventionRecord;
  interventionChain:CausalLink[];
  loading:boolean;
  setTool:(t:string)=>void;
  setHex:(h:string)=>void;
  refresh:()=>Promise<void>;
  init:()=>Promise<void>;
  tick:()=>Promise<void>;
  intervene:()=>Promise<void>;
  loadChain:(id:string)=>Promise<void>;
};
export const useWorldStore = create<Store>((set, get) => ({
  cells:[], nations:[], events:[], policies:[], selectedTool:'IRON', interventionChain:[], loading:false,
  setTool:(selectedTool)=>set({selectedTool}), setHex:(selectedHex)=>set({selectedHex}),
  refresh: async () => set({ cells: await api.map(), nations: await api.nations(), events: await api.events(), policies: await api.policies() }),
  init: async () => { set({loading:true, interventionChain:[], lastIntervention:undefined}); await api.init(); await get().refresh(); set({loading:false}); },
  tick: async () => { set({loading:true}); await api.tick(); await get().refresh(); const rec=get().lastIntervention; if(rec) await get().loadChain(rec.id); set({loading:false}); },
  loadChain: async (id) => set({ interventionChain: await api.chain(id) }),
  intervene: async () => { const h=get().selectedHex; if(!h) return; const rec=await api.intervene(get().selectedTool,h); set({lastIntervention:rec}); await get().loadChain(rec.id); await get().refresh(); },
}));
