import { useEffect, useMemo, useState } from 'react';
import { CircleMarker, MapContainer, Marker, Polyline, TileLayer, useMap } from 'react-leaflet';
import L from 'leaflet';
import {
  ArrowDownRight, ArrowRight, BadgeCheck, Camera, Check, CheckCircle2, ChevronDown,
  Clock3, Compass, Flag, MapPin, RotateCcw, Sparkles, Wallet,
} from 'lucide-react';
import 'leaflet/dist/leaflet.css';
import { requestQuest, toStops, type Stop, type QuestResponse } from './quest-api';

const portlandStops: Stop[] = [
  {
    id: 1, name: 'Pioneer Courthouse Square', area: 'The city’s living room',
    coordinates: [45.5189, -122.6793], duration: 8, cost: 0,
    challenge: 'Find the smallest detail in the square that most people walk past. Tell your crew why it caught your eye.',
    photo: 'Frame the square like a postcard, but put something tiny in the foreground.',
    detail: 'A good quest starts by looking closer.',
  },
  {
    id: 2, name: 'Director Park', area: 'An urban pocket garden',
    coordinates: [45.5162, -122.6806], duration: 10, cost: 0,
    challenge: 'Take one minute to sit. Spot three different kinds of motion without getting up.',
    photo: 'Capture a reflection, a shadow, or another little bit of movement.',
    detail: 'A pause counts as progress.',
  },
  {
    id: 3, name: 'Portland Art Museum steps', area: 'South Park Blocks',
    coordinates: [45.5163, -122.6832], duration: 12, cost: 0,
    challenge: 'Pick a shape in the architecture. Everyone in the group has ten seconds to find it somewhere else.',
    photo: 'Make a portrait where the building becomes your backdrop.',
    detail: 'Look up. The city has been posing for you.',
  },
  {
    id: 4, name: 'Ladd’s Addition Coffee', area: 'A neighborhood pick-me-up',
    coordinates: [45.514, -122.6782], duration: 15, cost: 6,
    challenge: 'Order something you have never tried. Give it a one-word review before the first sip.',
    photo: 'Photograph the little ritual of your coffee break, not just the cup.',
    detail: 'A tiny treat makes a fine checkpoint.',
  },
  {
    id: 5, name: 'South Park Blocks', area: 'A leafy finish line',
    coordinates: [45.512, -122.6835], duration: 12, cost: 0,
    challenge: 'Choose a tree that feels like your quest mascot. Give it a name as a group.',
    photo: 'Get a final crew shot with your new mascot in the frame.',
    detail: 'Every adventure deserves a closing scene.',
  },
];

type PresetLocation = {
  label: string;
  mapLabel: string;
  mapCenter: [number, number];
  coordinateLabel: [string, string];
  stops: Stop[];
};

type CurrentCoordinates = {
  latitude: number;
  longitude: number;
};

type StartLocation = 'portland' | 'cal-poly-pomona' | 'current';
type WorkspaceTab = 'plan' | 'route';

const pomonaStops: Stop[] = [
  {
    id: 1, name: 'Bronco Student Center', area: 'The campus gathering place',
    coordinates: [34.0573, -117.8211], duration: 8, cost: 0,
    challenge: 'Spot a detail in the campus architecture that feels unmistakably Cal Poly Pomona. Compare picks with your crew.',
    photo: 'Frame your group with a campus landmark in the background.',
    detail: 'A good quest starts by looking closer.',
  },
  {
    id: 2, name: 'CLA Building', area: 'A campus landmark',
    coordinates: [34.0586, -117.8208], duration: 10, cost: 0,
    challenge: 'Look up and find an unexpected shape in the building. Each person gets one guess.',
    photo: 'Use the building’s lines to make a geometric photo.',
    detail: 'Look up. The city has been posing for you.',
  },
  {
    id: 3, name: 'University Library', area: 'A quieter corner of campus',
    coordinates: [34.0562, -117.8220], duration: 12, cost: 0,
    challenge: 'Find a spot that feels made for a quick reset. Take a quiet minute before moving on.',
    photo: 'Capture a small detail that makes this corner feel calm.',
    detail: 'A pause counts as progress.',
  },
  {
    id: 4, name: 'Kellogg House area', area: 'A historic campus stop',
    coordinates: [34.0544, -117.8163], duration: 15, cost: 6,
    challenge: 'Notice one old and one new detail nearby. Make up a short story about how they ended up together.',
    photo: 'Pair a historic detail with something modern in one frame.',
    detail: 'A tiny treat makes a fine checkpoint.',
  },
  {
    id: 5, name: 'Campus gardens', area: 'A leafy finish line',
    coordinates: [34.0555, -117.8190], duration: 12, cost: 0,
    challenge: 'Choose a plant that feels like your quest mascot. Give it a name as a group.',
    photo: 'Get a final crew shot with your new mascot in the frame.',
    detail: 'Every adventure deserves a closing scene.',
  },
];

