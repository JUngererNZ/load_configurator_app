"""
MASTER LOAD CONFIGURATOR - One-Click Solution
Complete pipeline: Load Data → Optimize → Validate → Visualize → Export

Usage: python master_configurator.py
"""

import pandas as pd
import os
import sys
from datetime import datetime
from pathlib import Path

# Import all modules
from optimizer_engine import Item, Trailer, AutoOptimizer
from rules_validator import SARoadTrafficValidator, quick_legal_check
from visualizer_2d import create_top_down_view, create_side_view, generate_all_views
from exporter import export_manifest, print_loading_instructions
from trailer_library import SuperlinkTrailer, TRAILER_TYPES


def find_input_file():
    """Automatically find the consignment file in current directory"""
    current_dir = Path.cwd()
    
    # Look for common file patterns
    patterns = [
        "*GENSETS*.xlsx",
        "*GENSETS*.csv",
        "*consignment*.xlsx",
        "*consignment*.csv",
        "*load*.xlsx",
        "*load*.csv",
        "sample_data.xlsx",
        "sample_data.csv",
        "*.xlsx",
        "*.csv"
    ]
    
    for pattern in patterns:
        files = list(current_dir.glob(pattern))
        if files:
            # Return the first match (most recent if multiple)
            return max(files, key=lambda f: f.stat().st_mtime)
    
    return None


def load_items_from_file(filepath):
    """Load items from Excel/CSV with flexible column mapping"""
    print(f"\n📂 Loading file: {filepath}")
    
    try:
        # Determine file type and load
        if filepath.suffix.lower() in ['.xlsx', '.xls']:
            df = pd.read_excel(filepath)
        else:
            df = pd.read_csv(filepath)
        
        print(f"   Found columns: {list(df.columns)}")
        
        # Try to find the data row if there are header rows
        # Look for the first row with numeric values in expected columns
        data_start_row = 0
        for idx, row in df.iterrows():
            row_str = str(row.values)
            if any(x in row_str.upper() for x in ['LENGTH', 'WIDTH', 'HEIGHT', 'MASS', 'KG', 'MM']):
                # This might be a header row
                continue
            # Check if this row has numeric values that look like dimensions
            numeric_count = 0
            for val in row.values:
                try:
                    fval = float(val)
                    if 0.1 < fval < 100:  # Reasonable dimension range
                        numeric_count += 1
                except (ValueError, TypeError):
                    pass
            if numeric_count >= 3:  # At least 3 numeric values (L, W, H or similar)
                data_start_row = idx
                break
        
        if data_start_row > 0:
            print(f"   Auto-detected data starting at row {data_start_row + 1}")
            df = df.iloc[data_start_row:].reset_index(drop=True)
        
        # Find columns (case-insensitive)
        col_map = {}
        for col in df.columns:
            col_upper = str(col).upper()
            if 'CONSIGNMENT' in col_upper or 'ORDER' in col_upper or 'ITEM' in col_upper or 'NAME' in col_upper:
                col_map['consignment'] = col
            elif 'LENGTH' in col_upper or 'LEN' in col_upper:
                col_map['length'] = col
            elif 'WIDTH' in col_upper or 'WID' in col_upper:
                col_map['width'] = col
            elif 'HEIGHT' in col_upper or 'HEI' in col_upper:
                col_map['height'] = col
            elif 'MASS' in col_upper or 'WEIGHT' in col_upper or 'MASS_KG' in col_upper or 'KG' in col_upper:
                col_map['mass'] = col
        
        # If consignment not found, use index as name
        if 'consignment' not in col_map:
            col_map['consignment'] = df.columns[0]
            print(f"   Using '{col_map['consignment']}' as consignment identifier")
        
        # Validate required columns
        required = ['length', 'width', 'height', 'mass']
        missing = [r for r in required if r not in col_map]
        if missing:
            print(f"❌ Missing columns: {missing}")
            print(f"   Available columns: {list(df.columns)}")
            print("\n   Please ensure your file has columns named:")
            print("   - LENGTH or LEN (in meters)")
            print("   - WIDTH or WID (in meters)")
            print("   - HEIGHT or HEI (in meters)")
            print("   - MASS or WEIGHT (in tonnes or kg)")
            return None
        
        # Create Item objects
        items = []
        skipped = 0
        
        for idx, row in df.iterrows():
            try:
                # Get consignment name
                consignment = str(row[col_map['consignment']])
                if pd.isna(consignment) or consignment == 'nan':
                    consignment = f"ITEM_{idx+1}"
                
                # Get dimensions
                length_m = float(row[col_map['length']])
                width_m = float(row[col_map['width']])
                height_m = float(row[col_map['height']])
                
                # Get mass - handle various units
                mass_val = float(row[col_map['mass']])
                
                # Check if mass is in kg or tonnes
                # Typical genset masses: small genset ~500kg, large ~5000kg
                # If mass is < 100 and > 0, likely in tonnes
                if 0 < mass_val < 100:
                    mass_kg = mass_val * 1000  # Convert tonnes to kg
                else:
                    mass_kg = mass_val  # Already in kg
                
                # Skip invalid rows
                if length_m <= 0 or width_m <= 0 or height_m <= 0 or mass_kg <= 0:
                    skipped += 1
                    continue
                
                item = Item(
                    consignment=consignment,
                    length_m=length_m,
                    width_m=width_m,
                    height_m=height_m,
                    mass_kg=mass_kg,
                    rotated=False
                )
                items.append(item)
                
            except Exception as e:
                skipped += 1
                print(f"   Warning: Skipping row {idx}: {e}")
                continue
        
        print(f"✅ Loaded {len(items)} items (skipped {skipped} invalid rows)")
        
        if len(items) == 0:
            print("❌ No valid items found in file!")
            return None
            
        return items
    
    except Exception as e:
        print(f"❌ Error loading file: {e}")
        import traceback
        traceback.print_exc()
        return None


