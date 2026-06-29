export type HexCell = { id:string; q:number; r:number; terrain:string; fertility:number; nation_id?:string; };
export type Nation = { id:string; name:string; color:string; stock_food:number; stock_wood:number; stock_stone:number; stock_iron:number; stock_gold:number; pop_farmers:number; pop_extractors:number; army_size:number; current_year:number; current_month:number; };
export type WorldEvent = { id:string; tick_number:number; title:string; description:string; nation_id?:string; hex_id?:string };
export type PolicyAction = { id:string; tick_number:number; nation_id:string; policy_key:string; status:string; year:number; month:number };
export type InterventionRecord = { id:string; tool_type:string; hex_id:string };
export type CausalLink = { id:string; sequence:number; link_type:string; target_type:string; target_id:string; description:string };

const json = async <T>(url:string, init?:RequestInit): Promise<T> => {
  const res = await fetch(url, { headers: {'Content-Type':'application/json'}, ...init });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
};
export const api = {
  init: () => json('/api/world/init', { method:'POST' }),
  reset: () => json('/api/world/reset', { method:'POST' }),
  tick: () => json<{tick_number:number; elapsed_ms:number; events:string[]; snapshot:unknown}>('/api/world/tick', { method:'POST' }),
  state: () => json('/api/world/state'),
  replay: (tick:number) => json(`/api/world/replay/${tick}`),
  map: () => json<HexCell[]>('/api/world/map'),
  nations: () => json<Nation[]>('/api/world/nations'),
  nation: (id:string) => json<Nation>(`/api/world/nation/${id}`),
  events: (page=1, limit=50) => json<WorldEvent[]>(`/api/world/events?page=${page}&limit=${limit}`),
  eventStream: () => new EventSource('/api/world/events/stream'),
  policies: () => json<PolicyAction[]>('/api/world/policies'),
  decisions: (nationId:string, year:number, month:number) => json<PolicyAction[]>(`/api/nation/${nationId}/decisions/${year}/${month}`),
  tradeRoutes: () => json('/api/world/trade-routes'),
  intervene: (tool_type:string, hex_id:string) => json<InterventionRecord>('/api/world/intervene', { method:'POST', body:JSON.stringify({ tool_type, hex_id }) }),
  chain: (id:string) => json<CausalLink[]>(`/api/world/intervention/${id}/chain`),
};
