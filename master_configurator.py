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
from optimizer_engine import Item, Trailer
from rules_validator import SARoadTrafficValidator
from visualizer_2d import create_top_down_view, create_side_view
from exporter import export_manifest, print_loading_instructions
from trailer_library import SuperlinkTrailer, TRAILER_TYPES


def find_input_file():
    """Automatically find the consignment file in current directory"""
    current_dir = Path.cwd()
    
    patterns = [
        "*GENSETS*.xlsx", "*GENSETS*.csv",
        "*consignment*.xlsx", "*consignment*.csv",
        "sample_data.xlsx", "sample_data.csv",
        "*.xlsx", "*.csv"
    ]
    
    for pattern in patterns:
        files = list(current_dir.glob(pattern))
        if files:
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
        
        print(f"   Found columns: {list(df.columns)}")
        
        # Find columns (case-insensitive)
        col_map = {}
        for col in df.columns:
            col_upper = str(col).upper()
            if 'CONSIGNMENT' in col_upper or 'ORDER' in col_upper:
                col_map['consignment'] = col
            elif 'LENGTH' in col_upper or 'LEN' in col_upper:
                col_map['length'] = col
            elif 'WIDTH' in col_upper or 'WID' in col_upper:
                col_map['width'] = col
            elif 'HEIGHT' in col_upper or 'HEI' in col_upper:
                col_map['height'] = col
            elif 'MASS' in col_upper or 'WEIGHT' in col_upper:
                col_map['mass'] = col
        
        # Default column mapping if not found
        if 'consignment' not in col_map and len(df.columns) > 0:
            col_map['consignment'] = df.columns[0]
        if 'length' not in col_map and len(df.columns) > 1:
            col_map['length'] = df.columns[1]
        if 'width' not in col_map and len(df.columns) > 2:
            col_map['width'] = df.columns[2]
        if 'height' not in col_map and len(df.columns) > 3:
            col_map['height'] = df.columns[3]
        if 'mass' not in col_map and len(df.columns) > 4:
            col_map['mass'] = df.columns[4]
        
        # Create Item objects
        items = []
        
        for idx, row in df.iterrows():
            try:
                consignment = str(row[col_map['consignment']])
                if pd.isna(consignment) or consignment == 'nan':
                    consignment = f"ITEM_{idx+1}"
                
                length_m = float(row[col_map['length']])
                width_m = float(row[col_map['width']])
                height_m = float(row[col_map['height']])
                mass_val = float(row[col_map['mass']])
                
                # Convert tonnes to kg if needed (mass < 100 likely tonnes)
                if mass_val < 100:
                    mass_kg = mass_val * 1000
                else:
                    mass_kg = mass_val
                
                if length_m > 0 and width_m > 0 and height_m > 0 and mass_kg > 0:
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
                continue
        
        # Sort items by length (largest first) for better packing
        items.sort(key=lambda x: -x.length_m)
        
        print(f"✅ Loaded {len(items)} items")
        print(f"   Total mass: {sum(i.mass_kg for i in items)/1000:.1f} tonnes")
        if items:
            print(f"   Longest item: {items[0].consignment} ({items[0].length_m:.2f}m)")
            print(f"   Shortest item: {items[-1].consignment} ({items[-1].length_m:.2f}m)")
        
        return items
    
    except Exception as e:
        print(f"❌ Error loading file: {e}")
        return None


def safe_text(text):
    """Remove emoji characters that cause encoding issues"""
    import re
    return re.sub(r'[^\x00-\x7F]+', '', text)