def create_standard_trailers(trailer_type, num_trailers):
    """Create standard single trailer objects"""
    from optimizer_engine import Trailer
    
    specs = {
        "Flatbed Standard": {
            "name": "Flatbed",
            "length_m": 13.6,
            "width_m": 2.4,
            "deck_height_m": 1.2,
            "max_payload_kg": 28000,
            "max_rear_axle_kg": 18000,
            "max_kingpin_kg": 12000,
            "wheelbase_m": 10.5,
            "tare_kg": 6000,
            "axle_config": [{"type": "steering"}, {"type": "tandem", "axle_count": 2}]
        },
        "Low-Loader": {
            "name": "LowLoader",
            "length_m": 13.6,
            "width_m": 2.8,
            "deck_height_m": 0.8,
            "max_payload_kg": 35000,
            "max_rear_axle_kg": 22000,
            "max_kingpin_kg": 15000,
            "wheelbase_m": 9.5,
            "tare_kg": 8000,
            "axle_config": [{"type": "steering"}, {"type": "tandem", "axle_count": 2}, {"type": "single"}]
        },
        "Abnormal": {
            "name": "Abnormal",
            "length_m": 18.0,
            "width_m": 3.0,
            "deck_height_m": 1.0,
            "max_payload_kg": 50000,
            "max_rear_axle_kg": 30000,
            "max_kingpin_kg": 18000,
            "wheelbase_m": 14.0,
            "tare_kg": 10000,
            "axle_config": [{"type": "steering"}, {"type": "triaxle", "axle_count": 3}, {"type": "tandem", "axle_count": 2}]
        }
    }
    
    spec = specs.get(trailer_type, specs["Flatbed Standard"])
    trailers = []
    
    for i in range(num_trailers):
        # Create a simple trailer object with required attributes
        trailer = Trailer(
            name=f"{spec['name']}_{i+1}",
            type_name=trailer_type,
            length_m=spec["length_m"],
            width_m=spec["width_m"],
            deck_height_m=spec["deck_height_m"],
            max_payload_kg=spec["max_payload_kg"],
            max_rear_axle_kg=spec["max_rear_axle_kg"],
            max_kingpin_kg=spec["max_kingpin_kg"],
            wheelbase_m=spec["wheelbase_m"],
            trailer_tare_kg=spec["tare_kg"]
        )
        # Add axle configuration
        trailer.axle_configuration = spec["axle_config"]
        trailers.append(trailer)
    
    return trailers


