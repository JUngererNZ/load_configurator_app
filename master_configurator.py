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
        if filepath.suffix.lower() in ['.xlsx', '.xls']:
            df = pd.read_excel(filepath)
        else:
            df = pd.read_csv(filepath)
        
        # Try to skip header rows if needed
        # Look for data in first few rows
        for skip in range(0, 6):
            test_df = pd.read_csv(filepath, skiprows=skip) if filepath.suffix.lower() != '.xlsx' else pd.read_excel(filepath, skiprows=skip)
            if 'LENGTH' in str(test_df.columns).upper() or 'MASS' in str(test_df.columns).upper():
                df = test_df
                if skip > 0:
                    print(f"   Auto-skipped {skip} header row(s)")
                break
        
        # Find columns (case-insensitive)
        col_map = {}
        for col in df.columns:
            col_upper = col.upper()
            if 'CONSIGNMENT' in col_upper or 'ORDER' in col_upper:
                col_map['consignment'] = col
            elif 'LENGTH' in col_upper or 'LEN' in col_upper:
                col_map['length'] = col
            elif 'WIDTH' in col_upper or 'WID' in col_upper:
                col_map['width'] = col
            elif 'HEIGHT' in col_upper or 'HEI' in col_upper:
                col_map['height'] = col
            elif 'MASS' in col_upper or 'WEIGHT' in col_upper or 'MASS_KG' in col_upper:
                col_map['mass'] = col
        
        # Validate required columns
        required = ['consignment', 'length', 'width', 'height', 'mass']
        missing = [r for r in required if r not in col_map]
        if missing:
            print(f"❌ Missing columns: {missing}")
            print(f"   Available columns: {list(df.columns)}")
            return None
        
        # Create Item objects
        from optimizer_engine import Item
        items = []
        for idx, row in df.iterrows():
            try:
                mass_kg = float(row[col_map['mass']])
                # If mass is in tonnes (e.g., 3.7), convert to kg
                if mass_kg < 100:  # Likely tonnes if under 100
                    mass_kg = mass_kg * 1000
                
                item = Item(
                    consignment=str(row[col_map['consignment']]),
                    length_m=float(row[col_map['length']]),
                    width_m=float(row[col_map['width']]),
                    height_m=float(row[col_map['height']]),
                    mass_kg=mass_kg,
                    rotated=False
                )
                items.append(item)
            except Exception as e:
                print(f"   Warning: Skipping row {idx}: {e}")
        
        print(f"✅ Loaded {len(items)} items")
        return items
    
    except Exception as e:
        print(f"❌ Error loading file: {e}")
        return None


def create_trailers(trailer_type="Flatbed Standard", num_trailers=3):
    """Create trailer objects based on type"""
    from optimizer_engine import Trailer
    
    # Trailer specifications (length, width, deck_height, max_payload, max_rear, max_kingpin, wheelbase, tare)
    trailer_specs = {
        "Flatbed Standard": {
            "name": "Flatbed",
            "length_m": 13.6,
            "width_m": 2.4,
            "deck_height_m": 1.2,
            "max_payload_kg": 28000,
            "max_rear_axle_kg": 18000,
            "max_kingpin_kg": 12000,
            "wheelbase_m": 10.5,
            "tare_kg": 6000
        },
        "Low-Loader": {
            "name": "Low-Loader",
            "length_m": 13.6,
            "width_m": 2.8,
            "deck_height_m": 0.8,
            "max_payload_kg": 35000,
            "max_rear_axle_kg": 22000,
            "max_kingpin_kg": 15000,
            "wheelbase_m": 9.5,
            "tare_kg": 8000
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
            "tare_kg": 10000
        }
    }
    
    specs = trailer_specs.get(trailer_type, trailer_specs["Flatbed Standard"])
    trailers = []
    
    for i in range(num_trailers):
        trailer = Trailer(
            name=f"{specs['name']}_{i+1}",
            type_name=trailer_type,
            length_m=specs["length_m"],
            width_m=specs["width_m"],
            deck_height_m=specs["deck_height_m"],
            max_payload_kg=specs["max_payload_kg"],
            max_rear_axle_kg=specs["max_rear_axle_kg"],
            max_kingpin_kg=specs["max_kingpin_kg"],
            wheelbase_m=specs["wheelbase_m"],
            trailer_tare_kg=specs["tare_kg"]
        )
        trailers.append(trailer)
    
    return trailers


