"""Trailer library with South African specifications"""

TRAILER_TYPES = {
    "Flatbed Standard": {
        "length_m": 13.6,
        "width_m": 2.4,
        "height_m": 2.6,  # Deck height + load space
        "max_payload_kg": 28000,
        "max_axle_load_rear_kg": 18000,
        "max_kingpin_load_kg": 12000,
        "wheelbase_m": 10.5,
        "axle_count": 3,
        "permit_required": False,
        "description": "Standard flatbed trailer, no permit required for standard loads"
    },
    "Low-Loader": {
        "length_m": 13.6,
        "width_m": 2.8,
        "height_m": 1.2,  # Lower deck for tall items
        "max_payload_kg": 35000,
        "max_axle_load_rear_kg": 22000,
        "max_kingpin_load_kg": 15000,
        "wheelbase_m": 9.5,
        "axle_count": 4,
        "permit_required": False,
        "description": "Low-bed trailer for tall/heavy gensets"
    },
    "Abnormal (Extendable)": {
        "length_m": 18.0,
        "width_m": 3.0,
        "height_m": 1.0,
        "max_payload_kg": 50000,
        "max_axle_load_rear_kg": 30000,
        "max_kingpin_load_kg": 18000,
        "wheelbase_m": 14.0,
        "axle_count": 6,
        "permit_required": True,
        "description": "Requires abnormal load permit (Section 81)"
    },
    "Super-Abnormal": {
        "length_m": 24.0,
        "width_m": 3.5,
        "height_m": 1.0,
        "max_payload_kg": 80000,
        "max_axle_load_rear_kg": 40000,
        "max_kingpin_load_kg": 25000,
        "wheelbase_m": 19.0,
        "axle_count": 8,
        "permit_required": True,
        "description": "Escort vehicles required, route approval needed"
    }
}

def get_trailer(trailer_name):
    """Return trailer specs by name"""
    return TRAILER_TYPES.get(trailer_name, TRAILER_TYPES["Flatbed Standard"])

def list_trailers():
    """Return list of available trailer types"""
    return list(TRAILER_TYPES.keys())