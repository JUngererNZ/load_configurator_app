"""Export functions for manifests and loading sequences"""

import pandas as pd
from typing import List
from datetime import datetime


def export_manifest(trailers: List, items_by_trailer: List[List], 
                    validator_results: List[Dict] = None,
                    filename: str = "LOADING_MANIFEST"):
    """
    Export complete loading manifest to Excel and CSV.
    
    Args:
        trailers: List of Trailer objects
        items_by_trailer: List of lists, each containing items for corresponding trailer
        validator_results: Optional list of legal audit results per trailer
        filename: Base filename for export
    
    Returns:
        Tuple of (excel_filename, csv_filename, df_sequence)
    """
    
    all_rows = []
    loading_sequence = []
    sequence_step = 1
    
    for trailer_idx, (trailer, items) in enumerate(zip(trailers, items_by_trailer)):
        if hasattr(trailer, 'calculate_axle_loads'):
            front, rear, cog = trailer.calculate_axle_loads()
        else:
            front, rear, cog = 0, 0, 0
            
        if hasattr(trailer, 'is_safe'):
            is_safe, violations = trailer.is_safe()
        else:
            is_safe = True
            violations = []
        
        # Get In-Gauge classification if available
        ingauge_status = "UNKNOWN"
        ingauge_reason = ""
        commercial_note = ""
        if validator_results and trailer_idx < len(validator_results):
            commercial = validator_results[trailer_idx].get("commercial_classification", {})
            ingauge_status = "IN-GAUGE" if commercial.get("is_in_gauge") else "OUT-OF-GAUGE"
            ingauge_reason = "; ".join(commercial.get("reasons", []))
            commercial_note = commercial.get("commercial_note", "")
        
        for item in items:
            row = {
                "Trailer": trailer.name if hasattr(trailer, 'name') else f"Trailer_{trailer_idx+1}",
                "Trailer_Type": getattr(trailer, 'type_name', 'Standard Flatbed'),
                "Loading_Step": sequence_step,
                "Consignment": item.consignment,
                "Mass_kg": item.mass_kg,
                "Mass_t": round(item.mass_kg / 1000, 2),
                "Length_m": item.length_m,
                "Width_m": item.width_m,
                "Height_m": item.height_m,
                "X_Position_m": round(item.x_pos, 2),
                "Y_Position_m": round(item.y_pos, 2),
                "Rotated_90deg": getattr(item, 'rotated', False),
                "Front_Axle_Load_kg": round(front, 0),
                "Rear_Axle_Load_kg": round(rear, 0),
                "Safety_Status": "PASS" if is_safe else "FAIL",
                "Violations": "; ".join(violations) if violations else "None",
                # NEW: In-Gauge Cargo Classification
                "Cargo_Classification": ingauge_status,
                "OOG_Reasons": ingauge_reason,
                "Commercial_Note": commercial_note
            }
            all_rows.append(row)
            
            # Build loading sequence
            loading_sequence.append({
                "Step": sequence_step,
                "Action": f"Load {item.consignment}",
                "Trailer": trailer.name if hasattr(trailer, 'name') else f"Trailer_{trailer_idx+1}",
                "Position": f"X={item.x_pos:.1f}m, Y={item.y_pos:.1f}m",
                "Mass": f"{item.mass_kg/1000:.1f}t",
                "Cargo_Class": ingauge_status
            })
            sequence_step += 1
    
    df_manifest = pd.DataFrame(all_rows)
    df_sequence = pd.DataFrame(loading_sequence)
    
    # Create Excel file with multiple sheets
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    excel_filename = f"{filename}_{timestamp}.xlsx"
    
    with pd.ExcelWriter(excel_filename, engine='openpyxl') as writer:
        df_manifest.to_excel(writer, sheet_name='Full Manifest', index=False)
        df_sequence.to_excel(writer, sheet_name='Loading Sequence', index=False)
        
        # Summary sheet with In-Gauge totals
        summary_data = []
        for trailer_idx, (trailer, items) in enumerate(zip(trailers, items_by_trailer)):
            if hasattr(trailer, 'calculate_axle_loads'):
                front, rear, cog = trailer.calculate_axle_loads()
            else:
                front, rear, cog = 0, 0, 0
                
            ingauge_count = 0
            oog_count = 0
            if validator_results and trailer_idx < len(validator_results):
                commercial = validator_results[trailer_idx].get("commercial_classification", {})
                if commercial.get("is_in_gauge"):
                    ingauge_count = len(items)
                else:
                    oog_count = len(items)
            
            summary_data.append({
                "Trailer": trailer.name if hasattr(trailer, 'name') else f"Trailer_{trailer_idx+1}",
                "Type": getattr(trailer, 'type_name', 'Standard Flatbed'),
                "Items": len(items),
                "In-Gauge_Items": ingauge_count,
                "OOG_Items": oog_count,
                "Total_Mass_t": round(sum(i.mass_kg for i in items)/1000, 1),
                "Front_Load_t": round(front/1000, 1),
                "Rear_Load_t": round(rear/1000, 1),
                "Legal": "✅" if is_safe else "❌"
            })
        df_summary = pd.DataFrame(summary_data)
        df_summary.to_excel(writer, sheet_name='Summary', index=False)
    
    # Also save CSV version
    csv_filename = f"{filename}_{timestamp}.csv"
    df_manifest.to_csv(csv_filename, index=False)
    
    print(f"✅ Exported: {excel_filename}")
    print(f"✅ Exported: {csv_filename}")
    
    return excel_filename, csv_filename, df_sequence


def print_loading_instructions(df_sequence):
    """Generate printable loading instructions with In-Gauge notes"""
    instructions = []
    instructions.append("\n" + "="*60)
    instructions.append("🚛 LOADING INSTRUCTIONS - FOLLOW SEQUENCE EXACTLY 🚛")
    instructions.append("="*60)
    
    current_trailer = None
    for _, row in df_sequence.iterrows():
        if row['Trailer'] != current_trailer:
            current_trailer = row['Trailer']
            instructions.append(f"\n📦 TRAILER: {current_trailer}")
            instructions.append("-" * 40)
        
        cargo_marker = "📦" if row['Cargo_Class'] == "IN-GAUGE" else "⚠️"
        instructions.append(f"Step {row['Step']:2d}: {cargo_marker} {row['Action']:<20} → Position: {row['Position']:<15} → {row['Mass']}")
    
    instructions.append("\n" + "="*60)
    instructions.append("⚠️  IMPORTANT SAFETY NOTES ⚠️")
    instructions.append("1. Ensure 20cm gap between all units for lashing")
    instructions.append("2. Verify axle loads before departure")
    instructions.append("3. All loads must comply with Regulation 240 of Act 93/1996")
    instructions.append("\n🏷️ CARGO CLASSIFICATION LEGEND:")
    instructions.append("   📦 = IN-GAUGE - Standard rates apply")
    instructions.append("   ⚠️ = OUT-OF-GAUGE (OOG) - Premium rates, may require permits")
    instructions.append("="*60)
    
    return "\n".join(instructions)