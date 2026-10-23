import test from 'node:test';
import assert from 'node:assert/strict';
import { fetchNearbyPOIs, generateQuest, CPP_PRESET } from './overpass.js';

test('default CPP lookup uses the backend and returns source metadata', async () => {
  const original = globalThis.fetch;
  globalThis.fetch = async (url, options) => {
    assert.equal(url, '/api/places');
    assert.deepEqual(JSON.parse(options.body), { ...CPP_PRESET, minutes:45, budget:0 });
    return {ok:true,json:async()=>({places:[],source:'cache',warnings:[]})};
  };
  try { assert.equal((await fetchNearbyPOIs()).source,'cache'); }
  finally { globalThis.fetch=original; }
});

test('quest sends preferences, never a browser API key', async () => {
  const original=globalThis.fetch;
  const prefs={...CPP_PRESET,minutes:60,budget:10};
  globalThis.fetch=async (url,options)=>{
    assert.equal(url,'/api/quest');
    assert.deepEqual(JSON.parse(options.body),prefs);
    return {ok:true,json:async()=>({mode:'ai',stops:[]})};
  };
  try { assert.equal((await generateQuest(prefs)).mode,'ai'); }
  finally { globalThis.fetch=original; }
});

test('lookup errors stay errors instead of silently returning invented places', async()=>{
  const original=globalThis.fetch;
  globalThis.fetch=async()=>({ok:false,json:async()=>({error:{code:'places_unavailable',message:'Try later.'}})});
  try { await assert.rejects(fetchNearbyPOIs(), {message:'Try later.',code:'places_unavailable'}); }
  finally {globalThis.fetch=original;}
});
