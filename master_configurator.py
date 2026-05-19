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
        
        print(f"✅ Loaded {len(items)} items")
        return items
    
    except Exception as e:
        print(f"❌ Error loading file: {e}")
        return None


def distribute_to_superlink(items, superlink, gap_m=0.2):
    """
    Intelligently distribute items to Superlink front and rear trailers.
    Uses best-fit algorithm based on item size and weight.
    """
    # Sort items: heaviest first for weight distribution, then largest length
    items_sorted = sorted(items, key=lambda x: (-x.mass_kg, -x.length_m))
    
    # Track positions
    front_x = 0.2
    rear_x = 0.2
    
    # First pass: Place heavy/large items
    for item in items_sorted:
        # Try front trailer first (better for weight distribution)
        can_fit_front, _ = superlink.can_add_item_to_front(item, front_x, gap_m)
        can_fit_rear, _ = superlink.can_add_item_to_rear(item, rear_x, gap_m)
        
        # Calculate current utilization
        front_util = superlink.front["total_mass_kg"] / superlink.front["max_payload_kg"]
        rear_util = superlink.rear["total_mass_kg"] / superlink.rear["max_payload_kg"]
        
        # Place in less loaded trailer, preferring front for heavy items
        if can_fit_front and (front_util <= rear_util or item.mass_kg > 5000):
            superlink.add_item_to_front(item, front_x)
            front_x += item.length_m + gap_m
        elif can_fit_rear:
            superlink.add_item_to_rear(item, rear_x)
            rear_x += item.length_m + gap_m
        else:
            # Item doesn't fit - record but continue
            pass
    
    return superlink


def distribute_to_trailers(items, trailers, gap_m=0.2):
    """Distribute items across multiple standard trailers"""
    items_sorted = sorted(items, key=lambda x: -x.mass_kg)
    
    for trailer in trailers:
        trailer.items = []
        trailer.total_mass_kg = 0
    
    for item in items_sorted:
        placed = False
        
        for trailer in trailers:
            current_x = 0.2
            for existing in trailer.items:
                current_x += existing.length_m + gap_m
            
            if current_x + item.length_m <= trailer.length_m:
                if trailer.total_mass_kg + item.mass_kg <= trailer.max_payload_kg:
                    item.x_pos = current_x
                    item.y_pos = 0.15
                    trailer.add_item(item, current_x, 0.15)
                    placed = True
                    break
        
        if not placed:
            # Create new trailer if needed
            pass
    
    return [t for t in trailers if t.items]


