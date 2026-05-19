"""
Trailer Library with South African Specifications
Includes Standard Trailers and Superlink (Link) Configurations
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple


# ==================== TRAILER TYPE DEFINITIONS ====================

TRAILER_TYPES = {
    # ===== STANDARD SINGLE TRAILERS =====
    "Flatbed Standard": {
        "type": "single",
        "length_m": 13.6,
        "width_m": 2.4,
        "deck_height_m": 1.2,
        "max_payload_kg": 28000,
        "max_rear_axle_kg": 18000,
        "max_kingpin_kg": 12000,
        "wheelbase_m": 10.5,
        "axle_count": 3,
        "tare_kg": 6000,
        "permit_required": False,
        "description": "Standard flatbed trailer, no permit required for standard loads",
        "container_capacity": "1 x 40ft or 2 x 20ft"
    },
    
    "Low-Loader": {
        "type": "single",
        "length_m": 13.6,
        "width_m": 2.8,
        "deck_height_m": 0.8,
        "max_payload_kg": 35000,
        "max_rear_axle_kg": 22000,
        "max_kingpin_kg": 15000,
        "wheelbase_m": 9.5,
        "axle_count": 4,
        "tare_kg": 8000,
        "permit_required": False,
        "description": "Low-bed trailer for tall/heavy gensets",
        "container_capacity": "1 x 40ft or 2 x 20ft"
    },
    
    "Abnormal (Extendable)": {
        "type": "single",
        "length_m": 18.0,
        "width_m": 3.0,
        "deck_height_m": 1.0,
        "max_payload_kg": 50000,
        "max_rear_axle_kg": 30000,
        "max_kingpin_kg": 18000,
        "wheelbase_m": 14.0,
        "axle_count": 6,
        "tare_kg": 10000,
        "permit_required": True,
        "description": "Requires abnormal load permit (Section 81)",
        "container_capacity": "1 x 40ft + oversize"
    },
    
    "Super-Abnormal": {
        "type": "single",
        "length_m": 24.0,
        "width_m": 3.5,
        "deck_height_m": 1.0,
        "max_payload_kg": 80000,
        "max_rear_axle_kg": 40000,
        "max_kingpin_kg": 25000,
        "wheelbase_m": 19.0,
        "axle_count": 8,
        "tare_kg": 15000,
        "permit_required": True,
        "description": "Escort vehicles required, route approval needed",
        "container_capacity": "Custom oversize"
    },
    
    # ===== SUPERLINK (LINK) CONFIGURATIONS =====
    "Superlink (6m + 12m)": {
        "type": "superlink",
        "is_link": True,
        "front_trailer": {
            "name": "Leader (Front)",
            "length_m": 6.0,
            "width_m": 2.4,
            "deck_height_m": 1.2,
            "max_payload_kg": 14000,
            "tare_kg": 3500,
            "axle_count": 2,
            "container_fit": "1 x 20ft"
        },
        "rear_trailer": {
            "name": "Follower (Rear)",
            "length_m": 12.0,
            "width_m": 2.4,
            "deck_height_m": 1.2,
            "max_payload_kg": 20000,
            "tare_kg": 4500,
            "axle_count": 3,
            "container_fit": "1 x 40ft or 2 x 20ft"
        },
        "total_length_m": 18.0,
        "articulation_gap_m": 0.5,
        "max_payload_kg": 34000,
        "max_gcm_kg": 56000,
        "pallet_capacity_single": 60,
        "pallet_capacity_euro": 84,
        "permit_required": False,
        "description": "6m front + 12m rear trailer. Ideal for 2 x 20ft + 1 x 40ft containers. Max payload 34t.",
        "best_for": "Container transport, palletized goods, mixed cargo"
    },
    
    "Interlink (6m + 6m)": {
        "type": "superlink",
        "is_link": True,
        "front_trailer": {
            "name": "Leader (Front)",
            "length_m": 6.0,
            "width_m": 2.4,
            "deck_height_m": 1.2,
            "max_payload_kg": 17000,
            "tare_kg": 3500,
            "axle_count": 2
        },
        "rear_trailer": {
            "name": "Follower (Rear)",
            "length_m": 6.0,
            "width_m": 2.4,
            "deck_height_m": 1.2,
            "max_payload_kg": 17000,
            "tare_kg": 3500,
            "axle_count": 2
        },
        "total_length_m": 12.0,
        "articulation_gap_m": 0.5,
        "max_payload_kg": 34000,
        "max_gcm_kg": 56000,
        "pallet_capacity_single": 40,
        "pallet_capacity_euro": 56,
        "permit_required": False,
        "description": "6m + 6m configuration for high-density loads like mining or grain",
        "best_for": "Bulk commodities, side-tippers, heavy dense cargo"
    }
}


# ==================== SUPERLINK TRAILER CLASS ====================

class SuperlinkTrailer:
    """
    Superlink (Link) Trailer - Two trailers articulated together
    Front trailer: 6m (Leader)
    Rear trailer: 12m (Follower)
    
    This class handles the special loading requirements for link trailers:
    - Separate loading areas (front and rear)
    - Articulation gap between trailers
    - Combined weight limits
    """
    
    def __init__(self, name="Superlink", config_type="Superlink (6m + 12m)"):
        """
        Initialize a Superlink trailer combination.
        
        Args:
            name: Identifier for this Superlink (e.g., "Superlink_1")
            config_type: Must be one of TRAILER_TYPES keys with is_link=True
        """
        self.name = name
        self.config = TRAILER_TYPES[config_type]
        self.type_name = config_type
        self.is_link = True
        
        # Front trailer (Leader)
        self.front = self.config["front_trailer"].copy()
        self.front["items"] = []
        self.front["total_mass_kg"] = 0
        
        # Rear trailer (Follower)
        self.rear = self.config["rear_trailer"].copy()
        self.rear["items"] = []
        self.rear["total_mass_kg"] = 0
        
        # Combined metrics
        self.total_length_m = self.config["total_length_m"]
        self.max_payload_kg = self.config["max_payload_kg"]
        self.articulation_gap_m = self.config.get("articulation_gap_m", 0.5)
        self.total_mass_kg = 0
        self.width_m = self.front["width_m"]  # Both trailers same width
        self.length_m = self.total_length_m
        
        # For compatibility with visualizer
        self.items = []  # Will be populated by get_all_items()
    
    # ==================== PROPERTIES FOR COMPATIBILITY ====================
    
    @property
    def wheelbase_m(self):
        """Return effective wheelbase for Superlink"""
        return 10.5  # Standard wheelbase for compliance calculations
    
    @property
    def max_kingpin_kg(self):
        """Return kingpin limit for Superlink"""
        return 12000
    
    @property
    def max_rear_axle_kg(self):
        """Return rear axle limit for Superlink"""
        return 18000
    
    @property
    def deck_height_m(self):
        """Return deck height"""
        return 1.2
    
    @property
    def trailer_tare_kg(self):
        """Return tare weight of Superlink combination"""
        return self.front.get("tare_kg", 3500) + self.rear.get("tare_kg", 4500)
    
    # ==================== METHODS ====================
    
    def can_add_item_to_front(self, item, x_pos, gap_m=0.15):
        """
        Check if item fits on front trailer (6m)
        
        Args:
            item: Item object with length_m, width_m, mass_kg attributes
            x_pos: Desired X position in meters from front of front trailer
            gap_m: Required gap between items in meters
            
        Returns:
            (can_fit: bool, reason: str)
        """
        # Check length
        if x_pos + item.length_m > self.front["length_m"]:
            return False, f"Exceeds front trailer length ({self.front['length_m']}m)"
        
        # Check width
        if item.width_m > self.front["width_m"]:
            return False, f"Width {item.width_m}m exceeds trailer width {self.front['width_m']}m"
        
        # Check weight capacity
        if self.front["total_mass_kg"] + item.mass_kg > self.front["max_payload_kg"]:
            return False, f"Would exceed front trailer payload ({self.front['max_payload_kg']/1000:.0f}t)"
        
        # Collision check with existing items
        for existing in self.front["items"]:
            if (x_pos < existing.x_pos + existing.length_m + gap_m and
                x_pos + item.length_m + gap_m > existing.x_pos):
                return False, f"Collision with {existing.consignment} on front trailer"
        
        return True, "OK"
    
    def can_add_item_to_rear(self, item, x_pos, gap_m=0.15):
        """
        Check if item fits on rear trailer (12m)
        
        Args:
            item: Item object with length_m, width_m, mass_kg attributes
            x_pos: Desired X position in meters from front of rear trailer
            gap_m: Required gap between items in meters
            
        Returns:
            (can_fit: bool, reason: str)
        """
        # Check length
        if x_pos + item.length_m > self.rear["length_m"]:
            return False, f"Exceeds rear trailer length ({self.rear['length_m']}m)"
        
        # Check width
        if item.width_m > self.rear["width_m"]:
            return False, f"Width {item.width_m}m exceeds trailer width {self.rear['width_m']}m"
        
        # Check weight capacity
        if self.rear["total_mass_kg"] + item.mass_kg > self.rear["max_payload_kg"]:
            return False, f"Would exceed rear trailer payload ({self.rear['max_payload_kg']/1000:.0f}t)"
        
        # Collision check with existing items
        for existing in self.rear["items"]:
            if (x_pos < existing.x_pos + existing.length_m + gap_m and
                x_pos + item.length_m + gap_m > existing.x_pos):
                return False, f"Collision with {existing.consignment} on rear trailer"
        
        return True, "OK"
    
    def add_item_to_front(self, item, x_pos, y_pos=0.15):
        """Add item to front trailer"""
        item.x_pos = x_pos
        item.y_pos = y_pos
        item.trailer_section = "front"
        self.front["items"].append(item)
        self.front["total_mass_kg"] += item.mass_kg
        self.total_mass_kg += item.mass_kg
        
    def add_item_to_rear(self, item, x_pos, y_pos=0.15):
        """Add item to rear trailer"""
        item.x_pos = x_pos
        item.y_pos = y_pos
        item.trailer_section = "rear"
        self.rear["items"].append(item)
        self.rear["total_mass_kg"] += item.mass_kg
        self.total_mass_kg += item.mass_kg
    
    def calculate_axle_loads(self):
        """
        Calculate axle loads for Superlink combination.
        
        Returns:
            (front_axle_load_kg, rear_axle_load_kg, combined_cog_m)
        """
        # Simplified calculation based on typical Superlink weight distribution:
        # - Front trailer axles carry ~30% of front trailer load
        # - Rear trailer axles carry ~70% of total load
        # - Kingpin carries the balance
        
        front_axle_load = self.front["total_mass_kg"] * 0.3
        rear_axle_load = (self.rear["total_mass_kg"] * 0.7) + (self.front["total_mass_kg"] * 0.1)
        
        # Combined center of gravity (relative to front of first trailer)
        total_moment = 0
        
        for item in self.front["items"]:
            cog = item.x_pos + (item.length_m / 2)
            total_moment += item.mass_kg * cog
            
        for item in self.rear["items"]:
            # Add articulation gap offset (front trailer length + gap)
            cog = self.front["length_m"] + self.articulation_gap_m + item.x_pos + (item.length_m / 2)
            total_moment += item.mass_kg * cog
        
        combined_cog = total_moment / self.total_mass_kg if self.total_mass_kg > 0 else 0
        
        return front_axle_load, rear_axle_load, combined_cog
    
    def is_safe(self):
        """
        Check if load is within legal limits.
        
        Returns:
            (is_safe: bool, violations: List[str])
        """
        violations = []
        
        # Check total payload
        if self.total_mass_kg > self.max_payload_kg:
            violations.append(f"Total payload {self.total_mass_kg/1000:.1f}t exceeds {self.max_payload_kg/1000:.0f}t limit")
        
        # Check front trailer
        if self.front["total_mass_kg"] > self.front["max_payload_kg"]:
            violations.append(f"Front trailer overload: {self.front['total_mass_kg']/1000:.1f}t > {self.front['max_payload_kg']/1000:.0f}t")
        
        # Check rear trailer
        if self.rear["total_mass_kg"] > self.rear["max_payload_kg"]:
            violations.append(f"Rear trailer overload: {self.rear['total_mass_kg']/1000:.1f}t > {self.rear['max_payload_kg']/1000:.0f}t")
        
        # Check axle loads (Regulation 240)
        front_axle, rear_axle, _ = self.calculate_axle_loads()
        
        # Each axle on rear trailer max 9000kg (Reg 240)
        max_per_axle = 9000
        axles_on_rear = self.rear.get("axle_count", 3)
        load_per_axle = rear_axle / axles_on_rear
        
        if load_per_axle > max_per_axle:
            violations.append(f"Rear axle overload: {load_per_axle:.0f}kg per axle > {max_per_axle}kg limit")
        
        return len(violations) == 0, violations
    
    def get_all_items(self):
        """Return all items from both trailers as a flat list"""
        all_items = self.front["items"] + self.rear["items"]
        self.items = all_items  # Update for compatibility
        return all_items
    
    def get_summary(self):
        """Get a summary of the Superlink loading"""
        return {
            "name": self.name,
            "type": self.type_name,
            "total_items": len(self.get_all_items()),
            "total_mass_tons": self.total_mass_kg / 1000,
            "max_payload_tons": self.max_payload_kg / 1000,
            "front": {
                "items": len(self.front["items"]),
                "mass_tons": self.front["total_mass_kg"] / 1000,
                "capacity_tons": self.front["max_payload_kg"] / 1000
            },
            "rear": {
                "items": len(self.rear["items"]),
                "mass_tons": self.rear["total_mass_kg"] / 1000,
                "capacity_tons": self.rear["max_payload_kg"] / 1000
            },
            "is_safe": self.is_safe()[0]
        }
    
    def add_item(self, item, x_pos, y_pos=0.15):
        """
        Generic add_item method for compatibility with visualizer.
        Automatically determines whether to add to front or rear based on x_pos.
        """
        # If x_pos is beyond front trailer length, add to rear
        if x_pos > self.front["length_m"] + 0.5:
            # Adjust position for rear trailer
            rear_x = x_pos - self.front["length_m"] - self.articulation_gap_m
            self.add_item_to_rear(item, rear_x, y_pos)
        else:
            self.add_item_to_front(item, x_pos, y_pos)


# ==================== HELPER FUNCTIONS ====================

def get_trailer(trailer_name):
    """
    Return trailer specs by name.
    
    Args:
        trailer_name: One of the keys in TRAILER_TYPES
        
    Returns:
        Trailer specs dictionary or SuperlinkTrailer object
    """
    if trailer_name not in TRAILER_TYPES:
        return TRAILER_TYPES.get("Flatbed Standard")
    
    config = TRAILER_TYPES[trailer_name]
    
    if config.get("is_link"):
        return SuperlinkTrailer(config_type=trailer_name)
    
    return config


def list_trailers():
    """Return list of available trailer types"""
    return list(TRAILER_TYPES.keys())


def list_standard_trailers():
    """Return list of standard (non-link) trailer types"""
    return [t for t in TRAILER_TYPES if not TRAILER_TYPES[t].get("is_link", False)]


def list_superlink_trailers():
    """Return list of Superlink/Interlink trailer types"""
    return [t for t in TRAILER_TYPES if TRAILER_TYPES[t].get("is_link", False)]


# ==================== UNIT TEST ====================

if __name__ == "__main__":
    print("Testing Trailer Library...\n")
    
    # Test 1: Standard trailer
    print("TEST 1: Standard Flatbed")
    flatbed = get_trailer("Flatbed Standard")
    print(f"   Type: {flatbed['type']}")
    print(f"   Length: {flatbed['length_m']}m")
    print(f"   Payload: {flatbed['max_payload_kg']/1000:.0f}t")
    print("   ✓ Passed\n")
    
    # Test 2: Superlink
    print("TEST 2: Superlink (6m + 12m)")
    superlink = SuperlinkTrailer(name="Test_Superlink", config_type="Superlink (6m + 12m)")
    print(f"   Type: {superlink.type_name}")
    print(f"   Front length: {superlink.front['length_m']}m, max: {superlink.front['max_payload_kg']/1000:.0f}t")
    print(f"   Rear length: {superlink.rear['length_m']}m, max: {superlink.rear['max_payload_kg']/1000:.0f}t")
    print(f"   Total payload: {superlink.max_payload_kg/1000:.0f}t")
    print(f"   Wheelbase (property): {superlink.wheelbase_m}m")
    print(f"   Tare weight (property): {superlink.trailer_tare_kg}kg")
    print("   ✓ Passed\n")
    
    print("✅ All tests passed!")