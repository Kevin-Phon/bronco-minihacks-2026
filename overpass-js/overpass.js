/**
 * SideQuest - Overpass API Data Collector
 * Fetches diverse POIs around a coordinate within a given radius (meters).
 */

// Offline Backup / Cached Sample Data (Emergency Fallback for Demos)
const DEMO_FALLBACK_DATA = [
  { id: 1, name: "Stargazer Park & Lawn", type: "park", lat: 34.058, lon: -117.750, tags: { leisure: "park" } },
  { id: 2, name: "The Foundry Coffee Lab", type: "cafe", lat: 34.059, lon: -117.752, tags: { amenity: "cafe" } },
  { id: 3, name: "Historic Clock Tower", type: "historic", lat: 34.060, lon: -117.751, tags: { historic: "monument" } },
  { id: 4, name: "Second Street Murals", type: "artwork", lat: 34.057, lon: -117.749, tags: { tourism: "artwork" } },
  { id: 5, name: "Dragonfly Books & Games", type: "shop", lat: 34.061, lon: -117.753, tags: { shop: "books" } }
];

/**
 * Fetch diverse POIs around a (lat, lon) location.
 * @param {number} lat - Latitude
 * @param {number} lon - Longitude
 * @param {number} radius - Search radius in meters (default 1500m ~ 1 mile)
 * @returns {Promise<Array>} Array of parsed POI objects
 */
async function fetchNearbyPOIs(lat = 34.0552, lon = -117.7499, radius = 1500) {
  const cacheKey = `sidequest_pois_${lat.toFixed(3)}_${lon.toFixed(3)}_${radius}`;

  // 1. Check local cache first
  const cached = localStorage.getItem(cacheKey);
  if (cached) {
    console.log("⚡ [Cache Hit] Loaded POIs from LocalStorage");
    return JSON.parse(cached);
  }

  // 2. Overpass QL Query: Mix 5 distinct category types
  const overpassQuery = `
    [out:json][timeout:15];
    (
      node["amenity"~"cafe|restaurant|ice_cream|bakery"](around:${radius},${lat},${lon});
      node["leisure"~"park|garden|playground|pitch"](around:${radius},${lat},${lon});
      node["tourism"~"artwork|museum|viewpoint|attraction"](around:${radius},${lat},${lon});
      node["historic"](around:${radius},${lat},${lon});
      node["shop"~"books|gift|craft|record_shop"](around:${radius},${lat},${lon});
    );
    out body 30;
  `;

  const url = "https://overpass-api.de/api/interpreter";

  try {
    console.log("🌐 Fetching live POI data from Overpass API...");
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: `data=${encodeURIComponent(overpassQuery)}`
    });

    if (!response.ok) throw new Error(`Overpass HTTP error! status: ${response.status}`);

    const data = await response.json();
    const rawElements = data.elements || [];

    if (rawElements.length === 0) {
      console.warn("⚠️ No elements found near coordinates. Using demo backup.");
      return DEMO_FALLBACK_DATA;
    }

    // 3. Process & Balance Category Types (Max 2 items per category)
    const processedPOIs = processAndMixPOIs(rawElements);

    // 4. Save to Local Cache
    localStorage.setItem(cacheKey, JSON.stringify(processedPOIs));
    console.log(`✅ Fetched and cached ${processedPOIs.length} balanced POIs.`);

    return processedPOIs;
  } catch (error) {
    console.error("❌ Overpass API failed or timed out. Falling back to offline demo data.", error);
    return DEMO_FALLBACK_DATA;
  }
}

/**
 * Filter and balance POIs so no single category dominates.
 */
function processAndMixPOIs(elements) {
  const categories = {
    food: [],
    park: [],
    culture: [],
    historic: [],
    shop: []
  };

  elements.forEach((el) => {
    if (!el.tags || !el.tags.name) return; // Skip unnamed spots

    const item = {
      id: el.id,
      name: el.tags.name,
      lat: el.lat,
      lon: el.lon,
      tags: el.tags
    };

    if (el.tags.amenity) categories.food.push(item);
    else if (el.tags.leisure) categories.park.push(item);
    else if (el.tags.tourism) categories.culture.push(item);
    else if (el.tags.historic) categories.historic.push(item);
    else if (el.tags.shop) categories.shop.push(item);
  });

  // Pick max 2 items per category to guarantee variety
  const balancedList = [];
  Object.keys(categories).forEach((cat) => {
    const items = categories[cat];
    // Shuffle array
    items.sort(() => 0.5 - Math.random());
    balancedList.push(...items.slice(0, 2));
  });

  // If we still don't have enough named spots, fallback
  return balancedList.length >= 3 ? balancedList : DEMO_FALLBACK_DATA;
}
