import math

def get_color_with_transparency(base_color, percent):
    opacity = int((percent / 100) * 255)
    return f"{opacity:02x}{base_color}"

def fallback_polygon(lat, lon, size=10):
    delta = size / 111320
    return [
        (lat - delta, lon - delta),
        (lat - delta, lon + delta),
        (lat + delta, lon + delta),
        (lat + delta, lon - delta),
        (lat - delta, lon - delta)
    ]

def polygon_kml(coords, name, desc, color):
    coords_str = " ".join([f"{lon},{lat},0" for lat, lon in coords])
    return f"""
    <Placemark>
      <name>{name}</name>
      <description>{desc}</description>
      <Style>
        <PolyStyle>
          <color>{color}</color>
          <fill>1</fill>
          <outline>1</outline>
        </PolyStyle>
      </Style>
      <Polygon>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>{coords_str}</coordinates>
          </LinearRing>
        </outerBoundaryIs>
      </Polygon>
    </Placemark>
    """