def distribute_items_to_trailers(items, trailers, gap_m=0.2):
    """Distribute items across multiple trailers using heuristic"""
    # Sort items by mass (heaviest first) for better weight distribution
    items_sorted = sorted(items, key=lambda x: x.mass_kg, reverse=True)
    
    # Reset trailers
    for trailer in trailers:
        trailer.items = []
        trailer.total_mass_kg = 0
    
    unplaced_items = []
    
    for item in items_sorted:
        placed = False
        
        # Try each trailer
        for trailer in trailers:
            # Calculate current X position (end of last item + gap)
            if trailer.items:
                last_item = trailer.items[-1]
                current_x = last_item.x_pos + last_item.length_m + gap_m
            else:
                current_x = 0.2  # Start 20cm from front
            
            # Check if item fits
            if hasattr(trailer, 'can_add_item'):
                can_fit, reason = trailer.can_add_item(item, current_x, gap_m)
            else:
                # For standard Trailer class
                can_fit = (current_x + item.length_m <= trailer.length_m and
                          trailer.total_mass_kg + item.mass_kg <= trailer.max_payload_kg)
                reason = ""
            
            if can_fit:
                item.x_pos = current_x
                item.y_pos = 0.15
                trailer.add_item(item, current_x, 0.15)
                placed = True
                break
        
        if not placed:
            unplaced_items.append(item)
    
    if unplaced_items:
        print(f"\n⚠️ Could not place {len(unplaced_items)} items - need more trailers")
        for item in unplaced_items[:5]:
            print(f"   - {item.consignment} ({item.mass_kg/1000:.1f}t, {item.length_m}m)")
    
    return len(unplaced_items) == 0


