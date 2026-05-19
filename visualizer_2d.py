"""2D visualizations using matplotlib (top-down + side profile)"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from typing import List, Optional


def create_top_down_view(trailer, parent_frame=None):
    """Create top-down view of trailer with items - handles Superlink correctly"""
    fig, ax = plt.subplots(figsize=(14, 6))
    
    # Check if this is a Superlink (has front and rear trailers)
    is_superlink = hasattr(trailer, 'front') and hasattr(trailer, 'rear')
    
    if is_superlink:
        # Draw front trailer (6m)
        front_rect = patches.Rectangle(
            (0, 0), trailer.front["length_m"], trailer.front["width_m"],
            linewidth=2, edgecolor='black', facecolor='lightgray', alpha=0.3
        )
        ax.add_patch(front_rect)
        
        # Draw rear trailer (12m) - offset by articulation gap
        rear_x = trailer.front["length_m"] + trailer.