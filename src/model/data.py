import json
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OSM_FILE = ROOT / "data/osm/explanada_cayala.json"
OSM_WAY = 1569890595             # "Arena Gallo", terreno de la Explanada Cayalá
OSM_API = f"https://api.openstreetmap.org/api/0.6/way/{OSM_WAY}/full.json"


def fetch_osm(force=False):
    if OSM_FILE.exists() and not force:
        return OSM_FILE
    req = urllib.request.Request(OSM_API, headers={"User-Agent": "uvg-cc3074-proyecto2"})
    data = json.load(urllib.request.urlopen(req, timeout=90))
    data["descargado"] = date.today().isoformat()
    OSM_FILE.parent.mkdir(parents=True, exist_ok=True)
    OSM_FILE.write_text(json.dumps(data, indent=1, ensure_ascii=False))
    return OSM_FILE


if __name__ == "__main__":
    print(fetch_osm(force=True))
