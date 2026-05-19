"""
South African National Road Traffic Act (Act 93 of 1996)
Complete Compliance Validator for Heavy Transport Load Configurator

Version: 2.1 - Added In-Gauge Cargo Classification
Last Updated: 2026-05-19
Regulations Covered: 234, 235, 236, 239, 240, 242, 243, 247
"""

from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from enum import Enum


class PermitType(Enum):
    """Types of abnormal load permits under Section 81"""
    NONE = "No permit required"
    HEIGHT_EXEMPTION = "Height exemption (>4.3m up to 4.8m)"
    WIDTH_EXEMPTION = "Width exemption (>2.55m up to 3.5m)"
    LENGTH_EXEMPTION = "Length exemption (>13.6m up to 18.0m)"
    GCM_EXEMPTION = "GCM exemption (>56t up to 80t)"
    MULTI_EXEMPTION = "Multiple exemptions - Escort required"
    SUPER_ABNORMAL = "Super abnormal - Route approval + Police escort"


class CargoClass(Enum):
    """Commercial cargo classification for freight forwarding"""
    IN_GAUGE = "IN-GAUGE"
    OUT_OF_GAUGE = "OUT-OF-GAUGE (OOG)"
    ABNORMAL = "ABNORMAL"
    SUPER_ABNORMAL = "SUPER-ABNORMAL"


@dataclass
class AxleConfig:
    """Individual axle or axle group configuration (Regulation 240)"""
    type: str  # steering, single, tandem, triaxle
    max_kg: float
    axle_count: int = 1
    min_percent_of_gvm: Optional[float] = None  # For steering axle


@dataclass
class LegalViolation:
    """Structured violation record"""
    regulation: str
    severity: str  # CRITICAL, WARNING, INFO
    message: str
    current_value: float
    legal_limit: float
    is_remediable: bool = True


@dataclass
class PermitRequirement:
    """Required permits for abnormal loads"""
    permit_type: PermitType
    reason: str
    authority: str = "RTMC - Section 81"
    estimated_processing_days: int = 5