const locations: Record<'portland' | 'cal-poly-pomona', PresetLocation> = {
  portland: {
    label: 'Downtown Portland',
    mapLabel: 'central Portland, Oregon',
    mapCenter: [45.5162, -122.6808],
    coordinateLabel: ['45°31′N', '122°40′W'],
    stops: portlandStops,
  },
  'cal-poly-pomona': {
    label: 'Cal Poly Pomona campus',
    mapLabel: 'Cal Poly Pomona campus',
    mapCenter: [34.0572, -117.8214],
    coordinateLabel: ['34°03′N', '117°49′W'],
    stops: pomonaStops,
  },
};

const markerIcon = (number: number, done: boolean) => L.divIcon({
  className: 'leaflet-div-icon',
  html: `<span class="quest-marker ${done ? 'is-done' : ''}">${done ? '✓' : number}</span>`,
  iconSize: [34, 34],
  iconAnchor: [17, 17],
});

function MapFocus({ selected, stops, center }: { selected: number; stops: Stop[]; center: [number, number] }) {
  const map = useMap();
  const target = stops.find((stop) => stop.id === selected);
  useEffect(() => {
    if (target) map.flyTo(target.coordinates, 16, { duration: 0.7 });
    else map.flyTo(center, 15, { duration: 0.7 });
  }, [map, target, center]);
  return null;
}