def run_master_configurator(input_file=None):
    """Main function - runs complete pipeline"""
    print("\n" + "="*70)
    print("🚛 FML LOAD CONFIGURATOR - MASTER PIPELINE")
    print("="*70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # ===== STEP 1: Load Data =====
    print("\n" + "-"*50)
    print("STEP 1: Loading Consignment Data")
    print("-"*50)
    
    if input_file is None:
        input_file = find_input_file()
    
    if input_file is None:
        print("\n❌ No input file found!")
        return False
    
    items = load_items_from_file(Path(input_file))
    if not items:
        return False
    
    total_mass_kg = sum(item.mass_kg for item in items)
    total_mass_tons = total_mass_kg / 1000
    
    print(f"\n   Total items: {len(items)}")
    print(f"   Total mass: {total_mass_tons:.1f} tonnes")
    
    # ===== STEP 2: Select Trailer Type =====
    print("\n" + "-"*50)
    print("STEP 2: Configuring Trailers")
    print("-"*50)
    
    print("\n   Available trailer types:")
    print("   1. Flatbed Standard (13.6m, 28t payload)")
    print("   2. Low-Loader (13.6m, 35t payload)")
    print("   3. Abnormal (18.0m, 50t payload, requires permit)")
    print("   4. SUPERLINK (6m + 12m, 34t payload)")
    print("   5. INTERLINK (6m + 6m, 34t payload)")
    
    choice = input("\n   Select (1-5) [default: 1]: ").strip()
    
    if choice == "2":
        trailer_type = "Low-Loader"
        is_superlink = False
    elif choice == "3":
        trailer_type = "Abnormal"
        is_superlink = False
    elif choice == "4":
        trailer_type = "Superlink (6m + 12m)"
        is_superlink = True
    elif choice == "5":
        trailer_type = "Interlink (6m + 6m)"
        is_superlink = True
    else:
        trailer_type = "Flatbed Standard"
        is_superlink = False
    
    # ===== STEP 3: Distribute Items =====
    print("\n" + "-"*50)
    print("STEP 3: Optimizing Load Distribution")
    print("-"*50)
    
    if is_superlink:
        # Handle Superlink
        print(f"\n   Using {trailer_type}")
        
        # Calculate how many Superlinks needed
        payload_per_superlink = 34000  # 34 tonnes
        num_superlinks = max(1, int(total_mass_kg / payload_per_superlink) + 1)
        num_superlinks = min(num_superlinks, 3)  # Max 3 Superlinks
        
        print(f"   Need {num_superlinks} Superlink(s) for {total_mass_tons:.1f}t")
        
        all_superlinks = []
        remaining_items = items.copy()
        
        for sl_idx in range(num_superlinks):
            superlink = SuperlinkTrailer(name=f"Superlink_{sl_idx+1}", config_type=trailer_type)
            
            # Calculate capacity for this Superlink (even distribution)
            target_payload = total_mass_kg / num_superlinks
            
            # Select items for this Superlink
            sl_items = []
            current_payload = 0
            
            for item in sorted(remaining_items, key=lambda x: -x.mass_kg):
                if current_payload + item.mass_kg <= target_payload + 5000:  # Allow 5t buffer
                    sl_items.append(item)
                    current_payload += item.mass_kg
            
            # Remove selected items from remaining
            for item in sl_items:
                remaining_items.remove(item)
            
            # Distribute to front/rear
            front_x = 0.2
            rear_x = 0.2
            
            for item in sorted(sl_items, key=lambda x: -x.mass_kg):
                # Try front first
                can_fit_front, _ = superlink.can_add_item_to_front(item, front_x)
                if can_fit_front and superlink.front["total_mass_kg"] + item.mass_kg <= superlink.front["max_payload_kg"]:
                    superlink.add_item_to_front(item, front_x)
                    front_x += item.length_m + 0.2
                else:
                    # Try rear
                    can_fit_rear, _ = superlink.can_add_item_to_rear(item, rear_x)
                    if can_fit_rear:
                        superlink.add_item_to_rear(item, rear_x)
                        rear_x += item.length_m + 0.2
            
            all_superlinks.append(superlink)
            
            print(f"\n   {superlink.name}:")
            print(f"      Front: {len(superlink.front['items'])} items, {superlink.front['total_mass_kg']/1000:.1f}t / {superlink.front['max_payload_kg']/1000:.0f}t")
            print(f"      Rear: {len(superlink.rear['items'])} items, {superlink.rear['total_mass_kg']/1000:.1f}t / {superlink.rear['max_payload_kg']/1000:.0f}t")
            print(f"      Total: {superlink.total_mass_kg/1000:.1f}t / {superlink.max_payload_kg/1000:.0f}t")
        
        trailers = all_superlinks
        items_by_trailer = [sl.get_all_items() for sl in all_superlinks]
        
    else:
        # Handle standard trailers
        specs = {"Flatbed Standard": 28000, "Low-Loader": 35000, "Abnormal": 50000}
        payload_per_trailer = specs.get(trailer_type, 28000)
        
        num_trailers = max(1, int(total_mass_kg / payload_per_trailer) + 1)
        num_trailers = min(num_trailers, 5)
        
        print(f"\n   Using {num_trailers} x {trailer_type} trailer(s)")
        
        # Create trailers
        from optimizer_engine import Trailer
        
        trailers = []
        for i in range(num_trailers):
            trailer = Trailer(
                name=f"{trailer_type}_{i+1}",
                type_name=trailer_type,
                length_m=13.6 if trailer_type != "Abnormal" else 18.0,
                width_m=2.4 if trailer_type != "Low-Loader" else 2.8,
                deck_height_m=1.2,
                max_payload_kg=payload_per_trailer,
                max_rear_axle_kg=18000,
                max_kingpin_kg=12000,
                wheelbase_m=10.5,
                trailer_tare_kg=6000
            )
            trailers.append(trailer)
        
        # Distribute items evenly
        items_sorted = sorted(items, key=lambda x: -x.mass_kg)
        items_per_trailer = len(items_sorted) // num_trailers
        
        for t_idx, trailer in enumerate(trailers):
            start_idx = t_idx * items_per_trailer
            end_idx = start_idx + items_per_trailer if t_idx < num_trailers - 1 else len(items_sorted)
            
            current_x = 0.2
            for item in items_sorted[start_idx:end_idx]:
                item.x_pos = current_x
                item.y_pos = 0.15
                trailer.add_item(item, current_x, 0.15)
                current_x += item.length_m + 0.2
        
        items_by_trailer = [t.items for t in trailers if t.items]
        trailers = [t for t in trailers if t.items]
    
    # ===== STEP 4: Legal Compliance =====
    print("\n" + "-"*50)
    print("STEP 4: Legal Compliance & Cargo Classification")
    print("-"*50)
    
    validator = SARoadTrafficValidator(province="WesternCape")
    audit_results = []
    
    for trailer, t_items in zip(trailers, items_by_trailer):
        if t_items:
            try:
                audit = validator.full_legal_audit(trailer, t_items)
                audit_results.append(audit)
                validator.print_legal_report(audit)
            except Exception as e:
                print(f"   ⚠️ Audit error: {e}")
    
    # ===== STEP 5: Generate Visualizations =====
    print("\n" + "-"*50)
    print("STEP 5: Generating Visualizations")
    print("-"*50)
    
    for trailer in trailers:
        try:
            trailer_name = trailer.name
            fig1 = create_top_down_view(trailer)
            fig1.savefig(f"loading_plan_{trailer_name}_topdown.png", dpi=150, bbox_inches='tight')
            print(f"   ✅ Saved: loading_plan_{trailer_name}_topdown.png")
            
            fig2 = create_side_view(trailer)
            fig2.savefig(f"loading_plan_{trailer_name}_side.png", dpi=150, bbox_inches='tight')
            print(f"   ✅ Saved: loading_plan_{trailer_name}_side.png")
            
            import matplotlib.pyplot as plt
            plt.close(fig1)
            plt.close(fig2)
        except Exception as e:
            print(f"   ⚠️ Could not generate visualization: {e}")
    
    # ===== STEP 6: Export =====
    print("\n" + "-"*50)
    print("STEP 6: Exporting Manifest")
    print("-"*50)
    
    if trailers and items_by_trailer:
        excel_file, csv_file, df_sequence = export_manifest(
            trailers=trailers,
            items_by_trailer=items_by_trailer,
            validator_results=audit_results,
            filename="LOADING_MANIFEST"
        )
        
        instructions = print_loading_instructions(df_sequence)
        with open("LOADING_INSTRUCTIONS.txt", "w") as f:
            f.write(instructions)
        print("\n✅ Saved: LOADING_INSTRUCTIONS.txt")
    
    # ===== SUMMARY =====
    print("\n" + "="*70)
    print("✅ MASTER PIPELINE COMPLETE")
    print("="*70)
    print("\n📁 OUTPUT FILES:")
    if 'excel_file' in dir():
        print(f"   📊 {excel_file}")
        print(f"   📄 {csv_file}")
        print(f"   📝 LOADING_INSTRUCTIONS.txt")
    for trailer in trailers:
        print(f"   🖼️ loading_plan_{trailer.name}_topdown.png")
        print(f"   🖼️ loading_plan_{trailer.name}_side.png")
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