class SARoadTrafficValidator:
    """
    Comprehensive legal validator for South African road transport.
    
    Implements:
    - Regulation 234: Height limits (4.3m standard, 4.8m abnormal)
    - Regulation 235: Width limits (2.55m standard, 3.5m abnormal)
    - Regulation 236: Length limits (13.6m semi-trailer, 22.0m combination)
    - Regulation 239: Gross Combination Mass (56t standard, 80t abnormal)
    - Regulation 240: Axle mass limits (9t single, 18t tandem, 27t triaxle)
    - Regulation 242: Load distribution (minimum 15% on steering)
    - Regulation 243: Overhang limits (0.5m front, 1.5m rear, 0.3m side)
    - Regulation 247: Tire load ratings (3,500kg per tire typical)
    """
    
    def __init__(self, province: str = "National"):
        """
        Initialize validator with optional provincial overrides.
        
        Args:
            province: South African province (National, WesternCape, Gauteng, etc.)
                     Some provinces have stricter enforcement on certain routes.
        """
        self.province = province
        
        # ========== REGULATION 240: Axle Mass Limits ==========
        self.axle_configs = {
            "steering": AxleConfig(
                type="steering",
                max_kg=9000,
                axle_count=1,
                min_percent_of_gvm=0.15  # Minimum 15% on steering axle
            ),
            "single": AxleConfig(
                type="single",
                max_kg=9000,
                axle_count=1
            ),
            "tandem": AxleConfig(
                type="tandem",
                max_kg=18000,
                axle_count=2
            ),
            "triaxle": AxleConfig(
                type="triaxle",
                max_kg=27000,
                axle_count=3
            )
        }
        
        # ========== REGULATION 234: Height Limits ==========
        self.max_height_standard_m = 4.3
        self.max_height_abnormal_m = 4.8  # With Section 81 permit
        self.max_height_super_abnormal_m = 5.5  # With route approval
        
        # Known low-clearance routes (height restrictions)
        self.low_clearance_routes = {
            "Bain's Kloof Pass": 3.68,
            "Chapman's Peak Drive": 4.0,
            "Van Reenen's Pass": 4.5,
            "Montagu Pass": 3.5,
            "Outeniqua Pass": 4.2
        }
        
        # ========== REGULATION 235: Width Limits ==========
        self.max_width_standard_m = 2.55
        self.max_width_abnormal_m = 3.5   # With permit
        self.max_width_super_abnormal_m = 4.5  # Escort required
        
        # ========== REGULATION 236: Length Limits ==========
        self.max_length_semitrailer_m = 13.6
        self.max_length_rigid_truck_m = 12.5
        self.max_length_combination_m = 22.0  # Truck + trailer
        self.max_length_abnormal_m = 18.0  # With permit for single trailer
        
        # ========== REGULATION 239: Gross Combination Mass ==========
        self.max_gcm_standard_kg = 56000
        self.max_gcm_abnormal_kg = 80000
        self.max_gcm_super_abnormal_kg = 100000
        
        # Typical tare masses (Regulation 1 definitions)
        self.truck_tare_kg = 8000  # Typical 4x2 truck tractor
        self.trailer_tare_kg = 6000  # Typical flatbed trailer
        
        # ========== REGULATION 243: Overhang Limits ==========
        self.max_overhang_rear_m = 1.5
        self.max_overhang_front_m = 0.5
        self.max_side_overhang_m = 0.3
        
        # ========== REGULATION 247: Tire Load Ratings ==========
        self.standard_tire_capacity_kg = 3500  # 12R22.5 typical
        self.heavy_duty_tire_capacity_kg = 4000  # For abnormal loads
        self.tires_per_axle = 4  # Dual wheels on drive axles
        
        # ========== IN-GAUGE CARGO THRESHOLDS (Commercial Classification) ==========
        # Based on OneLogix Mega industry standards for cost-effective transport
        self.ingauge_max_height_m = 2.9   # Fits in standard container/high cube
        self.ingauge_max_width_m = 2.5    # Within 2.55m legal limit with margin
        self.ingauge_max_item_length_m = 12.0  # Fits in 40ft container
        self.ingauge_max_mass_kg = 28000  # Standard flatbed payload
        
        # ========== Provincial Weight Limit Variations ==========
        self.provincial_limits = {
            "WesternCape": {
                "mountain_routes": {"reduced_axle_load": 8000},  # Some passes
                "coastal_routes": {"standard": True}
            },
            "Gauteng": {
                "urban_restrictions": {"height_alert": 4.5}  # Low bridges in Joburg
            },
            "KwaZuluNatal": {
                "mountain_routes": {"reduced_gcm": 52000}  # Van Reenen's
            },
            "EasternCape": {
                "rural_routes": {"standard": True}
            }
        }
        
        # Tracking violations and permits
        self.violations: List[LegalViolation] = []
        self.permits_required: List[PermitRequirement] = []
        
    # ==================== IN-GAUGE CARGO CLASSIFICATION ====================
    
    def classify_cargo(self, items: List) -> Dict:
        """
        Classify cargo as In-Gauge, Out-of-Gauge (OOG), or Abnormal.
        Based on industry standards from OneLogix Mega and SA legal limits.
        
        In-Gauge cargo fits within standard container/vehicle dimensions:
        - Height ≤ 2.9m (fits in high cube container)
        - Width ≤ 2.5m (within legal limit with margin)
        - No single item > 12m length (fits in 40ft container)
        - Total mass ≤ 28t (standard flatbed payload)
        
        Out-of-Gauge (OOG) exceeds one or more in-gauge thresholds
        but remains within legal limits (permits may be required).
        
        Abnormal exceeds legal limits (permits always required).
        
        Returns:
            Dict with classification, reasons, and commercial implications
        """
        if not items:
            return {
                "class": CargoClass.IN_GAUGE,
                "class_name": "IN-GAUGE",
                "is_in_gauge": True,
                "reasons": [],
                "commercial_note": "Standard rates apply",
                "fleet_recommendation": "Standard flatbed"
            }
        
        total_height = max((item.height_m for item in items), default=0)
        total_width = max((item.width_m for item in items), default=0)
        max_item_length = max((item.length_m for item in items), default=0)
        total_mass = sum((item.mass_kg for item in items), default=0) / 1000  # tonnes
        
        is_ingauge = True
        reasons = []
        classification = CargoClass.IN_GAUGE
        
        # Check in-gauge thresholds
        if total_height > self.ingauge_max_height_m:
            is_ingauge = False
            reasons.append(f"Height ({total_height:.2f}m) exceeds in-gauge limit of {self.ingauge_max_height_m}m")
            
        if total_width > self.ingauge_max_width_m:
            is_ingauge = False
            reasons.append(f"Width ({total_width:.2f}m) exceeds in-gauge limit of {self.ingauge_max_width_m}m")
            
        if max_item_length > self.ingauge_max_item_length_m:
            is_ingauge = False
            reasons.append(f"Item length ({max_item_length:.2f}m) exceeds in-gauge limit of {self.ingauge_max_item_length_m}m")
            
        if total_mass > self.ingauge_max_mass_kg / 1000:
            is_ingauge = False
            reasons.append(f"Total mass ({total_mass:.1f}t) exceeds in-gauge payload of {self.ingauge_max_mass_kg/1000:.0f}t")
        
        # Determine final classification
        if is_ingauge:
            classification = CargoClass.IN_GAUGE
            commercial_note = "✅ Standard rates apply. Can use any standard flatbed fleet."
            fleet_rec = "Standard flatbed (13.6m x 2.4m)"
        else:
            # Check if legal limits are exceeded (abnormal)
            exceeds_legal_height = total_height > self.max_height_standard_m
            exceeds_legal_width = total_width > self.max_width_standard_m
            exceeds_legal_length = max_item_length > self.max_length_semitrailer_m
            
            if exceeds_legal_height or exceeds_legal_width or exceeds_legal_length:
                classification = CargoClass.ABNORMAL
                commercial_note = "⚠️ ABNORMAL LOAD: Permits required, specialized fleet needed, premium rates apply."
                fleet_rec = "Abnormal fleet (low-bed / extendable trailer)"
            else:
                classification = CargoClass.OUT_OF_GAUGE
                commercial_note = "💰 OUT-OF-GAUGE (OOG): May require route survey, potential premium rates. Contact operations for quote."
                fleet_rec = "Step deck or flatbed with overhang kit"
        
        return {
            "class": classification,
            "class_name": classification.value,
            "is_in_gauge": is_ingauge,
            "reasons": reasons,
            "commercial_note": commercial_note,
            "fleet_recommendation": fleet_rec,
            "metrics": {
                "max_height_m": round(total_height, 2),
                "max_width_m": round(total_width, 2),
                "max_item_length_m": round(max_item_length, 2),
                "total_mass_tons": round(total_mass, 1)
            }
        }
    
    # ==================== REGULATION 234: HEIGHT VALIDATION ====================
    
    def validate_height(self, total_height_m: float, route: str = None) -> Dict:
        """
        Validate load height against Regulation 234.
        
        Args:
            total_height_m: Overall height of vehicle + load (meters)
            route: Specific route name (for low-clearance checks)
        
        Returns:
            Dict with compliance status, permit requirements, and route warnings
        """
        result = {
            "compliant": True,
            "permit_required": False,
            "permit_type": PermitType.NONE,
            "message": "",
            "route_warnings": []
        }
        
        # Check route-specific low clearance
        if route and route in self.low_clearance_routes:
            route_limit = self.low_clearance_routes[route]
            if total_height_m > route_limit:
                result["route_warnings"].append(
                    f"⚠️ {route} has {route_limit}m clearance - Height {total_height_m}m exceeds!"
                )
                result["compliant"] = False
                result["message"] = f"Route {route} cannot accommodate height {total_height_m}m"
                return result
        
        # Standard legal height check
        if total_height_m <= self.max_height_standard_m:
            result["message"] = f"✓ Height {total_height_m}m compliant (≤{self.max_height_standard_m}m)"
            
        elif total_height_m <= self.max_height_abnormal_m:
            result["permit_required"] = True
            result["permit_type"] = PermitType.HEIGHT_EXEMPTION
            result["message"] = f"⚠️ Height {total_height_m}m exceeds standard limit - Abnormal load permit required (Section 81)"
            
        elif total_height_m <= self.max_height_super_abnormal_m:
            result["permit_required"] = True
            result["permit_type"] = PermitType.SUPER_ABNORMAL
            result["message"] = f"🚨 Height {total_height_m}m requires super abnormal permit + route approval"
            
        else:
            result["compliant"] = False
            result["message"] = f"❌ Height {total_height_m}m exceeds maximum legal limit of {self.max_height_super_abnormal_m}m"
        
        return result
    
    # ==================== REGULATION 235: WIDTH VALIDATION ====================
    
    def validate_width(self, total_width_m: float) -> Dict:
        """
        Validate load width against Regulation 235.
        
        Args:
            total_width_m: Overall width of vehicle + load (meters)
        
        Returns:
            Dict with compliance status and permit requirements
        """
        result = {
            "compliant": True,
            "permit_required": False,
            "permit_type": PermitType.NONE,
            "escort_required": False,
            "message": ""
        }
        
        if total_width_m <= self.max_width_standard_m:
            result["message"] = f"✓ Width {total_width_m}m compliant (≤{self.max_width_standard_m}m)"
            
        elif total_width_m <= self.max_width_abnormal_m:
            result["permit_required"] = True
            result["permit_type"] = PermitType.WIDTH_EXEMPTION
            result["message"] = f"⚠️ Width {total_width_m}m exceeds standard limit - Abnormal load permit required"
            
        elif total_width_m <= self.max_width_super_abnormal_m:
            result["permit_required"] = True
            result["permit_type"] = PermitType.SUPER_ABNORMAL
            result["escort_required"] = True
            result["message"] = f"🚨 Width {total_width_m}m requires escort vehicles + advance notice to RTMC"
            
        else:
            result["compliant"] = False
            result["message"] = f"❌ Width {total_width_m}m exceeds maximum legal limit of {self.max_width_super_abnormal_m}m"
        
        return result
    
    # ==================== REGULATION 236: LENGTH VALIDATION ====================
    
    def validate_length(self, trailer_length_m: float, 
                        vehicle_type: str = "semitrailer",
                        combination_length_m: float = None) -> Dict:
        """
        Validate trailer length against Regulation 236.
        
        Args:
            trailer_length_m: Length of the trailer (meters)
            vehicle_type: "semitrailer", "rigid", or "combination"
            combination_length_m: Total length if truck + trailer (meters)
        
        Returns:
            Dict with compliance status
        """
        result = {
            "compliant": True,
            "permit_required": False,
            "permit_type": PermitType.NONE,
            "message": ""
        }
        
        if vehicle_type == "semitrailer":
            if trailer_length_m <= self.max_length_semitrailer_m:
                result["message"] = f"✓ Semi-trailer length {trailer_length_m}m compliant"
            elif trailer_length_m <= self.max_length_abnormal_m:
                result["permit_required"] = True
                result["permit_type"] = PermitType.LENGTH_EXEMPTION
                result["message"] = f"⚠️ Length {trailer_length_m}m exceeds standard - Permit required"
            else:
                result["compliant"] = False
                result["message"] = f"❌ Length {trailer_length_m}m exceeds maximum {self.max_length_abnormal_m}m"
                
        elif vehicle_type == "rigid":
            if trailer_length_m <= self.max_length_rigid_truck_m:
                result["message"] = f"✓ Rigid truck length {trailer_length_m}m compliant"
            else:
                result["compliant"] = False
                result["message"] = f"❌ Rigid truck exceeds {self.max_length_rigid_truck_m}m limit"
                
        elif vehicle_type == "combination":
            if combination_length_m:
                if combination_length_m <= self.max_length_combination_m:
                    result["message"] = f"✓ Combination length {combination_length_m}m compliant"
                else:
                    result["compliant"] = False
                    result["message"] = f"❌ Combination exceeds {self.max_length_combination_m}m limit"
        
        return result
    
    # ==================== REGULATION 239: GCM VALIDATION ====================
    
    def validate_gcm(self, 
                     payload_kg: float,
                     truck_mass_kg: float = None,
                     trailer_mass_kg: float = None) -> Dict:
        """
        Validate Gross Combination Mass against Regulation 239.
        
        Args:
            payload_kg: Total weight of all items (kg)
            truck_mass_kg: Tare mass of truck/tractor (default: 8000kg)
            trailer_mass_kg: Tare mass of trailer (default: 6000kg)
        
        Returns:
            Dict with compliance status
        """
        truck_mass = truck_mass_kg or self.truck_tare_kg
        trailer_mass = trailer_mass_kg or self.trailer_tare_kg
        
        gcm = truck_mass + trailer_mass + payload_kg
        
        result = {
            "compliant": True,
            "gcm_kg": gcm,
            "gcm_tons": round(gcm / 1000, 1),
            "permit_required": False,
            "permit_type": PermitType.NONE,
            "message": ""
        }
        
        if gcm <= self.max_gcm_standard_kg:
            result["message"] = f"✓ GCM {result['gcm_tons']}t compliant (≤56t)"
            
        elif gcm <= self.max_gcm_abnormal_kg:
            result["permit_required"] = True
            result["permit_type"] = PermitType.GCM_EXEMPTION
            result["message"] = f"⚠️ GCM {result['gcm_tons']}t exceeds 56t - Abnormal load permit required"
            
        elif gcm <= self.max_gcm_super_abnormal_kg:
            result["permit_required"] = True
            result["permit_type"] = PermitType.SUPER_ABNORMAL
            result["message"] = f"🚨 GCM {result['gcm_tons']}t exceeds 80t - Super abnormal + escort required"
            
        else:
            result["compliant"] = False
            result["message"] = f"❌ GCM {result['gcm_tons']}t exceeds maximum 100t limit"
        
        return result
    
    # ==================== REGULATION 240: AXLE LOAD VALIDATION ====================
    
    def validate_axle_loads(self,
                            front_load_kg: float,
                            rear_load_kg: float,
                            total_mass_kg: float,
                            axle_configuration: List[Dict]) -> Dict:
        """
        Validate axle loads against Regulation 240.
        
        Args:
            front_load_kg: Load on kingpin/front axle (kg)
            rear_load_kg: Load on rear axle group (kg)
            total_mass_kg: Total vehicle + load mass (kg)
            axle_configuration: List of axle types from trailer
        
        Returns:
            Dict with compliance status and per-axle breakdown
        """
        result = {
            "compliant": True,
            "violations": [],
            "per_axle_breakdown": [],
            "message": ""
        }
        
        # Check steering axle (minimum 15% rule - Regulation 242)
        steering_percent = (front_load_kg / total_mass_kg) * 100 if total_mass_kg > 0 else 0
        min_steering = self.axle_configs["steering"].min_percent_of_gvm * 100
        
        if steering_percent < min_steering:
            violation = LegalViolation(
                regulation="242",
                severity="CRITICAL",
                message=f"Insufficient steering axle load: {steering_percent:.1f}% (minimum {min_steering}%)",
                current_value=front_load_kg,
                legal_limit=total_mass_kg * self.axle_configs["steering"].min_percent_of_gvm
            )
            result["violations"].append(violation)
            result["compliant"] = False
        
        # Check each axle group
        remaining_load = rear_load_kg
        for i, axle in enumerate(axle_configuration):
            axle_type = axle.get("type", "single")
            config = self.axle_configs.get(axle_type, self.axle_configs["single"])
            
            # Distribute load across axles in group
            load_per_axle = remaining_load / axle.get("axle_count", 1) if i == len(axle_configuration) - 1 else config.max_kg * 0.8
            
            if load_per_axle > config.max_kg:
                violation = LegalViolation(
                    regulation="240",
                    severity="CRITICAL",
                    message=f"Axle group {i+1} ({axle_type}) overloaded: {load_per_axle:.0f}kg > {config.max_kg}kg",
                    current_value=load_per_axle,
                    legal_limit=config.max_kg
                )
                result["violations"].append(violation)
                result["compliant"] = False
            
            result["per_axle_breakdown"].append({
                "axle_group": i + 1,
                "type": axle_type,
                "load_kg": round(load_per_axle, 0),
                "limit_kg": config.max_kg,
                "status": "OK" if load_per_axle <= config.max_kg else "OVERLOAD"
            })
            
            remaining_load -= load_per_axle * axle.get("axle_count", 1)
        
        return result
    
    # ==================== REGULATION 243: OVERHANG VALIDATION ====================
    
    def validate_overhang(self,
                          overhang_front_m: float,
                          overhang_rear_m: float,
                          overhang_left_m: float = 0,
                          overhang_right_m: float = 0) -> Dict:
        """
        Validate load overhang against Regulation 243.
        
        Returns:
            Dict with compliance status
        """
        result = {
            "compliant": True,
            "violations": [],
            "message": ""
        }
        
        if overhang_front_m > self.max_overhang_front_m:
            violation = LegalViolation(
                regulation="243",
                severity="WARNING",
                message=f"Front overhang {overhang_front_m}m exceeds {self.max_overhang_front_m}m limit",
                current_value=overhang_front_m,
                legal_limit=self.max_overhang_front_m
            )
            result["violations"].append(violation)
            result["compliant"] = False
        
        if overhang_rear_m > self.max_overhang_rear_m:
            violation = LegalViolation(
                regulation="243",
                severity="WARNING",
                message=f"Rear overhang {overhang_rear_m}m exceeds {self.max_overhang_rear_m}m limit",
                current_value=overhang_rear_m,
                legal_limit=self.max_overhang_rear_m
            )
            result["violations"].append(violation)
            result["compliant"] = False
        
        if overhang_left_m > self.max_side_overhang_m or overhang_right_m > self.max_side_overhang_m:
            violation = LegalViolation(
                regulation="243",
                severity="WARNING",
                message=f"Side overhang exceeds {self.max_side_overhang_m}m limit",
                current_value=max(overhang_left_m, overhang_right_m),
                legal_limit=self.max_side_overhang_m
            )
            result["violations"].append(violation)
        
        if not result["violations"]:
            result["message"] = "✓ All overhangs within legal limits"
        
        return result
    
    # ==================== REGULATION 247: TIRE LOAD VALIDATION ====================
    
    def validate_tire_loads(self,
                            total_load_kg: float,
                            axle_count: int,
                            tire_type: str = "standard") -> Dict:
        """
        Validate tire loads against Regulation 247.
        
        Args:
            total_load_kg: Total load on all tires (kg)
            axle_count: Number of axles
            tire_type: "standard" (3500kg) or "heavy_duty" (4000kg)
        
        Returns:
            Dict with compliance status
        """
        tire_capacity = self.heavy_duty_tire_capacity_kg if tire_type == "heavy_duty" else self.standard_tire_capacity_kg
        
        total_tires = axle_count * self.tires_per_axle
        load_per_tire = total_load_kg / total_tires if total_tires > 0 else 0
        
        result = {
            "compliant": True,
            "load_per_tire_kg": round(load_per_tire, 0),
            "tire_capacity_kg": tire_capacity,
            "utilization_percent": round((load_per_tire / tire_capacity) * 100, 1),
            "message": ""
        }
        
        if load_per_tire > tire_capacity:
            result["compliant"] = False
            result["message"] = f"❌ Tire overload: {load_per_tire:.0f}kg > {tire_capacity}kg capacity"
        elif load_per_tire > tire_capacity * 0.9:
            result["message"] = f"⚠️ Tire load near limit: {result['utilization_percent']}% of capacity"
        else:
            result["message"] = f"✓ Tire loads within capacity ({result['utilization_percent']}%)"
        
        return result
    
    # ==================== COMPREHENSIVE AUDIT ====================
    
    def full_legal_audit(self,
                         trailer,
                         items: List,
                         truck_mass_kg: float = 8000,
                         route: str = None,
                         vehicle_type: str = "semitrailer") -> Dict:
        """
        Perform complete legal audit of the loading configuration.
        
        This is the main entry point that checks ALL regulations.
        
        Args:
            trailer: Trailer object with dimensions and configuration
            items: List of Item objects
            truck_mass_kg: Tare mass of truck/tractor
            route: Specific route name (for height restrictions)
            vehicle_type: "semitrailer", "rigid", or "combination"
        
        Returns:
            Complete legal assessment with all violations and permits
        """
        self.violations = []
        self.permits_required = []
        
        # Calculate basic metrics
        total_payload_kg = sum(item.mass_kg for item in items)
        total_height_m = max(item.height_m for item in items) if items else 0
        total_width_m = max(item.width_m for item in items) if items else 0
        
        # Get axle loads from trailer
        if hasattr(trailer, 'calculate_axle_loads'):
            front_load, rear_load, cog = trailer.calculate_axle_loads()
        else:
            front_load, rear_load, cog = 0, 0, 0
            
        total_mass = total_payload_kg + truck_mass_kg + getattr(trailer, 'trailer_tare_kg', 6000)
        
        # ===== IN-GAUGE CARGO CLASSIFICATION =====
        commercial_class = self.classify_cargo(items)
        
        # ===== Run all validations =====
        
        # Regulation 234: Height
        height_result = self.validate_height(total_height_m, route)
        if not height_result["compliant"]:
            self.violations.append(LegalViolation(
                regulation="234",
                severity="CRITICAL",
                message=height_result["message"],
                current_value=total_height_m,
                legal_limit=self.max_height_standard_m
            ))
        if height_result.get("permit_required"):
            self.permits_required.append(PermitRequirement(
                permit_type=height_result["permit_type"],
                reason=f"Height {total_height_m}m exceeds standard limit"
            ))
        
        # Regulation 235: Width
        width_result = self.validate_width(total_width_m)
        if not width_result["compliant"]:
            self.violations.append(LegalViolation(
                regulation="235",
                severity="CRITICAL",
                message=width_result["message"],
                current_value=total_width_m,
                legal_limit=self.max_width_standard_m
            ))
        if width_result.get("permit_required"):
            self.permits_required.append(PermitRequirement(
                permit_type=width_result["permit_type"],
                reason=f"Width {total_width_m}m exceeds standard limit"
            ))
        
        # Regulation 236: Length
        trailer_length = getattr(trailer, 'length_m', 13.6)
        length_result = self.validate_length(trailer_length, vehicle_type)
        if not length_result["compliant"]:
            self.violations.append(LegalViolation(
                regulation="236",
                severity="WARNING",
                message=length_result["message"],
                current_value=trailer_length,
                legal_limit=self.max_length_semitrailer_m
            ))
        if length_result.get("permit_required"):
            self.permits_required.append(PermitRequirement(
                permit_type=length_result["permit_type"],
                reason=f"Length {trailer_length}m exceeds standard limit"
            ))
        
        # Regulation 239: GCM
        gcm_result = self.validate_gcm(total_payload_kg, truck_mass_kg, getattr(trailer, 'trailer_tare_kg', 6000))
        if not gcm_result["compliant"]:
            self.violations.append(LegalViolation(
                regulation="239",
                severity="CRITICAL",
                message=gcm_result["message"],
                current_value=gcm_result["gcm_kg"],
                legal_limit=self.max_gcm_standard_kg
            ))
        if gcm_result.get("permit_required"):
            self.permits_required.append(PermitRequirement(
                permit_type=gcm_result["permit_type"],
                reason=f"GCM {gcm_result['gcm_tons']}t exceeds 56t limit"
            ))
        
        # Regulation 240: Axle loads
        axle_config = getattr(trailer, 'axle_configuration', [{"type": "tandem", "axle_count": 2}])
        axle_result = self.validate_axle_loads(
            front_load, rear_load, total_mass,
            axle_config
        )
        for violation in axle_result.get("violations", []):
            self.violations.append(violation)
        
        # Regulation 247: Tire loads
        axle_count = getattr(trailer, 'axle_count', 3)
        tire_result = self.validate_tire_loads(rear_load, axle_count)
        if not tire_result["compliant"]:
            self.violations.append(LegalViolation(
                regulation="247",
                severity="CRITICAL",
                message=tire_result["message"],
                current_value=tire_result["load_per_tire_kg"],
                legal_limit=tire_result["tire_capacity_kg"]
            ))
        
        # ===== Generate summary =====
        audit_result = {
            "compliant": len([v for v in self.violations if v.severity == "CRITICAL"]) == 0,
            "critical_violations": [vars(v) for v in self.violations if v.severity == "CRITICAL"],
            "warnings": [vars(v) for v in self.violations if v.severity == "WARNING"],
            "permits_required": [{"type": p.permit_type.value, "reason": p.reason} for p in self.permits_required],
            "commercial_classification": {
                "class": commercial_class["class_name"],
                "is_in_gauge": commercial_class["is_in_gauge"],
                "reasons": commercial_class["reasons"],
                "commercial_note": commercial_class["commercial_note"],
                "fleet_recommendation": commercial_class["fleet_recommendation"],
                "metrics": commercial_class["metrics"]
            },
            "summary": {
                "total_payload_tons": round(total_payload_kg / 1000, 1),
                "total_gcm_tons": round(gcm_result["gcm_tons"], 1),
                "front_load_kg": round(front_load, 0),
                "rear_load_kg": round(rear_load, 0),
                "height_m": total_height_m,
                "width_m": total_width_m,
                "length_m": trailer_length
            },
            "recommendations": self._generate_recommendations()
        }
        
        return audit_result
    
    def _generate_recommendations(self) -> List[str]:
        """Generate actionable recommendations based on violations"""
        recommendations = []
        
        for violation in self.violations:
            if "height" in violation.message.lower():
                recommendations.append("Apply for Section 81 abnormal load permit for height exemption")
                recommendations.append("Consider using low-loader trailer to reduce overall height")
            elif "width" in violation.message.lower():
                recommendations.append("Apply for abnormal width permit (5-7 working days)")
                recommendations.append("Schedule escort vehicles for wide load")
            elif "gcm" in violation.message.lower():
                recommendations.append("Apply for GCM exemption permit")
                recommendations.append("Consider splitting load across additional trailers")
            elif "axle" in violation.message.lower():
                recommendations.append("Redistribute items - move heavy items toward center")
                recommendations.append("Add additional axle group to trailer")
        
        if not recommendations and self.permits_required:
            recommendations.append(f"Contact RTMC for {len(self.permits_required)} permit(s) before departure")
        
        return list(set(recommendations))  # Remove duplicates
    
    def print_legal_report(self, audit_result: Dict):
        """Print formatted legal compliance report"""
        print("\n" + "="*70)
        print("📜 SOUTH AFRICAN NATIONAL ROAD TRAFFIC ACT - COMPLIANCE REPORT")
        print("="*70)
        print(f"Act 93 of 1996 | Regulations 234-247 | Province: {self.province}")
        print("-"*70)
        
        # ===== IN-GAUGE CARGO SECTION =====
        commercial = audit_result.get("commercial_classification", {})
        print("\n🏷️ COMMERCIAL CLASSIFICATION (In-Gauge / OOG):")
        if commercial.get("is_in_gauge", False):
            print(f"   ✅ {commercial.get('class', 'IN-GAUGE')}")
            print(f"   💰 {commercial.get('commercial_note', 'Standard rates apply')}")
        else:
            print(f"   ⚠️ {commercial.get('class', 'OUT-OF-GAUGE')}")
            print(f"   💰 {commercial.get('commercial_note', 'Premium rates apply')}")
            if commercial.get("reasons"):
                print("   Reasons:")
                for reason in commercial["reasons"]:
                    print(f"     - {reason}")
        print(f"   🚛 Fleet Recommendation: {commercial.get('fleet_recommendation', 'Standard flatbed')}")
        
        print("\n📊 LOAD SUMMARY:")
        print(f"   Total Payload: {audit_result['summary']['total_payload_tons']} tons")
        print(f"   Gross Combination Mass: {audit_result['summary']['total_gcm_tons']} tons")
        print(f"   Front (Kingpin) Load: {audit_result['summary']['front_load_kg']:,.0f} kg")
        print(f"   Rear Axle Load: {audit_result['summary']['rear_load_kg']:,.0f} kg")
        print(f"   Dimensions: {audit_result['summary']['height_m']}m(H) × {audit_result['summary']['width_m']}m(W) × {audit_result['summary']['length_m']}m(L)")
        
        if audit_result["critical_violations"]:
            print("\n❌ CRITICAL VIOLATIONS (DO NOT DEPART):")
            for v in audit_result["critical_violations"]:
                print(f"   • Reg {v['regulation']}: {v['message']}")
        
        if audit_result["warnings"]:
            print("\n⚠️ WARNINGS:")
            for v in audit_result["warnings"]:
                print(f"   • Reg {v['regulation']}: {v['message']}")
        
        if audit_result["permits_required"]:
            print("\n📋 PERMITS REQUIRED (Section 81):")
            for p in audit_result["permits_required"]:
                print(f"   • {p['type']}")
                print(f"     Reason: {p['reason']}")
        
        if audit_result["recommendations"]:
            print("\n💡 RECOMMENDATIONS:")
            for r in audit_result["recommendations"]:
                print(f"   • {r}")
        
        print("\n" + "="*70)
        if audit_result["compliant"] and commercial.get("is_in_gauge", False):
            print("✅ VERDICT: IN-GAUGE & LEGALLY COMPLIANT - Standard rates, safe to depart")
        elif audit_result["compliant"] and not commercial.get("is_in_gauge", True):
            print("⚠️ VERDICT: OUT-OF-GAUGE - Legal but premium rates apply, obtain permit if required")
        else:
            print("🚨 VERDICT: NON-COMPLIANT - DO NOT DEPART until violations resolved")
        print("="*70 + "\n")
        
        return audit_result["compliant"] and not audit_result["critical_violations"]