def distribute_items_to_trailers(items, trailers, gap_m=0.2):
    """Distribute items across multiple trailers using heuristic"""
    items_sorted = sorted(items, key=lambda x: x.mass_kg, reverse=True)
    
    for trailer in trailers:
        trailer.items = []
        trailer.total_mass_kg = 0
    
    for item in items_sorted:
        placed = False
        for trailer in trailers:
            # Calculate current X position
            current_x = 0.2
            for existing in trailer.items:
                current_x += existing.length_m + gap_m
            
            can_fit, _ = trailer.can_add_item(item, current_x, gap_m)
            if can_fit:
                item.x_pos = current_x
                item.y_pos = 0.15
                trailer.add_item(item, current_x, 0.15)
                placed = True
                break
        
        if not placed:
            print(f"⚠️ Warning: Could not place {item.consignment} - need more trailers")
            # Create new trailer if needed (handled by caller)
            return False
    
    return True


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
    
    # Display loaded items
    print("\n   Loaded items:")
    for i, item in enumerate(items[:5]):
        print(f"   {i+1}. {item.consignment}: {item.length_m}m x {item.width_m}m x {item.height_m}m, {item.mass_kg/1000:.1f}t")
    if len(items) > 5:
        print(f"   ... and {len(items)-5} more")
    
    # ===== STEP 2: Create Trailers =====
    print("\n" + "-"*50)
    print("STEP 2: Configuring Trailers")
    print("-"*50)
    
    # Ask user for trailer type
    print("\n   Available trailer types:")
    print("   1. Flatbed Standard (13.6m, 28t payload)")
    print("   2. Low-Loader (13.6m, 35t payload, lower deck)")
    print("   3. Abnormal (18.0m, 50t payload, requires permit)")
    
    trailer_choice = input("\n   Select trailer type (1-3) [default: 1]: ").strip()
    if trailer_choice == "2":
        trailer_type = "Low-Loader"
    elif trailer_choice == "3":
        trailer_type = "Abnormal"
    else:
        trailer_type = "Flatbed Standard"
    
    # Calculate required number of trailers
    total_mass_tons = sum(i.mass_kg for i in items) / 1000
    specs = {"Flatbed Standard": 28, "Low-Loader": 35, "Abnormal": 50}
    payload_per_trailer = specs.get(trailer_type, 28)
    num_trailers = max(1, int(total_mass_tons / payload_per_trailer) + 1)
    num_trailers = min(num_trailers, 5)  # Cap at 5 trailers
    
    print(f"\n   Total mass: {total_mass_tons:.1f}t")
    print(f"   Using {num_trailers} x {trailer_type} trailer(s)")
    
    trailers = create_trailers(trailer_type, num_trailers)
    
    # ===== STEP 3: Distribute Items =====
    print("\n" + "-"*50)
    print("STEP 3: Optimizing Load Distribution")
    print("-"*50)
    
    success = distribute_items_to_trailers(items, trailers, gap_m=0.2)
    if not success:
        print("\n⚠️ Need more trailers! Adding one more...")
        trailers.append(create_trailers(trailer_type, 1)[0])
        success = distribute_items_to_trailers(items, trailers, gap_m=0.2)
    
    print(f"\n   Distribution complete:")
    for trailer in trailers:
        if trailer.items:
            print(f"   {trailer.name}: {len(trailer.items)} items, {trailer.total_mass_kg/1000:.1f}t")
    
    # ===== STEP 4: Legal Compliance & In-Gauge Classification =====
    print("\n" + "-"*50)
    print("STEP 4: Legal Compliance & Cargo Classification")
    print("-"*50)
    
    validator = SARoadTrafficValidator(province="WesternCape")
    audit_results = []
    
    for trailer in trailers:
        if trailer.items:
            audit = validator.full_legal_audit(trailer, trailer.items)
            audit_results.append(audit)
            validator.print_legal_report(audit)
    
    # ===== STEP 5: Generate Visualizations =====
    print("\n" + "-"*50)
    print("STEP 5: Generating 2D Visualizations")
    print("-"*50)
    
    for i, trailer in enumerate(trailers):
        if trailer.items:
            print(f"   Generating views for {trailer.name}...")
            # Create and save top-down view
            fig1 = create_top_down_view(trailer)
            fig1.savefig(f"loading_plan_{trailer.name}_topdown.png", dpi=150, bbox_inches='tight')
            print(f"   ✅ Saved: loading_plan_{trailer.name}_topdown.png")
            
            # Create and save side view
            fig2 = create_side_view(trailer)
            fig2.savefig(f"loading_plan_{trailer.name}_side.png", dpi=150, bbox_inches='tight')
            print(f"   ✅ Saved: loading_plan_{trailer.name}_side.png")
            
            # Close figures to free memory
            import matplotlib.pyplot as plt
            plt.close(fig1)
            plt.close(fig2)
    
    # ===== STEP 6: Export Manifest =====
    print("\n" + "-"*50)
    print("STEP 6: Exporting Loading Manifest")
    print("-"*50)
    
    # Prepare items_by_trailer for exporter
    items_by_trailer = [trailer.items for trailer in trailers if trailer.items]
    non_empty_trailers = [trailer for trailer in trailers if trailer.items]
    
    excel_file, csv_file, df_sequence = export_manifest(
        trailers=non_empty_trailers,
        items_by_trailer=items_by_trailer,
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
    print(f"   📊 {excel_file}")
    print(f"   📄 {csv_file}")
    print(f"   📝 LOADING_INSTRUCTIONS.txt")
    for trailer in non_empty_trailers:
        print(f"   🖼️ loading_plan_{trailer.name}_topdown.png")
        print(f"   🖼️ loading_plan_{trailer.name}_side.png")
    
    # Determine overall status
    all_compliant = all(a.get("compliant", False) for a in audit_results)
    all_ingauge = all(a.get("commercial_classification", {}).get("is_in_gauge", False) for a in audit_results)
    
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
    parser.add_argument('--trailer', '-t', type=str, choices=['flatbed', 'lowloader', 'abnormal'],
                        default='flatbed', help='Trailer type')
    
    args = parser.parse_args()
    
    # Run the pipeline
    success = run_master_configurator(input_file=args.file)
    
    if not success:
        print("\n❌ Pipeline failed. Please check your input file and try again.")
        sys.exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    main()