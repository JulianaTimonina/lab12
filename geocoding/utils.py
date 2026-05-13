from geopy.geocoders import Nominatim
from geopy.distance import geodesic

geolocator = Nominatim(user_agent="taxi_app")

def get_coordinates(address):
    location = geolocator.geocode(address)
    if location is None:
        raise ValueError(f"Address not found: {address}")
    return location.latitude, location.longitude

def calculate_distance(lat1, lon1, lat2, lon2):
    return geodesic((lat1, lon1), (lat2, lon2)).kilometers