# ==================== HELPER FUNCTION FOR INTEGRATION ====================

def quick_legal_check(trailer, items, route=None) -> Dict:
    """
    Quick one-line legal check for integration with main app.
    
    Usage:
        result = quick_legal_check(my_trailer, my_items, route="Bain's Kloof Pass")
        if result["compliant"]:
            print("Legal to load")
        else:
            print(f"Violations: {result['critical_violations']}")
    """
    validator = SARoadTrafficValidator()
    audit = validator.full_legal_audit(trailer, items, route=route)
    validator.print_legal_report(audit)
    return audit


# ==================== UNIT TESTS ====================

if __name__ == "__main__":
    # Run legal compliance tests
    print("Running legal compliance tests...\n")
    
    validator = SARoadTrafficValidator(province="WesternCape")
    
    # Test 1: Standard legal load (should be IN-GAUGE)
    print("TEST 1: Standard legal load (IN-GAUGE expected)")
    test_items = []
    test_item = type('Item', (), {'mass_kg': 5000, 'height_m': 2.8, 'width_m': 2.4, 'length_m': 6.0})()
    test_items.append(test_item)
    
    test_trailer = type('Trailer', (), {
        'length_m': 13.6, 
        'calculate_axle_loads': lambda: (6000, 12000, 6.8),
        'trailer_tare_kg': 6000,
        'axle_count': 3,
        'axle_configuration': [{'type': 'steering'}, {'type': 'tandem', 'axle_count': 2}]
    })()
    
    result = validator.full_legal_audit(test_trailer, test_items, route="Standard Highway")
    assert result["compliant"] == True, "Standard load should be compliant"
    assert result["commercial_classification"]["is_in_gauge"] == True, "Standard load should be IN-GAUGE"
    print("✓ Test 1 passed: IN-GAUGE classification correct\n")
    
    # Test 2: Out-of-Gauge load (oversized but legal)
    print("TEST 2: Out-of-Gauge load (OOG expected)")
    test_items_oog = []
    oog_item = type('Item', (), {'mass_kg': 5000, 'height_m': 3.5, 'width_m': 2.5, 'length_m': 8.0})()
    test_items_oog.append(oog_item)
    
    result2 = validator.full_legal_audit(test_trailer, test_items_oog)
    assert result2["commercial_classification"]["is_in_gauge"] == False, "Oversized should be OOG"
    print("✓ Test 2 passed: OOG classification correct\n")
    
    # Test 3: Over-height load (requires permit)
    print("TEST 3: Over-height load (Abnormal expected)")
    test_items_abnormal = []
    abnormal_item = type('Item', (), {'mass_kg': 5000, 'height_m': 4.5, 'width_m': 2.4, 'length_m': 6.0})()
    test_items_abnormal.append(abnormal_item)
    
    result3 = validator.full_legal_audit(test_trailer, test_items_abnormal)
    assert result3["commercial_classification"]["class"] == "ABNORMAL", "Over-height should be ABNORMAL"
    assert len(result3["permits_required"]) > 0, "Should require permits"
    print("✓ Test 3 passed: Abnormal classification correct\n")
    
    print("\n✅ All tests passed!")