def run_master_configurator(input_file=None):
    """
    Main function - runs complete pipeline
    """
    print("\n" + "="*70)
    print("🚛 FML LOAD CONFIGURATOR - MASTER PIPELINE")
    print("="*70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # ===== STEP 1: Find and Load Input File =====
    print("\n" + "-"*50)
    print("STEP 1: Loading Consignment Data")
    print("-"*50)
    
    if input_file is None:
        input_file = find_input_file()
    
    if input_file is None:
        print("\n❌ No input file found!")
        print("   Please place your consignment file (.xlsx or .csv) in this folder")
        print("   Required columns: CONSIGNMENT, LENGTH, WIDTH, HEIGHT, MASS")
        return False
    
    items = load_items_from_file(Path(input_file))
    if not items:
        return False
    
    # Calculate total mass safely
    total_mass_kg = sum(item.mass_kg for item in items if hasattr(item, 'mass_kg'))
    total_mass_tons = total_mass_kg / 1000
    
    print(f"\n   Total items: {len(items)}")
    print(f"   Total mass: {total_mass_tons:.1f} tonnes")
    
    # Display first few items
    print("\n   Loaded items:")
    for i, item in enumerate(items[:8]):
        print(f"   {i+1}. {item.consignment}: {item.length_m}m x {item.width_m}m x {item.height_m}m, {item.mass_kg/1000:.1f}t")
    if len(items) > 8:
        print(f"   ... and {len(items)-8} more")
    
    # ===== STEP 2: Create Trailers =====
    print("\n" + "-"*50)
    print("STEP 2: Configuring Trailers")
    print("-"*50)
    
    # Display available trailer types
    print("\n   Available trailer types:")
    print("   1. Flatbed Standard (13.6m, 28t payload)")
    print("   2. Low-Loader (13.6m, 35t payload, lower deck)")
    print("   3. Abnormal (18.0m, 50t payload, requires permit)")
    print("   4. SUPERLINK (6m + 12m, 34t payload, 3 x 20ft or 1 x 20ft + 1 x 40ft)")
    print("   5. INTERLINK (6m + 6m, 34t payload, high-density)")
    
    trailer_choice = input("\n   Select trailer type (1-5) [default: 1]: ").strip()
    
    if trailer_choice == "2":
        trailer_type = "Low-Loader"
        is_superlink = False
    elif trailer_choice == "3":
        trailer_type = "Abnormal"
        is_superlink = False
    elif trailer_choice == "4":
        trailer_type = "Superlink (6m + 12m)"
        is_superlink = True
    elif trailer_choice == "5":
        trailer_type = "Interlink (6m + 6m)"
        is_superlink = True
    else:
        trailer_type = "Flatbed Standard"
        is_superlink = False
    
    # Handle Superlink specially
    if is_superlink:
        print(f"\n   Using SUPERLINK configuration: {trailer_type}")
        print(f"   - Front trailer: 6m (max 14t)")
        print(f"   - Rear trailer: 12m (max 20t)")
        print(f"   - Total payload: 34t")
        
        # Create a single Superlink
        superlink = SuperlinkTrailer(name="Superlink_1", config_type=trailer_type)
        
        # Distribute items to Superlink
        print("\n   Distributing items to Superlink...")
        
        # Sort items by mass (heaviest first)
        items_sorted = sorted(items, key=lambda x: x.mass_kg, reverse=True)
        
        # Track placement
        front_x = 0.2
        rear_x = 0.2
        
        for item in items_sorted:
            # Try front trailer first (better weight distribution)
            can_fit_front, _ = superlink.can_add_item_to_front(item, front_x)
            can_fit_rear, _ = superlink.can_add_item_to_rear(item, rear_x)
            
            if can_fit_front and superlink.front["total_mass_kg"] + item.mass_kg <= superlink.front["max_payload_kg"]:
                superlink.add_item_to_front(item, front_x)
                front_x += item.length_m + 0.2
            elif can_fit_rear and superlink.rear["total_mass_kg"] + item.mass_kg <= superlink.rear["max_payload_kg"]:
                superlink.add_item_to_rear(item, rear_x)
                rear_x += item.length_m + 0.2
            else:
                print(f"   ⚠️ Could not place {item.consignment} - payload exceeded")
        
        trailers = [superlink]
        items_by_trailer = [superlink.get_all_items()]
        
        # Display distribution
        print(f"\n   Superlink loading complete:")
        print(f"   Front trailer (6m): {len(superlink.front['items'])} items, {superlink.front['total_mass_kg']/1000:.1f}t / {superlink.front['max_payload_kg']/1000:.0f}t")
        print(f"   Rear trailer (12m): {len(superlink.rear['items'])} items, {superlink.rear['total_mass_kg']/1000:.1f}t / {superlink.rear['max_payload_kg']/1000:.0f}t")
        print(f"   Total: {len(superlink.get_all_items())} items, {superlink.total_mass_kg/1000:.1f}t / {superlink.max_payload_kg/1000:.0f}t")
        
    else:
        # Standard trailer logic
        # Calculate required number of trailers
        specs = {"Flatbed Standard": 28, "Low-Loader": 35, "Abnormal": 50}
        payload_per_trailer = specs.get(trailer_type, 28)
        
        # Ensure total_mass_tons is valid
        if pd.isna(total_mass_tons) or total_mass_tons <= 0:
            print(f"❌ Invalid total mass: {total_mass_tons}")
            return False
        
        num_trailers = max(1, int(total_mass_tons / payload_per_trailer) + 1)
        num_trailers = min(num_trailers, 5)  # Cap at 5 trailers
        
        print(f"\n   Total mass: {total_mass_tons:.1f}t")
        print(f"   Using {num_trailers} x {trailer_type} trailer(s)")
        
        trailers = create_standard_trailers(trailer_type, num_trailers)
        
        # ===== STEP 3: Distribute Items =====
        print("\n" + "-"*50)
        print("STEP 3: Optimizing Load Distribution")
        print("-"*50)
        
        success = distribute_items_to_trailers(items, trailers, gap_m=0.2)
        if not success:
            print("\n⚠️ Need more trailers! Adding one more...")
            trailers.append(create_standard_trailers(trailer_type, 1)[0])
            distribute_items_to_trailers(items, trailers, gap_m=0.2)
        
        print(f"\n   Distribution complete:")
        for trailer in trailers:
            if trailer.items:
                print(f"   {trailer.name}: {len(trailer.items)} items, {trailer.total_mass_kg/1000:.1f}t")
        
        items_by_trailer = [trailer.items for trailer in trailers if trailer.items]
        trailers = [t for t in trailers if t.items]  # Remove empty trailers
    
    # ===== STEP 4: Legal Compliance & In-Gauge Classification =====
    print("\n" + "-"*50)
    print("STEP 4: Legal Compliance & Cargo Classification")
    print("-"*50)
    
    validator = SARoadTrafficValidator(province="WesternCape")
    audit_results = []
    
    for trailer in trailers:
        if hasattr(trailer, 'get_all_items'):
            trailer_items = trailer.get_all_items()
        else:
            trailer_items = trailer.items
        
        if trailer_items:
            audit = validator.full_legal_audit(trailer, trailer_items)
            audit_results.append(audit)
            validator.print_legal_report(audit)
    
    # ===== STEP 5: Generate Visualizations =====
    print("\n" + "-"*50)
    print("STEP 5: Generating 2D Visualizations")
    print("-"*50)
    
    for i, trailer in enumerate(trailers):
        if hasattr(trailer, 'get_all_items'):
            trailer_items = trailer.get_all_items()
            trailer_name = trailer.name
        else:
            trailer_items = trailer.items
            trailer_name = trailer.name if hasattr(trailer, 'name') else f"Trailer_{i+1}"
        
        if trailer_items:
            print(f"   Generating views for {trailer_name}...")
            try:
                # Create and save top-down view
                fig1 = create_top_down_view(trailer)
                fig1.savefig(f"loading_plan_{trailer_name}_topdown.png", dpi=150, bbox_inches='tight')
                print(f"   ✅ Saved: loading_plan_{trailer_name}_topdown.png")
                
                # Create and save side view
                fig2 = create_side_view(trailer)
                fig2.savefig(f"loading_plan_{trailer_name}_side.png", dpi=150, bbox_inches='tight')
                print(f"   ✅ Saved: loading_plan_{trailer_name}_side.png")
                
                # Close figures
                import matplotlib.pyplot as plt
                plt.close(fig1)
                plt.close(fig2)
            except Exception as e:
                print(f"   ⚠️ Could not generate visualization: {e}")
    
    # ===== STEP 6: Export Manifest =====
    print("\n" + "-"*50)
    print("STEP 6: Exporting Loading Manifest")
    print("-"*50)
    
    # Prepare non-empty trailers and their items
    non_empty_trailers = []
    final_items_by_trailer = []
    
    for trailer in trailers:
        if hasattr(trailer, 'get_all_items'):
            trailer_items = trailer.get_all_items()
        else:
            trailer_items = trailer.items
        
        if trailer_items:
            non_empty_trailers.append(trailer)
            final_items_by_trailer.append(trailer_items)
    
    if non_empty_trailers:
        excel_file, csv_file, df_sequence = export_manifest(
            trailers=non_empty_trailers,
            items_by_trailer=final_items_by_trailer,
            validator_results=audit_results,
            filename="LOADING_MANIFEST"
        )
        
        # Print loading instructions
        instructions = print_loading_instructions(df_sequence)
        print(instructions)
        
        # Save instructions to text file
        with open("LOADING_INSTRUCTIONS.txt", "w") as f:
            f.write(instructions)
        print("\n✅ Saved: LOADING_INSTRUCTIONS.txt")
    
    # ===== SUMMARY =====
    print("\n" + "="*70)
    print("✅ MASTER PIPELINE COMPLETE")
    print("="*70)
    print("\n📁 OUTPUT FILES GENERATED:")
    
    if non_empty_trailers:
        print(f"   📊 {excel_file}")
        print(f"   📄 {csv_file}")
        print(f"   📝 LOADING_INSTRUCTIONS.txt")
        for trailer in non_empty_trailers:
            trailer_display = trailer.name if hasattr(trailer, 'name') else str(trailer)
            print(f"   🖼️ loading_plan_{trailer_display}_topdown.png")
            print(f"   🖼️ loading_plan_{trailer_display}_side.png")
    
    # Determine overall status
    all_compliant = all(a.get("compliant", False) for a in audit_results) if audit_results else True
    all_ingauge = all(a.get("commercial_classification", {}).get("is_in_gauge", False) for a in audit_results) if audit_results else True
    
    print("\n" + "="*70)
    if all_compliant and all_ingauge:
        print("🚛 VERDICT: IN-GAUGE & LEGALLY COMPLIANT")
        print("   ✅ Safe to depart - Standard rates apply")
    elif all_compliant and not all_ingauge:
        print("⚠️ VERDICT: OUT-OF-GAUGE - Legally compliant but premium rates apply")
        print("   📋 Ensure permits are obtained before departure")
    else:
        print("🚨 VERDICT: NON-COMPLIANT - DO NOT DEPART")
        print("   🔧 Reconfigure load or add more trailers")
    print("="*70)
    
    return True


def main():
    """Entry point with command line argument support"""
    import argparse
    
    parser = argparse.ArgumentParser(description='FML Load Configurator - Master Pipeline')
    parser.add_argument('--file', '-f', type=str, help='Path to consignment file (Excel/CSV)')
    
    args = parser.parse_args()
    
    # Run the pipeline
    success = run_master_configurator(input_file=args.file)
    
    if not success:
        print("\n❌ Pipeline failed. Please check your input file and try again.")
        sys.exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    main()