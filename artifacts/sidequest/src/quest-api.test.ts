import test from 'node:test';
import assert from 'node:assert/strict';
import { requestQuest, toStops } from './quest-api.ts';

const quest = {
  mode:'ai', places_source:'live', model:'test-model', title:'Test quest', intro:'Look closer.',
  badge_name:'Test Explorer', warnings:['Check paths.'], requested_minutes:45, requested_budget:0,
  stops:[1,2,3].map(i=>({place_id:`node/${i}`,name:`Place ${i}`,lat:34.057+i/10000,
    lon:-117.8214,category:'park',fee:'unknown',access:'unknown',challenge:'Observe a pattern.',photo_prompt:'Frame a detail.'})),
};
const preferences={lat:34.0572,lon:-117.8214,minutes:45,budget:0};

test('uses the real backend path and exact request fields',async()=>{
  const transport: typeof fetch=async(input,options)=>{
    assert.equal(input,'/api/quest');
    assert.deepEqual(JSON.parse(String(options?.body)),preferences);
    assert.ok(options?.signal);
    return Response.json(quest);
  };
  const result=await requestQuest(preferences,false,transport);
  assert.equal(result.badge_name,'Test Explorer');
});

test('maps source facts and creative text without inventing price or duration',()=>{
  const stop=toStops(quest as any)[0];
  assert.deepEqual(stop.coordinates,[quest.stops[0].lat,quest.stops[0].lon]);
  assert.equal(stop.photo,quest.stops[0].photo_prompt);
  assert.equal(stop.name,'Place 1');
  assert.equal(stop.cost,undefined);
  assert.equal(stop.duration,undefined);
});

test('explicit demo uses the demo endpoint and preserves mode',async()=>{
  const transport:typeof fetch=async(input)=>{
    assert.equal(input,'/api/demo-quest');
    return Response.json({...quest,mode:'demo',model:null,places_source:'demo'});
  };
  assert.equal((await requestQuest(preferences,true,transport)).mode,'demo');
});

test('shows the backend error message without substituting sample places',async()=>{
  const transport:typeof fetch=async()=>Response.json({error:{code:'places_unavailable',message:'Lookup unavailable.'}},{status:503});
  await assert.rejects(requestQuest(preferences,false,transport),/Lookup unavailable/);
});

test('rejects invalid coordinates and duplicated stop IDs before mapping',async()=>{
  for(const stops of [quest.stops.map(s=>({...s,lat:999})),quest.stops.map(s=>({...s,place_id:'same'}))]){
    const transport:typeof fetch=async()=>Response.json({...quest,stops});
    await assert.rejects(requestQuest(preferences,false,transport),/unexpected/);
  }
});
