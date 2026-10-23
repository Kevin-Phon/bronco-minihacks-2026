"""Check the running local API. Default mode never requests live generation."""
import argparse
import json
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live-request', type=Path, help='JSON with real preferences/places; calls configured Groq')
    args = parser.parse_args()
    try:
        with urlopen('http://127.0.0.1:5050/api/health', timeout=5) as response:
            health = json.load(response)
        print('Server:', health['status'], '| AI key configured:', health['ai_configured'])
        path = '/api/quest' if args.live_request else '/api/demo-quest'
        payload = args.live_request.read_bytes() if args.live_request else b'{}'
        req = Request('http://127.0.0.1:5050'+path, data=payload,
                      headers={'Content-Type':'application/json'}, method='POST')
        with urlopen(req, timeout=30) as response:
            quest = json.load(response)
        print('Mode:', quest['mode'], '| Stops:', len(quest['stops']))
        expected = 'ai' if args.live_request else 'demo'
        if quest['mode'] != expected or len(quest['stops']) != 3:
            print('FAIL: expected', expected, 'with three stops. Check configuration and warnings.')
            return 1
        print('PASS: '+('live AI generation verified.' if args.live_request else 'local synthetic demo verified; live AI not tested.'))
        return 0
    except (URLError, OSError, ValueError, KeyError):
        print('FAIL: check the server, request file, places adapter, and API configuration. No secrets are printed.')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
