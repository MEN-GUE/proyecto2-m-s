import json
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OSM_FILE = ROOT / "data/osm/explanada_cayala.json"
OSM_WAY = 688526225
MIRRORS = ["https://overpass-api.de/api/interpreter",
           "https://overpass.kumi.systems/api/interpreter",
           "https://overpass.private.coffee/api/interpreter"]


def fetch_osm(force=False):
    if OSM_FILE.exists() and not force:
        return OSM_FILE
    query = f"[out:json][timeout:60];way({OSM_WAY});out tags geom;"
    body = urllib.parse.urlencode({"data": query}).encode()
    for url in MIRRORS:
        try:
            req = urllib.request.Request(url, body, {"User-Agent": "uvg-cc3074-proyecto2"})
            data = json.load(urllib.request.urlopen(req, timeout=90))
            OSM_FILE.parent.mkdir(parents=True, exist_ok=True)
            OSM_FILE.write_text(json.dumps(data, indent=1, ensure_ascii=False))
            return OSM_FILE
        except Exception as e:
            print(f"{url}: {e}")
    raise RuntimeError("No se pudo descargar el poligono de OSM")


if __name__ == "__main__":
    print(fetch_osm(force=True))
