"""Main Tkinter Desktop Application"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
from pathlib import Path
import threading

from trailer_library import TRAILER_TYPES, list_trailers, get_trailer
from optimizer_engine import Item, Trailer, AutoOptimizer
from visualizer_2d import create_top_down_view, create_side_view, generate_all_views
from exporter import export_manifest, print_loading_instructions
from rules_validator import SARoadTrafficValidator

class LoadConfiguratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("FML Load Configurator - Genset Transport Optimizer")
        self.root.geometry("1400x900")
        
        self.items = []
        self.trailers = []
        self.validator = SARoadTrafficValidator()
        
        self.setup_ui()
        
    def setup_ui(self):
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Left panel - Input controls
        left_panel = ttk.LabelFrame(main_frame, text="1. Load Data", padding="10")
        left_panel.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5)
        
        # File input
        ttk.Button(left_panel, text="📂 Load Consignment File (Excel/CSV/TXT)", 
                   command=self.load_file).grid(row=0, column=0, pady=5, sticky=tk.W)
        
        self.file_label = ttk.Label(left_panel, text="No file loaded", foreground="gray")
        self.file_label.grid(row=1, column=0, pady=5, sticky=tk.W)
        
        # Manual entry
        ttk.Label(left_panel, text="Or Add Item Manually:").grid(row=2, column=0, pady=(10,5), sticky=tk.W)
        
        entry_frame = ttk.Frame(left_panel)
        entry_frame.grid(row=3, column=0, pady=5)
        
        ttk.Label(entry_frame, text="Consignment:").grid(row=0, column=0, sticky=tk.W)
        self.cons_entry = ttk.Entry(entry_frame, width=15)
        self.cons_entry.grid(row=0, column=1, padx=5)
        
        ttk.Label(entry_frame, text="L(m):").grid(row=0, column=2, sticky=tk.W)
        self.len_entry = ttk.Entry(entry_frame, width=8)
        self.len_entry.grid(row=0, column=3, padx=5)
        
        ttk.Label(entry_frame, text="W(m):").grid(row=0, column=4, sticky=tk.W)
        self.wid_entry = ttk.Entry(entry_frame, width=8)
        self.wid_entry.grid(row=0, column=5, padx=5)
        
        ttk.Label(entry_frame, text="H(m):").grid(row=0, column=6, sticky=tk.W)
        self.hei_entry = ttk.Entry(entry_frame, width=8)
        self.hei_entry.grid(row=0, column=7, padx=5)
        
        ttk.Label(entry_frame, text="Mass(t):").grid(row=0, column=8, sticky=tk.W)
        self.mass_entry = ttk.Entry(entry_frame, width=8)
        self.mass_entry.grid(row=0, column=9, padx=5)
        
        ttk.Button(entry_frame, text="➕ Add", command=self.add_manual_item).grid(row=0, column=10, padx=10)
        
        # Items list
        ttk.Label(left_panel, text="Consignment Items:").grid(row=4, column=0, pady=(10,5), sticky=tk.W)
        
        self.items_listbox = tk.Listbox(left_panel, height=12, width=50)
        self.items_listbox.grid(row=5, column=0, pady=5, sticky=(tk.W, tk.E))
        
        ttk.Button(left_panel, text="🗑 Remove Selected", command=self.remove_item).grid(row=6, column=0, pady=5)
        
        # Trailer selection
        trailer_frame = ttk.LabelFrame(main_frame, text="2. Select Trailers", padding="10")
        trailer_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=10, padx=5)
        
        ttk.Label(trailer_frame, text="Add trailer type:").grid(row=0, column=0, sticky=tk.W)
        self.trailer_combo = ttk.Combobox(trailer_frame, values=list_trailers(), width=20)
        self.trailer_combo.grid(row=0, column=1, padx=5)
        ttk.Button(trailer_frame, text="➕ Add Trailer", command=self.add_trailer).grid(row=0, column=2, padx=5)
        
        self.trailer_listbox = tk.Listbox(trailer_frame, height=4, width=50)
        self.trailer_listbox.grid(row=1, column=0, columnspan=3, pady=5, sticky=(tk.W, tk.E))
        
        # Action buttons
        action_frame = ttk.Frame(main_frame)
        action_frame.grid(row=2, column=0, pady=10)
        
        ttk.Button(action_frame, text="🚛 RUN OPTIMIZER", command=self.run_optimizer,
                   style="Accent.TButton").grid(row=0, column=0, padx=5)
        ttk.Button(action_frame, text="📊 Export Manifest", command=self.export_manifest).grid(row=0, column=1, padx=5)
        ttk.Button(action_frame, text="🖨️ Print Instructions", command=self.print_instructions).grid(row=0, column=2, padx=5)
        
        # Right panel - Visualization
        right_panel = ttk.LabelFrame(main_frame, text="3. Load Visualization", padding="10")
        right_panel.grid(row=0, column=1, rowspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10)
        
        self.view_notebook = ttk.Notebook(right_panel)
        self.view_notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.topdown_frame = ttk.Frame(self.view_notebook)
        self.side_frame = ttk.Frame(self.view_notebook)
        self.view_notebook.add(self.topdown_frame, text="Top-Down View")
        self.view_notebook.add(self.side_frame, text="Side Profile View")
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(0, weight=1)
        right_panel.columnconfigure(0, weight=1)
        right_panel.rowconfigure(0, weight=1)
        
        # Style
        style = ttk.Style()
        style.configure("Accent.TButton", font=('Arial', 10, 'bold'))
        
    def load_file(self):
        filepath = filedialog.askopenfilename(
            title="Select consignment file",
            filetypes=[("Excel files", "*.xlsx *.xls"), ("CSV files", "*.csv"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        if not filepath:
            return
        
        try:
            if filepath.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(filepath)
            else:
                df = pd.read_csv(filepath)
            
            # Find relevant columns
            df = df.dropna(subset=[df.columns[0]])  # Drop empty rows
            
            # Map columns (flexible)
            cons_col = next((c for c in df.columns if 'CONSIGNMENT' in c.upper() or 'ORDER' in c.upper()), df.columns[0])
            len_col = next((c for c in df.columns if 'LENGTH' in c.upper() or 'LEN' in c.upper()), None)
            wid_col = next((c for c in df.columns if 'WIDTH' in c.upper() or 'WID' in c.upper()), None)
            hei_col = next((c for c in df.columns if 'HEIGHT' in c.upper() or 'HEI' in c.upper()), None)
            mass_col = next((c for c in df.columns if 'MASS' in c.upper() or 'WEIGHT' in c.upper()), None)
            
            if not all([len_col, wid_col, hei_col, mass_col]):
                messagebox.showerror("Error", "Could not find required columns (LENGTH, WIDTH, HEIGHT, MASS)")
                return
            
            self.items = []
            for _, row in df.iterrows():
                try:
                    item = Item(
                        consignment=str(row[cons_col]),
                        length_m=float(row[len_col