"""Flask API; run from repo root: python -m backend.app."""
import os
from pathlib import Path
from flask import Flask, jsonify, request, send_file
from dotenv import load_dotenv
from pydantic import ValidationError
from werkzeug.exceptions import HTTPException
from .places import get_places, PlacesUnavailable, PlacesBatch
from .geocoding import geocode_location, LocationNotFound, LocationUnavailable
from .quest_ai import GroqCompletion, NoSuitablePlaces, generate_quest, basic_content, assemble, MODEL
from .schemas import QuestRequest, Place

ROOT = Path(__file__).resolve().parent.parent


def create_app(config=None, *, places_provider=None, completion=None, geocode_provider=None):
    load_dotenv(ROOT / '.env', override=False)
    app = Flask(__name__)
    app.config.update(MAX_CONTENT_LENGTH=65536, GROQ_API_KEY=os.getenv('GROQ_API_KEY', '').strip(),
                      GROQ_MODEL=os.getenv('GROQ_MODEL', MODEL).strip() or MODEL)
    if config:
        app.config.update(config)
    provider = places_provider or get_places
    geocoder = geocode_provider or geocode_location

    def error(code, message, status):
        return jsonify(error={'code':code,'message':message}), status

    @app.errorhandler(HTTPException)
    def http_error(exc):
        return error('http_error', exc.description, exc.code)

    @app.get('/')
    def index():
        return send_file(Path(__file__).parent / 'diagnostics.html')

    @app.get('/api/health')
    def health():
        return jsonify(status='ok', ai_configured=bool(app.config['GROQ_API_KEY']), model=app.config['GROQ_MODEL'])

    @app.post('/api/geocode')
    def geocode():
        raw = request.get_json()
        if not isinstance(raw, dict) or not isinstance(raw.get('location'), str):
            return error('invalid_location', 'Send a location string of 1 to 200 characters.', 422)
        location = raw['location'].strip()
        if not location or len(location) > 200:
            return error('invalid_location', 'Send a location string of 1 to 200 characters.', 422)
        try:
            result = geocoder(location)
        except LocationNotFound:
            return error('location_not_found', 'No matching location was found. Try an address, city, or landmark.', 422)
        except LocationUnavailable:
            return error('location_unavailable', 'The location lookup is unavailable. Try again in a moment.', 503)
        return jsonify(result)

    @app.post('/api/quest')
    @app.post('/api/places')
    def quest():
        raw = request.get_json()
        if not isinstance(raw, dict):
            return error('invalid_request', 'Send a JSON object with lat, lon, minutes and budget.', 422)
        try:
            preferences = QuestRequest.model_validate(raw)
        except ValidationError as exc:
            fields = sorted({str(e['loc'][0]) if e['loc'] else 'request' for e in exc.errors()})
            return error('invalid_request', 'Invalid fields: '+', '.join(fields)+'. See docs/BACKEND_HANDOFF.md.', 422)
        try:
            candidates = preferences.places if preferences.places is not None else provider(preferences)
            source = 'supplied' if preferences.places is not None else 'provider'
            place_warnings = []
            if isinstance(candidates, PlacesBatch):
                source, place_warnings = candidates.source, candidates.warnings
                candidates = candidates.places
            if not isinstance(candidates, (list, tuple)):
                raise PlacesUnavailable()
            candidates = [p if isinstance(p,Place) else Place.model_validate(p) for p in candidates]
        except (PlacesUnavailable, ValidationError, TypeError):
            return error('places_unavailable', 'Nearby-place lookup is unavailable or found too few places. Try again later; /api/demo-quest is an explicit synthetic test.', 503)
        if request.path == '/api/places':
            return jsonify(places=[p.model_dump() for p in candidates], source=source, warnings=place_warnings)
        ai = completion
        owned_ai = None
        try:
            if ai is None and app.config['GROQ_API_KEY']:
                owned_ai = GroqCompletion(api_key=app.config['GROQ_API_KEY'], model=app.config['GROQ_MODEL'])
                ai = owned_ai
            result = generate_quest(preferences, candidates, ai)
            result.places_source = source
            result.warnings.extend(place_warnings)
            return jsonify(result.model_dump())
        except NoSuitablePlaces as exc:
            return error('no_suitable_places', str(exc), 422)
        finally:
            if owned_ai is not None:
                owned_ai.close()

    @app.post('/api/demo-quest')
    def demo():
        preferences = QuestRequest(lat=34.06,lon=-117.82,minutes=45,budget=0)
        places = [Place(place_id=f'demo/{i}',name=f'Synthetic sample stop {i}',
                        lat=lat,lon=-117.82,category='sample')
                  for i,lat in enumerate((34.0601,34.0602,34.0603),1)]
        result = assemble(preferences, places, basic_content(places), 'demo',
            ['Synthetic sample locations for backend testing only; not verified destinations or live AI output.'])
        result.places_source = 'demo'
        return jsonify(result.model_dump())

    return app


if __name__ == '__main__':
    create_app().run(host='127.0.0.1', port=5050, debug=False)