function App() {
  const [activeTab, setActiveTab] = useState<WorkspaceTab>('plan');
  const [start, setStart] = useState<StartLocation>('cal-poly-pomona');
  const [time, setTime] = useState(60);
  const [budget, setBudget] = useState(10);
  const [activeStops, setActiveStops] = useState<Stop[]>(locations['cal-poly-pomona'].stops);
  const [currentCoordinates, setCurrentCoordinates] = useState<CurrentCoordinates | null>(null);
  const [completed, setCompleted] = useState<number[]>([]);
  const [revealed, setRevealed] = useState<number[]>([]);
  const [selected, setSelected] = useState(1);
  const [started, setStarted] = useState(false);
  const [isRequestingLocation, setIsRequestingLocation] = useState(false);
  const [isPlanning, setIsPlanning] = useState(false);
  const [isGeneratedQuest, setIsGeneratedQuest] = useState(false);
  const [status, setStatus] = useState('');
  const [questDetails, setQuestDetails] = useState<QuestResponse | null>(null);
  const [planningError, setPlanningError] = useState('');
  const [locationError, setLocationError] = useState('');


  const currentMapCenter = useMemo<[number, number]>(
    () => currentCoordinates
      ? [currentCoordinates.latitude, currentCoordinates.longitude]
      : locations['cal-poly-pomona'].mapCenter,
    [currentCoordinates],
  );
  const location: PresetLocation = start === 'current'
    ? {
      label: 'your current location',
      mapLabel: 'your current location',
      mapCenter: currentMapCenter,
      coordinateLabel: currentCoordinates
        ? [currentCoordinates.latitude.toFixed(3), currentCoordinates.longitude.toFixed(3)]
        : ['', ''],
      stops: [],
    }
    : locations[start];
  const doneCount = completed.length;
  const finished = activeStops.length > 0 && doneCount === activeStops.length;
  const routePoints = useMemo(() => activeStops.map((stop) => stop.coordinates), [activeStops]);
  const estimatedTime = activeStops.reduce((sum, stop) => sum + (stop.duration ?? 0), 0);
  const estimatedCost = activeStops.reduce((sum, stop) => sum + (stop.cost ?? 0), 0);

  const requestCurrentLocation = () => {
    setLocationError('');

    if (!navigator.geolocation) {
      const message =
        'Location is not available in this browser. Choose a preset neighborhood instead.';
      setLocationError(message);
      setStatus(message);
      return;
    }

    setIsRequestingLocation(true);
    setStatus('Waiting for location permission…');

    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        const nextCoordinates = {
          latitude: coords.latitude,
          longitude: coords.longitude,
        };

        setCurrentCoordinates(nextCoordinates);
        setStart('current');
        setActiveStops([]);
        setCompleted([]);
        setRevealed([]);
        setSelected(0);
        setStarted(false);
        setIsGeneratedQuest(false);
        setQuestDetails(null);
        setIsRequestingLocation(false);
        setLocationError('');
        setStatus(
          'Location ready. Tap “Find my quest” to send it to the quest service.',
        );
      },
      (error) => {
        setIsRequestingLocation(false);

        let message: string;

        if (error.code === 1) {
          message =
            'Location permission was denied. Choose a preset neighborhood or allow location access in your browser.';
        } else if (error.code === 2) {
          message =
            'Your location could not be determined. Try again or choose a preset neighborhood.';
        } else {
          message =
            'The location request timed out. Try again or choose a preset neighborhood.';
        }

        setLocationError(message);
        setStatus(message);
      },
      {
        enableHighAccuracy: false,
        maximumAge: 60_000,
        timeout: 15_000,
      },
    );
  };

  const planQuest = async (demo = false) => {
    if (start === 'current' && !currentCoordinates && !demo) {
      const message = 'Choose your current location first, or select a preset.';
      setLocationError(message);
      setStatus(message);
      return;
    }
    const [lat, lon] = location.mapCenter;
    setIsPlanning(true);
    setPlanningError('');
    setLocationError('');
    setStatus(demo ? 'Loading the synthetic backend demo…' : 'Finding nearby places and writing your quest…');
    try {
      const result = await requestQuest({lat, lon, minutes:time, budget}, demo);
      const generatedStops = toStops(result);
      if (demo) { setStart('cal-poly-pomona'); setCurrentCoordinates(null); }
      setActiveStops(generatedStops);
      setCompleted([]);
      setRevealed([]);
      setSelected(generatedStops[0].id);
      setStarted(true);
      setIsGeneratedQuest(true);
      setQuestDetails(result);
      setActiveTab('route');
      setStatus(demo ? 'Synthetic backend demo ready: these are test locations.'
        : `Your three-stop quest is ready. ${result.mode === 'ai' ? 'AI-generated activities.' : 'Basic template activities.'}`);
    } catch (error) {
      const message=error instanceof Error ? error.message : 'The quest service could not be reached. Try again.';
      setPlanningError(message);
      setActiveTab('plan');
      setStatus(message);
      setActiveStops([]);
      setCompleted([]);
      setRevealed([]);
      setSelected(0);
      setStarted(false);
      setIsGeneratedQuest(false);
      setQuestDetails(null);
    } finally {
      setIsPlanning(false);
    }
  };

  const changeLocation = (locationId: StartLocation) => {
    if (locationId === 'current') {
      setStart('current');
      setCurrentCoordinates(null);
      setActiveStops([]);
      setCompleted([]);
      setRevealed([]);
      setSelected(0);
      setStarted(false);
      setIsGeneratedQuest(false);
      setQuestDetails(null);
      setPlanningError('');
      requestCurrentLocation();
      return;
    }

    const nextLocation = locations[locationId];
    setStart(locationId);
    setCurrentCoordinates(null);
    setActiveStops(nextLocation.stops);
    setCompleted([]);
    setRevealed([]);
    setSelected(nextLocation.stops[0]?.id ?? 1);
    setStarted(false);
    setIsGeneratedQuest(false);
    setQuestDetails(null);
    setPlanningError('');
    setLocationError('');
    setStatus(`Showing the fixed demo route near ${nextLocation.label}.`);
  };

  const toggleDone = (id: number) => {
    const stop = activeStops.find((item) => item.id === id);
    const willComplete = !completed.includes(id);
    setCompleted((current) => willComplete ? [...current, id] : current.filter((item) => item !== id));
    if (willComplete) setStatus(`${stop?.name ?? 'Stop'} checked off. Nice work.`);
    else setStatus(`${stop?.name ?? 'Stop'} moved back to your quest list.`);
  };

  const togglePhoto = (id: number) => {
    setRevealed((current) => current.includes(id) ? current.filter((item) => item !== id) : [...current, id]);
  };

  const resetQuest = () => {
    setCompleted([]);
    setRevealed([]);
    setStarted(false);
    setStatus(questDetails ? 'Progress reset. Your current quest is ready to play again.'
      : 'Progress reset. The illustrative sample stops are ready.');
  };

  return (
    <main className="app-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="SideQuest home" data-testid="link-home">
          <span className="brand-mark"><Compass size={21} strokeWidth={2.1} /></span>
          <span>sidequest<span className="brand-period">.</span></span>
        </a>
        <div className="topbar-right">
          <span className="demo-chip"><span className="demo-dot" /> {planningError ? 'NO QUEST GENERATED' : questDetails ? `${questDetails.mode.toUpperCase()} QUEST · ${questDetails.places_source.toUpperCase()}` : 'SAMPLE · FIXED STOPS'}</span>
          <span className="avatar-button" aria-label="SideQuest demo">SQ</span>
        </div>
      </header>

      <section className="intro">
        <div className="intro-copy rise-in">
          <div className="eyebrow"><span className="eyebrow-line" /> A LITTLE DETOUR, A LOT OF STORY</div>
          <h1>Make today<br /><em>a side quest.</em></h1>
          <p>Good plans are overrated. Pick your window, rally your people, and see what’s just around the corner.</p>
          <div className="intro-foot"><Sparkles className="mini-stars" size={15} aria-hidden="true" /> Three tiny missions. One very good story.</div>
        </div>
        <div className="intro-stamp" aria-hidden="true">
          <span className="stamp-orbit">GO OUTSIDE · LOOK CLOSER · GO OUTSIDE ·</span>
          <Compass size={48} strokeWidth={1.2} />
          <span className="stamp-coordinates">{location.coordinateLabel[0]}<br />{location.coordinateLabel[1]}</span>
        </div>
      </section>

      <div className="workspace-tabs" role="group" aria-label="Quest sections">
        <button
          className="workspace-tab"
          type="button"
          aria-pressed={activeTab === 'plan'}
          onClick={() => setActiveTab('plan')}
          data-testid="button-tab-plan"
        >
          <span className="workspace-tab-number">01</span>
          <span className="workspace-tab-copy"><strong>Plan a quest</strong><small>Choose a starting point, time, and budget</small></span>
        </button>
        <button
          className="workspace-tab"
          type="button"
          aria-pressed={activeTab === 'route'}
          onClick={() => setActiveTab('route')}
          data-testid="button-tab-route"
        >
          <span className="workspace-tab-number">02</span>
          <span className="workspace-tab-copy"><strong>Map &amp; quests</strong><small>Explore the route and check off stops</small></span>
          <span className="workspace-tab-count" aria-label={`${activeStops.length} quest stops`}>{activeStops.length}</span>
        </button>
      </div>

      {activeTab === 'plan' && <section className="planner" aria-label="Quest planner">
        <div className="planner-title">
          <span className="planner-kicker">FIRST, THE BASICS</span>
          <span className="planner-note">{'Nearby places, with a little imagination.'}</span>
        </div>
        <div className="planner-fields">
          <label className="field-block" htmlFor="start">
            <span className="field-label"><MapPin size={14} /> START NEAR</span>
            <span className="select-shell">
              <select
                id="start"
                value={start}
                onChange={(event) => changeLocation(event.target.value as StartLocation)}
                disabled={isRequestingLocation || isPlanning}
                data-testid="input-start-location"
              >
                <option value="portland">Downtown Portland</option>
                <option value="cal-poly-pomona">Cal Poly Pomona campus</option>
                <option value="current">My current location</option>
              </select>
              <ChevronDown size={15} aria-hidden="true" />
            </span>
          </label>
          <label className="field-block" htmlFor="time">
            <span className="field-label"><Clock3 size={14} /> I HAVE</span>
            <span className="select-shell">
              <select id="time" value={time} onChange={(event) => setTime(Number(event.target.value))} disabled={isPlanning} data-testid="input-available-time">
                <option value={15} disabled>15 minutes · choose 30+ for three stops</option>
                <option value={30}>30 minutes</option>
                <option value={45}>45 minutes</option>
                <option value={60}>About an hour</option>
                <option value={90}>About 90 minutes</option>
                <option value={120}>2 hours</option>
                <option value={180}>3 hours</option>
              </select>
              <ChevronDown size={15} aria-hidden="true" />
            </span>
          </label>
          <label className="field-block" htmlFor="budget">
            <span className="field-label"><Wallet size={14} /> SPEND UP TO</span>
            <span className="select-shell">
              <select id="budget" value={budget} onChange={(event) => setBudget(Number(event.target.value))} disabled={isPlanning} data-testid="input-budget">
                <option value={0}>$0 · no purchases</option>
                <option value={5}>$5</option>
                <option value={10}>$10</option>
                <option value={15}>$15</option>
                <option value={20}>$20</option>
                <option value={30}>$30</option>
                <option value={50}>$50</option>
              </select>
              <ChevronDown size={15} aria-hidden="true" />
            </span>
          </label>
          <button className="plan-button" onClick={() => planQuest()} type="button" disabled={isPlanning || isRequestingLocation} data-testid="button-plan-quest">
            {isPlanning ? 'Finding quests…' : started ? 'Replan my quest' : 'Find my quest'} <ArrowRight size={17} />
          </button>
        </div>
        {(planningError || locationError) && (
          <p
            className="planner-error"
            role="alert"
            data-testid="error-quest-generation"
          >
            <strong>
              {locationError
                ? 'Could not get your location.'
                : 'Could not create a quest.'}
            </strong>{' '}
            {locationError || planningError}
            {planningError &&
              ' No new stops were generated. For the campus backup, choose Cal Poly Pomona campus.'}
          </p>
        )}
        <p className="fixture-note" data-testid="text-demo-disclaimer">
          <span className="fixture-pin" /> {start === 'current'
            ? 'Your coordinates go to the quest backend only after you tap “Find my quest”.'
            : `Choose Find my quest to load nearby places. Initial sample stops near ${location.label} are illustrative.`}
        </p>
        <button type="button" className="reset-button" onClick={() => planQuest(true)} disabled={isPlanning || isRequestingLocation} data-testid="button-backend-demo">Try synthetic backend demo</button>
        {status && <p className="planner-status" role="status" aria-live="polite" data-testid="status-planner-message">{status}</p>}
      </section>}

      {questDetails && <section className="quest-summary" aria-label="Generated quest">
        <h2>{questDetails.title}</h2><p>{questDetails.intro}</p>
        {questDetails.places_source==='snapshot' && <p>Using saved real CPP map data; live place lookup is unavailable.</p>}
        <details><summary>Quest notes ({questDetails.warnings.length})</summary><ul>{questDetails.warnings.map((warning,i)=><li key={i}>{warning}</li>)}</ul></details>
      </section>}

      {activeTab === 'route' && <section className="quest-layout" aria-label="Your neighborhood quest">
        <div className="map-column">
          <div className="section-heading map-heading">
            <div><span className="section-kicker">THE NEIGHBORHOOD</span><h2>{activeStops.length === 0
              ? planningError ? 'No quest generated yet.' : 'Choose a location to begin.'
              : `${activeStops.length} stops, one good loop.`}</h2></div>
            <div className="map-legend"><span className="legend-dot" /> {planningError ? 'NO STOPS' : isGeneratedQuest ? 'YOUR QUESTS' : start === 'current' ? 'YOUR LOCATION' : 'DEMO STOPS'}</div>
          </div>
          <div className="map-frame" data-testid="map-quest">
            <MapContainer center={location.mapCenter} zoom={15} scrollWheelZoom={false} zoomControl={true} className="quest-map" aria-label={`Interactive quest map of ${location.mapLabel}`}>
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              {routePoints.length > 1 && <Polyline positions={routePoints} pathOptions={{ color: '#df7650', weight: 4, opacity: 0.85, dashArray: '7 9' }} />}
              {activeStops.map((stop) => (
                <Marker
                  key={`${stop.id}:${stop.name}:${stop.coordinates.join(',')}`}
                  position={stop.coordinates}
                  icon={markerIcon(stop.id, completed.includes(stop.id))}
                  eventHandlers={{ click: () => setSelected(stop.id) }}
                  keyboard
                  title={`Stop ${stop.id}: ${stop.name}`}
                  alt={`Stop ${stop.id}: ${stop.name}`}
                />
              ))}
              {start === 'current' && currentCoordinates && (
                <CircleMarker
                  center={[currentCoordinates.latitude, currentCoordinates.longitude]}
                  radius={8}
                  pathOptions={{ color: '#ffffff', weight: 3, fillColor: '#2ec4b6', fillOpacity: 1 }}
                />
              )}
              <MapFocus selected={selected} stops={activeStops} center={location.mapCenter} />
            </MapContainer>
            <div className="map-count"><span>{activeStops.length}</span> STOPS <i /> <span>{questDetails ? questDetails.requested_minutes : estimatedTime}</span> {questDetails ? 'MIN AVAILABLE · NOT DIRECTIONS' : 'MIN · SAMPLE ESTIMATE'}</div>
          </div>
          <div className="map-caption">
            <span><ArrowDownRight size={16} /> Follow the dotted line, or pick a pin.</span>
            <button type="button" onClick={() => { setSelected(activeStops[0]?.id ?? 1); }} data-testid="button-reset-map">Back to start</button>
          </div>
          <aside className="side-note">
            <div className="note-mark"><Sparkles size={17} /></div>
            <p><strong>Keep it loose.</strong> The best part is the part you didn’t plan. Every challenge is an invitation, not a rule.</p>
          </aside>
        </div>

        <div className="stops-column">
          <div className="section-heading stops-heading">
            <div><span className="section-kicker">YOUR QUEST LOG</span><h2>Out there, waiting.</h2></div>
            <span className="progress-label" data-testid="status-quest-progress"><strong>{doneCount}</strong> / {activeStops.length} DONE</span>
          </div>
          <div className="progress-track" aria-label={`${doneCount} of ${activeStops.length} stops complete`} role="progressbar" aria-valuemin={0} aria-valuemax={activeStops.length} aria-valuenow={doneCount}>
            <span style={{ width: `${activeStops.length ? doneCount / activeStops.length * 100 : 0}%` }} />
          </div>

          {finished ? (
            <div className="finish-card rise-in" data-testid="status-quest-finished" role="status">
              <div className="badge-art"><BadgeCheck size={41} strokeWidth={1.45} /><span>FIELD<br />NOTES</span></div>
              <span className="section-kicker">QUEST COMPLETE</span>
              <h3>You made a day of it.</h3>
              <p>{doneCount} stops, a little wandering, and a story that’s yours now. That’s the good stuff.</p>
              <div className="badge-award"><span className="award-seal"><Flag size={17} /></span><span><b>{questDetails?.badge_name ?? 'Neighborhood Scout'}</b><small>SideQuest field badge · earned today</small></span><CheckCircle2 size={19} /></div>
              <button type="button" className="reset-button" onClick={resetQuest} data-testid="button-reset-quest"><RotateCcw size={15} /> Start over</button>
            </div>
          ) : activeStops.length === 0 ? (
            <div className="empty-quest" role="status">
              <MapPin size={20} aria-hidden="true" />
              <h3>Your quest stops will appear here.</h3>
              <p>Choose your time and budget, then find a quest to fill in this map and log.</p>
              <button type="button" onClick={() => setActiveTab('plan')} data-testid="button-return-to-planner">Choose quest settings <ArrowRight size={14} /></button>
            </div>
          ) : (
            <div className="stop-list">
              {activeStops.map((stop, index) => {
                const isDone = completed.includes(stop.id);
                const isRevealed = revealed.includes(stop.id);
                const isSelected = selected === stop.id;
                return (
                  <article className={`stop-card rise-in delay-${Math.min(index + 1, 3)} ${isSelected ? 'is-selected' : ''} ${isDone ? 'is-complete' : ''}`} key={stop.id} data-testid={`card-stop-${stop.id}`}>
                    <button className="stop-main" type="button" onClick={() => setSelected(stop.id)} aria-expanded={isSelected} data-testid={`button-select-stop-${stop.id}`}>
                      <span className={`stop-number ${isDone ? 'number-done' : ''}`}>{isDone ? <Check size={15} /> : String(stop.id).padStart(2, '0')}</span>
                      <span className="stop-heading">
                        <span className="stop-title">{stop.name}</span>
                        <span className="stop-area">{stop.area}</span>
                      </span>
                      <span className="stop-time">{stop.duration === undefined ? 'EXPLORE' : `${stop.duration} MIN`}</span>
                    </button>
                    {isSelected && (
                      <div className="stop-detail">
                        <p className="challenge-copy">{stop.challenge}</p>
                        <p className="stop-detail-note">{stop.detail}</p>
                        {isRevealed && <div className="photo-prompt" data-testid={`text-photo-prompt-${stop.id}`}><Camera size={15} /><span><b>PHOTO PROMPT</b>{stop.photo}</span></div>}
                        <div className="stop-actions">
                          <button type="button" className={`photo-button ${isRevealed ? 'photo-active' : ''}`} onClick={() => togglePhoto(stop.id)} aria-expanded={isRevealed} data-testid={`button-photo-prompt-${stop.id}`}>
                            <Camera size={15} /> {isRevealed ? 'Hide photo idea' : 'Reveal photo idea'}
                          </button>
                          <button type="button" className={`complete-button ${isDone ? 'complete-active' : ''}`} onClick={() => toggleDone(stop.id)} data-testid={`button-complete-stop-${stop.id}`}>
                            {isDone ? <><Check size={15} /> Done</> : <>Mark complete <ArrowRight size={15} /></>}
                          </button>
                        </div>
                      </div>
                    )}
                    {isDone && !isSelected && <span className="completed-tag"><CheckCircle2 size={13} /> COMPLETED</span>}
                  </article>
                );
              })}
            </div>
          )}
          {activeStops.length>0 && <div className="quest-totals">
            <span><Clock3 size={14} /> {questDetails ? `${questDetails.requested_minutes} MIN AVAILABLE` : `ABOUT ${estimatedTime} MIN`}</span><i />
            <span><Wallet size={14} /> {questDetails ? 'NO PURCHASE REQUIRED · FEES UNKNOWN' : `UP TO $${estimatedCost}`}</span>
            <span className="totals-foot">{questDetails ? questDetails.mode.toUpperCase() : 'SAMPLE ESTIMATE'}</span>
          </div>}
          <p className="live-status" role="status" aria-live="polite" data-testid="status-quest-message">{status}</p>
        </div>
      </section>}
      <footer className="footer">
        <div className="footer-brand"><span className="footer-mark"><Compass size={16} /></span> sidequest.</div>
        <span>Made for the time between plans.</span>
          <span className="footer-demo">{questDetails ? `${questDetails.mode.toUpperCase()} QUEST · ${questDetails.places_source.toUpperCase()} PLACES` : 'ILLUSTRATIVE SAMPLE STOPS'}</span>
      </footer>
    </main>
  );
}

export default App;
