"""South African National Road Traffic Act compliance validator"""

class SARoadTrafficValidator:
    def __init__(self):
        # Act 93 of 1996 - Regulation 240 (Axle mass limits)
        self.axle_limits = {
            "single_steering": 9000,      # kg
            "single_non_steering": 9000,  # kg
            "tandem": 18000,               # kg
            "triaxle": 27000               # kg
        }
        # Regulation 242 - Load distribution requirements
        self.max_height_m = 4.3  # Legal max without permit
        self.max_width_standard_m = 2.55
        self.max_overhang_rear_m = 1.5  # Regulation 243
        self.max_overhang_front_m = 0.5
        
    def validate_height(self, total_height_m: float) -> dict:
        """Check if height exceeds legal limits"""
        if total_height_m <= 4.3:
            return {"compliant": True, "permit_required": False, "message": "Legal height"}
        elif total_height_m <= 4.8:
            return {"compliant": True, "permit_required": True, 
                    "message": f"Abnormal load - {total_height_m}m requires permit (Section 81)"}
        else:
            return {"compliant": False, "permit_required": True,
                    "message": f"Height {total_height_m}m exceeds legal max. Re-route required."}
    
    def validate_overhang(self, overhang_rear_m: float, overhang_front_m: float) -> dict:
        """Check overhang limits (Regulation 243)"""
        errors = []
        if overhang_rear_m > self.max_overhang_rear_m:
            errors.append(f"Rear overhang {overhang_rear_m}m exceeds {self.max_overhang_rear_m}m limit")
        if overhang_front_m > self.max_overhang_front_m:
            errors.append(f"Front overhang {overhang_front_m}m exceeds {self.max_overhang_front_m}m limit")
        return {"compliant": len(errors) == 0, "errors": errors}
    
    def validate_axle_loads(self, front_kg: float, rear_kg: float, 
                            max_front: float, max_rear: float) -> dict:
        """Check axle load limits"""
        violations = []
        if front_kg > max_front:
            violations.append(f"Kingpin load {front_kg:.0f}kg > {max_front:.0f}kg limit")
        if rear_kg > max_rear:
            violations.append(f"Rear axle load {rear_kg:.0f}kg > {max_rear:.0f}kg limit")
        
        # Steering axle regulation (minimum traction)
        if front_kg < (rear_kg * 0.15):
            violations.append(f"Insufficient kingpin load ({front_kg:.0f}kg) - steering risk")
            
        return {"compliant": len(violations) == 0, "violations": violations}
    
    def validate_combination(self, total_kg: float, max_combination_kg: float = 56000) -> dict:
        """Check if combination mass exceeds abnormal load threshold"""
        if total_kg > max_combination_kg:
            return {"compliant": True, "abnormal": True, 
                    "message": f"Total {total_kg:.0f}kg > 56t - Abnormal load permit required"}
        return {"compliant": True, "abnormal": False, "message": "Standard combination mass"}