def pack_superlink(superlink, items):
    """
    Pack items into a Superlink using best-fit algorithm.
    Returns: (packed_items, remaining_items, front_mass, rear_mass)
    """
    # Sort items by length (largest first) for efficient packing
    items_to_pack = sorted(items, key=lambda x: -x.length_m)
    
    # Track space on each trailer
    front_space = [{'start': 0.2, 'end': superlink.front["length_m"]}]
    rear_space = [{'start': 0.2, 'end': superlink.rear["length_m"]}]
    
    front_items = []
    rear_items = []
    front_mass = 0
    rear_mass = 0
    
    packed_items = []
    remaining = []
    
    for item in items_to_pack:
        placed = False
        
        # Try front trailer first (better weight distribution)
        for space in front_space[:]:
            if space['end'] - space['start'] >= item.length_m:
                if front_mass + item.mass_kg <= superlink.front["max_payload_kg"]:
                    item.x_pos = space['start']
                    item.y_pos = 0.15
                    front_items.append(item)
                    front_mass += item.mass_kg
                    
                    new_start = space['start'] + item.length_m + 0.2
                    if new_start < space['end']:
                        space['start'] = new_start
                    else:
                        front_space.remove(space)
                    
                    packed_items.append(item)
                    placed = True
                    break
        
        if not placed:
            # Try rear trailer
            for space in rear_space[:]:
                if space['end'] - space['start'] >= item.length_m:
                    if rear_mass + item.mass_kg <= superlink.rear["max_payload_kg"]:
                        item.x_pos = space['start']
                        item.y_pos = 0.15
                        rear_items.append(item)
                        rear_mass += item.mass_kg
                        
                        new_start = space['start'] + item.length_m + 0.2
                        if new_start < space['end']:
                            space['start'] = new_start
                        else:
                            rear_space.remove(space)
                        
                        packed_items.append(item)
                        placed = True
                        break
        
        if not placed:
            remaining.append(item)
    
    # Add items to superlink
    for item in front_items:
        superlink.add_item_to_front(item, item.x_pos)
    for item in rear_items:
        superlink.add_item_to_rear(item, item.x_pos)
    
    return packed_items, remaining, front_mass, rear_mass


