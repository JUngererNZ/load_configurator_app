"""Export functions for manifests and loading sequences"""

import pandas as pd
from typing import List
from datetime import datetime

def export_manifest(trailers: List, filename: str = "LOADING_MANIFEST"):
    """Export complete loading manifest to Excel and CSV"""
    
    all_rows = []
    loading_sequence = []
    sequence_step = 1
    
    for trailer in trailers:
        front, rear, cog = trailer.calculate_axle_loads()
        is_safe, violations = trailer.is_safe()
        
        for item in trailer.items:
            row = {
                "Trailer": trailer.name,
                "Trailer_Type": trailer.type_name,
                "Loading_Step": sequence_step,
                "Consignment": item.consignment,
                "Mass_kg": item.mass_kg,
                "Mass_t": round(item.mass_kg / 1000, 2),
                "Length_m": item.length_m,
                "Width_m": item.width_m,
                "Height_m": item.height_m,
                "X_Position_m": round(item.x_pos, 2),
                "Y_Position_m": round(item.y_pos, 2),
                "Rotated_90deg": item.rotated,
                "Front_Axle_Load_kg": round(front, 0),
                "Rear_Axle_Load_kg": round(rear, 0),
                "Safety_Status": "PASS" if is_safe else "FAIL",
                "Violations": "; ".join(violations) if violations else "None"
            }
            all_rows.append(row)
            
            # Build loading sequence
            loading_sequence.append({
                "Step": sequence_step,
                "Action": f"Load {item.consignment}",
                "Trailer": trailer.name,
                "Position": f"X={item.x_pos:.1f}m, Y={item.y_pos:.1f}m",
                "Mass": f"{item.mass_kg/1000:.1f}t"
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
        
        # Summary sheet
        summary_data = []
        for trailer in trailers:
            front, rear, cog = trailer.calculate_axle_loads()
            is_safe, _ = trailer.is_safe()
            summary_data.append({
                "Trailer": trailer.name,
                "Type": trailer.type_name,
                "Items": len(trailer.items),
                "Total_Mass_t": round(trailer.total_mass_kg/1000, 1),
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
    """Generate printable loading instructions"""
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
        
        instructions.append(f"Step {row['Step']:2d}: {row['Action']:<20} → Position: {row['Position']:<15} → {row['Mass']}")
    
    instructions.append("\n" + "="*60)
    instructions.append("⚠️  IMPORTANT SAFETY NOTES ⚠️")
    instructions.append("1. Ensure 20cm gap between all units for lashing")
    instructions.append("2. Verify axle loads before departure")
    instructions.append("3. All loads must comply with Regulation 240 of Act 93/1996")
    instructions.append("="*60)
    
    return "\n".join(instructions)