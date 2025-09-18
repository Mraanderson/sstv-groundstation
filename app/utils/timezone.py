from timezonefinder import TimezoneFinder

def get_timezone_for_coords(lat, lon):
    """
    Given latitude and longitude, return the timezone name.
    Returns None if it cannot be determined.
    """
    try:
        tf = TimezoneFinder()
        return tf.timezone_at(lat=lat, lng=lon)
    except Exception:
        return None
      