def run_master_configurator(input_file=None):
    """Main function - runs complete pipeline"""
    print("\n" + "="*70)
    print("FML LOAD CONFIGURATOR - MASTER PIPELINE")
    print("="*70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # ===== STEP 1: Load Data =====
    print("\n" + "-"*50)
    print("STEP 1: Loading Consignment Data")
    print("-"*50)
    
    if input_file is None:
        input_file = find_input_file()
    
    if input_file is None:
        print("\n[ERROR] No input file found!")
        return False
    
    items = load_items_from_file(Path(input_file))
    if not items:
        return False
    
    total_mass_kg = sum(item.mass_kg for item in items)
    total_mass_tons = total_mass_kg / 1000
    
    # ===== STEP 2: Select Trailer Type (UPDATED with Tri-Axle options) =====
    print("\n" + "-"*50)
    print("STEP 2: Configuring Trailers")
    print("-"*50)
    
    print("\n   Available trailer types:")
    print("   1. Flatbed Standard (13.6m, 28t payload, 2 axles)")
    print("   2. Low-Loader (13.6m, 35t payload, 2 axles)")
    print("   3. TRI-AXLE Flatbed (13.6m, 30t payload, 3 axles)")
    print("   4. TRI-AXLE Low-Loader (13.6m, 35t payload, 3 axles)")
    print("   5. Abnormal (18.0m, 50t payload, requires permit)")
    print("   6. SUPERLINK (6m + 12m, 34t payload)")
    print("   7. SUPERLINK Tri-Axle (6m + 12m tri-axle rear, 34t)")
    print("   8. INTERLINK (6m + 6m, 34t payload)")
    
    choice = input("\n   Select (1-8) [default: 1]: ").strip()
    
    if choice == "2":
        trailer_type = "Low-Loader"
        is_superlink = False
    elif choice == "3":
        trailer_type = "Tri-Axle Flatbed"
        is_superlink = False
    elif choice == "4":
        trailer_type = "Tri-Axle Low-Loader"
        is_superlink = False
    elif choice == "5":
        trailer_type = "Abnormal (Extendable)"
        is_superlink = False
    elif choice == "6":
        trailer_type = "Superlink (6m + 12m)"
        is_superlink = True
    elif choice == "7":
        trailer_type = "Tri-Axle Superlink"
        is_superlink = True
    elif choice == "8":
        trailer_type = "Interlink (6m + 6m)"
        is_superlink = True
    else:
        trailer_type = "Flatbed Standard"
        is_superlink = False
    
    print(f"\n   Selected: {trailer_type}")
    
    # ===== STEP 3: Distribute Items =====
    print("\n" + "-"*50)
    print("STEP 3: Optimizing Load Distribution")
    print("-"*50)
    
    if is_superlink:
        print(f"\n   Using {trailer_type}")
        
        # Pack items into Superlinks
        all_superlinks = []
        remaining_items = items.copy()
        sl_idx = 0
        
        while remaining_items and sl_idx < 10:  # Max 10 Superlinks
            sl_idx += 1
            superlink = SuperlinkTrailer(name=f"Superlink_{sl_idx}", config_type=trailer_type)
            
            packed, remaining, front_mass, rear_mass = pack_superlink(superlink, remaining_items)
            remaining_items = remaining
            
            if packed:
                all_superlinks.append(superlink)
                print(f"\n   {superlink.name}:")
                print(f"      Front: {len(superlink.front['items'])} items, {front_mass/1000:.1f}t / {superlink.front['max_payload_kg']/1000:.0f}t")
                print(f"      Rear: {len(superlink.rear['items'])} items, {rear_mass/1000:.1f}t / {superlink.rear['max_payload_kg']/1000:.0f}t")
                print(f"      Total: {(front_mass+rear_mass)/1000:.1f}t / {superlink.max_payload_kg/1000:.0f}t")
            else:
                break
        
        trailers = all_superlinks
        
        # Calculate totals
        total_placed = sum(len(sl.get_all_items()) for sl in trailers)
        total_placed_mass = sum(sl.total_mass_kg for sl in trailers) / 1000
        
        print(f"\n   SUMMARY:")
        print(f"   Total Superlinks used: {len(trailers)}")
        print(f"   Total items placed: {total_placed} / {len(items)}")
        print(f"   Total mass placed: {total_placed_mass:.1f} / {total_mass_tons:.1f} tonnes")
        print(f"   Utilization: {total_placed_mass/total_mass_tons*100:.1f}%")
        
        if remaining_items:
            print(f"\n   WARNING: {len(remaining_items)} items could not be placed!")
            print(f"   Remaining mass: {sum(i.mass_kg for i in remaining_items)/1000:.1f}t")
        
    else:
        # Handle standard single trailers (including Tri-Axle)
        specs = {
            "Flatbed Standard": 28000,
            "Low-Loader": 35000,
            "Tri-Axle Flatbed": 30000,
            "Tri-Axle Low-Loader": 35000,
            "Abnormal (Extendable)": 50000
        }
        
        # Get rear axle limit based on trailer type
        rear_axle_limits = {
            "Flatbed Standard": 18000,
            "Low-Loader": 18000,
            "Tri-Axle Flatbed": 27000,
            "Tri-Axle Low-Loader": 27000,
            "Abnormal (Extendable)": 30000
        }
        
        payload_per_trailer = specs.get(trailer_type, 28000)
        rear_axle_limit = rear_axle_limits.get(trailer_type, 18000)
        num_trailers = max(1, int(total_mass_kg / payload_per_trailer) + 1)
        num_trailers = min(num_trailers, 5)
        
        print(f"\n   Using {num_trailers} x {trailer_type} trailer(s)")
        print(f"   Each trailer rear axle limit: {rear_axle_limit/1000:.0f}t")
        
        from optimizer_engine import Trailer
        
        trailers = []
        for i in range(num_trailers):
            trailer = Trailer(
                name=f"{trailer_type}_{i+1}",
                type_name=trailer_type,
                length_m=13.6 if "Abnormal" not in trailer_type else 18.0,
                width_m=2.8 if "Low-Loader" in trailer_type else 2.4,
                deck_height_m=0.8 if "Low-Loader" in trailer_type else 1.2,
                max_payload_kg=payload_per_trailer,
                max_rear_axle_kg=rear_axle_limit,
                max_kingpin_kg=12000 if "Tri-Axle" not in trailer_type else 15000,
                wheelbase_m=10.5,
                trailer_tare_kg=7000 if "Tri-Axle" in trailer_type else 6000
            )
            # Add axle configuration for tri-axle
            if "Tri-Axle" in trailer_type:
                trailer.axle_configuration = [
                    {"type": "steering", "axle_count": 1},
                    {"type": "triaxle", "axle_count": 3}
                ]
            trailers.append(trailer)
        
        # Distribute items to standard trailers
        items_sorted = sorted(items, key=lambda x: -x.length_m)
        for t_idx, trailer in enumerate(trailers):
            current_x = 0.2
            for item in items_sorted[t_idx::num_trailers]:
                if current_x + item.length_m <= trailer.length_m:
                    if trailer.total_mass_kg + item.mass_kg <= trailer.max_payload_kg:
                        # Also check rear axle limit
                        estimated_rear_load = (trailer.total_mass_kg + item.mass_kg) * 0.7
                        if estimated_rear_load <= trailer.max_rear_axle_kg:
                            item.x_pos = current_x
                            item.y_pos = 0.15
                            trailer.add_item(item, current_x, 0.15)
                            current_x += item.length_m + 0.2
        
        trailers = [t for t in trailers if t.items]
    
    # ===== STEP 4: Legal Compliance =====
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
            try:
                audit = validator.full_legal_audit(trailer, trailer_items)
                audit_results.append(audit)
                print(f"\n   {trailer.name}: {len(trailer_items)} items, {sum(i.mass_kg for i in trailer_items)/1000:.1f}t")
            except Exception as e:
                print(f"   Audit error for {trailer.name}: {e}")
    
    # ===== STEP 5: Generate Visualizations =====
    print("\n" + "-"*50)
    print("STEP 5: Generating Visualizations")
    print("-"*50)
    
    import matplotlib.pyplot as plt
    plt.rcParams['font.sans-serif'] = ['Arial']
    
    for trailer in trailers:
        try:
            trailer_name = safe_text(trailer.name)
            fig1 = create_top_down_view(trailer)
            fig1.savefig(f"loading_plan_{trailer_name}_topdown.png", dpi=150, bbox_inches='tight')
            print(f"   [OK] Saved: loading_plan_{trailer_name}_topdown.png")
            
            fig2 = create_side_view(trailer)
            fig2.savefig(f"loading_plan_{trailer_name}_side.png", dpi=150, bbox_inches='tight')
            print(f"   [OK] Saved: loading_plan_{trailer_name}_side.png")
            
            plt.close(fig1)
            plt.close(fig2)
        except Exception as e:
            print(f"   [WARN] Could not generate visualization for {trailer.name}: {e}")
    
    # ===== STEP 6: Export =====
    print("\n" + "-"*50)
    print("STEP 6: Exporting Manifest")
    print("-"*50)
    
    export_trailers = []
    export_items_by_trailer = []
    
    for trailer in trailers:
        if hasattr(trailer, 'get_all_items'):
            trailer_items = trailer.get_all_items()
        else:
            trailer_items = trailer.items
        
        if trailer_items:
            export_trailers.append(trailer)
            export_items_by_trailer.append(trailer_items)
    
    if export_trailers:
        excel_file, csv_file, df_sequence = export_manifest(
            trailers=export_trailers,
            items_by_trailer=export_items_by_trailer,
            validator_results=audit_results,
            filename="LOADING_MANIFEST"
        )
        
        # Save instructions without emoji
        with open("LOADING_INSTRUCTIONS.txt", "w", encoding='utf-8') as f:
            for _, row in df_sequence.iterrows():
                action = safe_text(row['Action'])
                f.write(f"Step {int(row['Step']):2d}: Load {action} -> Position: {row['Position']} -> {row['Mass']}\n")
            f.write("\nIMPORTANT SAFETY NOTES\n")
            f.write("1. Ensure 20cm gap between all units for lashing\n")
            f.write("2. Verify axle loads before departure\n")
            f.write("3. All loads must comply with Regulation 240 of Act 93/1996\n")
        
        print(f"\n[OK] Saved: LOADING_INSTRUCTIONS.txt")
        print(f"[OK] Saved: {excel_file}")
        print(f"[OK] Saved: {csv_file}")
    
    # ===== SUMMARY =====
    print("\n" + "="*70)
    print("MASTER PIPELINE COMPLETE")
    print("="*70)
    print(f"\n   Total units used: {len(export_trailers)}")
    print(f"   Total items placed: {sum(len(t) for t in export_items_by_trailer)} / {len(items)}")
    if export_trailers:
        total_placed_mass = sum(t.total_mass_kg if hasattr(t, 'total_mass_kg') else sum(i.mass_kg for i in t.items) for t in export_trailers) / 1000
        print(f"   Total mass placed: {total_placed_mass:.1f} / {total_mass_tons:.1f} tonnes")
    print("="*70)
    
    return True


def main():
    import argparse
    parser = argparse.ArgumentParser(description='FML Load Configurator')
    parser.add_argument('--file', '-f', type=str, help='Path to consignment file')
    args = parser.parse_args()
    
    success = run_master_configurator(input_file=args.file)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()