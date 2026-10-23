/** The shared Python API is the source of quest facts and creative text. */
export type Stop = {
  id:number; name:string; area:string; coordinates:[number,number];
  duration?:number; cost?:number; challenge:string; photo:string; detail:string;
};
type ApiStop = {
  place_id:string; name:string; lat:number; lon:number; category:string;
  challenge:string; photo_prompt:string;
};
export type QuestResponse = {
  mode:'ai'|'basic'|'demo'; places_source:string; model:string|null;
  title:string; intro:string; badge_name:string; warnings:string[]; stops:ApiStop[];
  requested_minutes:number; requested_budget:number;
};
export type Preferences = {lat:number;lon:number;minutes:number;budget:number};

function record(value:unknown): value is Record<string,unknown> {
  return !!value && typeof value==='object';
}
function text(value:unknown): value is string {
  return typeof value==='string' && value.trim().length>0;
}
function coordinate(value:unknown,limit:number): value is number {
  return typeof value==='number' && Number.isFinite(value) && Math.abs(value)<=limit;
}
function validQuest(value:unknown): value is QuestResponse {
  if(!record(value) || !['ai','basic','demo'].includes(String(value.mode)) ||
    !['live','cache','stale_cache','supplied','provider','demo','snapshot'].includes(String(value.places_source)) ||
    !(value.model===null || text(value.model)) ||
    !text(value.title) || !text(value.intro) || !text(value.badge_name) ||
    !Array.isArray(value.warnings) || !value.warnings.every(text) ||
    !Array.isArray(value.stops) || value.stops.length!==3 ||
    typeof value.requested_minutes!=='number' || typeof value.requested_budget!=='number') return false;
  const stops=value.stops;
  return stops.every(s=>record(s) && text(s.place_id) && text(s.name) &&
    text(s.category) && coordinate(s.lat,90) && coordinate(s.lon,180) &&
    text(s.challenge) && text(s.photo_prompt)) &&
    new Set(stops.map(s=>s.place_id)).size===3;
}

export async function requestQuest(preferences:Preferences,demo=false,transport:typeof fetch=fetch):Promise<QuestResponse> {
  const response=await transport(demo?'/api/demo-quest':'/api/quest', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body:JSON.stringify(demo?{}:preferences), signal:AbortSignal.timeout(45000),
  });
  const result:unknown=await response.json().catch(()=>null);
  if(!response.ok) {
    const message=record(result) && record(result.error) && text(result.error.message)
      ?result.error.message:'The quest service could not be reached. Try again.';
    throw new Error(message);
  }
  if(!validQuest(result)) throw new Error('The quest service returned an unexpected response.');
  return result;
}

export function toStops(quest:QuestResponse):Stop[] {
  return quest.stops.map((s,i)=>({id:i+1,name:s.name,area:s.category,coordinates:[s.lat,s.lon],
    challenge:s.challenge,photo:s.photo_prompt,
    detail:'Check public paths, access and opening hours before visiting.'}));
}
