"""Auto-optimizer for trailer loading with axle physics"""

import random
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
import numpy as np

@dataclass
class Item:
    consignment: str
    length_m: float
    width_m: float
    height_m: float
    mass_kg: float
    x_pos: float = 0
    y_pos: float = 0
    rotated: bool = False

@dataclass
class Trailer:
    name: str
    type_name: str
    length_m: float
    width_m: float
    deck_height_m: float
    max_payload_kg: float
    max_rear_axle_kg: float
    max_kingpin_kg: float
    wheelbase_m: float
    items: List[Item] = None
    
    def __post_init__(self):
        self.items = []
        self.total_mass_kg = 0
    
    def can_add_item(self, item: Item, x_pos: float, gap_m: float = 0.15) -> Tuple[bool, str]:
        """Check if item fits at given position"""
        # Check length boundaries
        if x_pos + item.length_m > self.length_m:
            return False, f"Exceeds trailer length (max {self.length_m}m)"
        
        # Check width boundaries (with safety margin)
        if item.width_m > self.width_m:
            return False, f"Width {item.width_m}m exceeds trailer {self.width_m}m"
        
        # Check weight capacity
        if self.total_mass_kg + item.mass_kg > self.max_payload_kg:
            return False, f"Would exceed payload {self.max_payload_kg:.0f}kg"
        
        # Check collision with existing items
        for existing in self.items:
            if (x_pos < existing.x_pos + existing.length_m + gap_m and
                x_pos + item.length_m + gap_m > existing.x_pos):
                return False, f"Collision with {existing.consignment}"
        
        return True, "OK"
    
    def add_item(self, item: Item, x_pos: float, y_pos: float = 0.15):
        item.x_pos = x_pos
        item.y_pos = y_pos
        self.items.append(item)
        self.total_mass_kg += item.mass_kg
    
    def calculate_axle_loads(self) -> Tuple[float, float, float]:
        """Calculate kingpin (front) and rear axle loads"""
        if not self.items:
            return 0, 0, 0
        
        total_moment = 0
        for item in self.items:
            cog_x = item.x_pos + (item.length_m / 2)
            total_moment += item.mass_kg * cog_x
        
        combined_cog = total_moment / self.total_mass_kg
        
        # Lever principle: Rear load = (CoG / wheelbase) * total
        rear_load = (combined_cog / self.wheelbase_m) * self.total_mass_kg
        front_load = self.total_mass_kg - rear_load
        
        return front_load, rear_load, combined_cog
    
    def is_safe(self) -> Tuple[bool, List[str]]:
        """Check if load meets all safety requirements"""
        front, rear, cog = self.calculate_axle_loads()
        violations = []
        
        if front > self.max_kingpin_kg:
            violations.append(f"Kingpin overload: {front:.0f}/{self.max_kingpin_kg:.0f}kg")
        if rear > self.max_rear_axle_kg:
            violations.append(f"Rear axle overload: {rear:.0f}/{self.max_rear_axle_kg:.0f}kg")
        if front < self.total_mass_kg * 0.15:
            violations.append(f"Insufficient steering weight: {front:.0f}kg")
        
        return len(violations) == 0, violations

class AutoOptimizer:
    def __init__(self, items: List[Item], trailer: Trailer, 
                 gap_m: float = 0.15, iterations: int = 100):
        self.items = items
        self.trailer = trailer
        self.gap_m = gap_m
        self.iterations = iterations
        self.gap_allowed_m = 0.2  # 20cm between items
        
    def try_pack_sequence(self, sequence: List[Item]) -> Optional[Trailer]:
        """Try to pack items in given sequence"""
        test_trailer = Trailer(
            name=self.trailer.name,
            type_name=self.trailer.type_name,
            length_m=self.trailer.length_m,
            width_m=self.trailer.width_m,
            deck_height_m=self.trailer.deck_height_m,
            max_payload_kg=self.trailer.max_payload_kg,
            max_rear_axle_kg=self.trailer.max_rear_axle_kg,
            max_kingpin_kg=self.trailer.max_kingpin_kg,
            wheelbase_m=self.trailer.wheelbase_m
        )
        
        current_x = 0.2  # Start 20cm from front
        
        for item in sequence:
            # Try both orientations (if beneficial)
            best_item = item
            if item.length_m > item.width_m:
                # Try rotating 90 degrees if it fits better
                rotated_item = Item(
                    consignment=item.consignment,
                    length_m=item.width_m,
                    width_m=item.length_m,
                    height_m=item.height_m,
                    mass_kg=item.mass_kg,
                    rotated=True
                )
                can_fit_original, _ = test_trailer.can_add_item(item, current_x, self.gap_allowed_m)
                can_fit_rotated, _ = test_trailer.can_add_item(rotated_item, current_x, self.gap_allowed_m)
                
                if can_fit_rotated and not can_fit_original:
                    best_item = rotated_item
            
            can_fit, reason = test_trailer.can_add_item(best_item, current_x, self.gap_allowed_m)
            if not can_fit:
                return None
            
            test_trailer.add_item(best_item, current_x, 0.15)
            current_x += best_item.length_m + self.gap_allowed_m
        
        return test_trailer
    
    def optimize(self) -> Tuple[Optional[Trailer], Dict]:
        """Find optimal packing sequence"""
        best_trailer = None
        best_imbalance = float('inf')
        best_front = 0
        best_rear = 0
        
        # Sort items by mass (heavier first) for better weight distribution
        sorted_items = sorted(self.items, key=lambda x: x.mass_kg, reverse=True)
        
        for iteration in range(self.iterations):
            # Shuffle lighter items, keep heaviest roughly in place
            if iteration > 0:
                to_shuffle = sorted_items[1:len(sorted_items)//2] if len(sorted_items) > 2 else sorted_items
                random.shuffle(to_shuffle)
                sequence = [sorted_items[0]] + to_shuffle + sorted_items[len(sorted_items)//2:]
            else:
                sequence = sorted_items
            
            result = self.try_pack_sequence(sequence)
            if result and result.is_safe()[0]:
                front, rear, _ = result.calculate_axle_loads()
                imbalance = abs(front - rear)
                
                if imbalance < best_imbalance:
                    best_imbalance = imbalance
                    best_trailer = result
                    best_front = front
                    best_rear = rear
        
        metrics = {
            "attempts": self.iterations,
            "best_imbalance_kg": best_imbalance if best_trailer else None,
            "best_front_load_kg": best_front if best_trailer else None,
            "best_rear_load_kg": best_rear if best_trailer else None,
            "total_items": len(self.items),
            "total_mass_kg": sum(i.mass_kg for i in self.items)
        }
        
        return best_trailer, metrics