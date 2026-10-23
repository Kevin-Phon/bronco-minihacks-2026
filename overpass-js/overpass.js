/** Browser bridge for the team's Overpass collector (original: Berserk_Alert).
 * Normalization, caching and live Overpass requests now run in backend/places.py.
 * Use a same-origin /api proxy to Flask. No keys belong in browser code.
 */
export const CPP_PRESET = Object.freeze({ lat:34.0572, lon:-117.8214 });

async function post(path, preferences) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 45000);
  try {
    const response = await fetch(path, {
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify(preferences), signal:controller.signal,
    });
    const data = await response.json();
    if (!response.ok) {
      const error = new Error(data.error?.message || 'SideQuest request failed.');
      error.code = data.error?.code || 'request_failed';
      throw error;
    }
    return data;
  } finally {
    clearTimeout(timer);
  }
}

/** Returns {places, source, warnings}. Third argument is options, not radius. */
export function fetchNearbyPOIs(lat=CPP_PRESET.lat, lon=CPP_PRESET.lon,
                               {minutes=45, budget=0}={}) {
  return post('/api/places', {lat,lon,minutes,budget});
}

/** Preferred UI path: one call performs OSM lookup and validated AI generation. */
export function generateQuest({lat,lon,minutes,budget}) {
  return post('/api/quest', {lat,lon,minutes,budget});
}
