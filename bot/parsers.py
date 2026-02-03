import re
import pyproj

def parse_google_maps(text):
    m = re.search(r"https://www\.google\.com/maps\?q=(-?\d+\.\d+),(-?\d+\.\d+)", text)
    if m:
        return float(m.group(1)), float(m.group(2))
    return None

def parse_wgs84(line):
    m = re.match(r"^\s*(-?\d+\.\d+),\s*(-?\d+\.\d+)(?:\s*;\s*(.+))?", line)
    if m:
        return float(m.group(1)), float(m.group(2)), m.group(3) or "Unnamed"
    return None

def parse_utm(line, name):
    m = re.match(r"^\s*(\d+\.?\d*)\s*,\s*(\d+\.?\d*)", line)
    if not m:
        return None

    utm = pyproj.Proj(proj="utm", zone=36, ellps="WGS84", north=True)
    lon, lat = utm(float(m.group(1)), float(m.group(2)), inverse=True)
    return lat, lon, name or "Unnamed"
