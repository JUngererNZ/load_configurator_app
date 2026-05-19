"""2D visualizations using matplotlib (top-down + side profile)"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from typing import List, Optional

def create_top_down_view(trailer, parent_frame=None):
    """Create top-down view of trailer with items"""
    fig, ax = plt.subplots(figsize=(14, 6))
    
    # Draw trailer bed
    trailer_rect = patches.Rectangle(
        (0, 0), trailer.length_m, trailer.width_m,
        linewidth=2, edgecolor='black', facecolor='lightgray', alpha=0.3
    )
    ax.add_patch(trailer_rect)
    
    # Draw axle positions
    for axle_x in [trailer.wheelbase_m * 0.3, trailer.wheelbase_m * 0.6, trailer.wheelbase_m]:
        ax.axvline(x=axle_x, ymin=0, ymax=1, color='red', linestyle='--', linewidth=1, alpha=0.5)
    
    # Draw items
    colors = plt.cm.Set3(range(len(trailer.items)))
    for item, color in zip(trailer.items, colors):
        rect = patches.Rectangle(
            (item.x_pos, item.y_pos), item.length_m, item.width_m,
            linewidth=2, edgecolor='blue', facecolor=color, alpha=0.7
        )
        ax.add_patch(rect)
        
        # Add label
        ax.text(item.x_pos + item.length_m/2, item.y_pos + item.width_m/2,
                f"{item.consignment}\n{item.mass_kg/1000:.1f}t",
                ha='center', va='center', fontsize=8, fontweight='bold')
    
    # Add kingpin marker
    ax.plot(0, trailer.width_m/2, '^', markersize=15, color='darkgreen', label='Kingpin')
    
    # Formatting
    ax.set_xlim(-0.5, trailer.length_m + 0.5)
    ax.set_ylim(-0.2, trailer.width_m + 0.2)
    ax.set_xlabel('Length (meters)', fontsize=12)
    ax.set_ylabel('Width (meters)', fontsize=12)
    
    # Add load info
    front, rear, cog = trailer.calculate_axle_loads()
    is_safe, violations = trailer.is_safe()
    
    info_text = f"Trailer: {trailer.name} ({trailer.type_name})\n"
    info_text += f"Total: {trailer.total_mass_kg/1000:.1f}t | "
    info_text += f"Front: {front/1000:.1f}t | Rear: {rear/1000:.1f}t\n"
    info_text += f"Status: {'✅ SAFE' if is_safe else '❌ OVERLOADED'}"
    
    ax.set_title(info_text, fontsize=10, color='green' if is_safe else 'red')
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3)
    
    if parent_frame:
        canvas = FigureCanvasTkAgg(fig, master=parent_frame)
        canvas.draw()
        return canvas.get_tk_widget()
    return fig


def create_side_view(trailer, parent_frame=None):
    """Create side profile view showing height and length"""
    fig, ax = plt.subplots(figsize=(14, 5))
    
    # Draw trailer deck
    ax.plot([0, trailer.length_m], [0, 0], 'k-', linewidth=3, color='brown')
    
    # Draw axle groups
    for axle_x in [trailer.wheelbase_m * 0.3, trailer.wheelbase_m * 0.6, trailer.wheelbase_m]:
        ax.plot([axle_x, axle_x], [-0.3, 0], 'r-', linewidth=2)
    
    # Draw items as blocks (height profile)
    for item in trailer.items:
        rect = patches.Rectangle(
            (item.x_pos, 0), item.length_m, item.height_m,
            linewidth=2, edgecolor='black', facecolor='steelblue', alpha=0.7
        )
        ax.add_patch(rect)
        
        # Add label above
        ax.text(item.x_pos + item.length_m/2, item.height_m + 0.05,
                item.consignment, ha='center', va='bottom', fontsize=7, rotation=45)
    
    # Add height limit line (4.3m SA legal limit)
    ax.axhline(y=4.3, xmin=0, xmax=1, color='red', linestyle='--', linewidth=2, 
               label=f'SA Legal Height Limit: 4.3m')
    
    # Check if any item exceeds height limit
    max_item_height = max([item.height_m for item in trailer.items], default=0)
    if max_item_height > 4.3:
        ax.fill_between([0, trailer.length_m], 4.3, max_item_height + 0.5, 
                        color='red', alpha=0.2, label='EXCEEDS LEGAL LIMIT')
    
    ax.set_xlim(-0.5, trailer.length_m + 0.5)
    ax.set_ylim(-0.5, max(5.0, max_item_height + 0.5))
    ax.set_xlabel('Length (meters)', fontsize=12)
    ax.set_ylabel('Height (meters)', fontsize=12)
    ax.set_title(f'Side Profile View - {trailer.name}')
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3)
    
    if parent_frame:
        canvas = FigureCanvasTkAgg(fig, master=parent_frame)
        canvas.draw()
        return canvas.get_tk_widget()
    return fig


def generate_all_views(trailers, output_prefix="loading_plan"):
    """Generate and save all views as PNG files"""
    for i, trailer in enumerate(trailers):
        # Top-down view
        fig1 = create_top_down_view(trailer)
        fig1.savefig(f"{output_prefix}_trailer_{i+1}_topdown.png", dpi=150, bbox_inches='tight')
        plt.close(fig1)
        
        # Side view
        fig2 = create_side_view(trailer)
        fig2.savefig(f"{output_prefix}_trailer_{i+1}_side.png", dpi=150, bbox_inches='tight')
        plt.close(fig2)

        def create_top_down_view(trailer, parent_frame=None):
    """Create top-down view of trailer with items - handles Superlink correctly"""
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    
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
        rear_x = trailer.front["length_m"] + trailer.articulation_gap_m
        rear_rect = patches.Rectangle(
            (rear_x, 0), trailer.rear["length_m"], trailer.rear["width_m"],
            linewidth=2, edgecolor='black', facecolor='lightgray', alpha=0.3
        )
        ax.add_patch(rear_rect)
        
        # Draw items on front trailer
        colors = plt.cm.Set3(range(len(trailer.front["items"])))
        for item, color in zip(trailer.front["items"], colors):
            rect = patches.Rectangle(
                (item.x_pos, item.y_pos), item.length_m, item.width_m,
                linewidth=2, edgecolor='blue', facecolor=color, alpha=0.7
            )
            ax.add_patch(rect)
            ax.text(item.x_pos + item.length_m/2, item.y_pos + item.width_m/2,
                    f"{item.consignment}\n{item.mass_kg/1000:.1f}t",
                    ha='center', va='center', fontsize=8, fontweight='bold')
        
        # Draw items on rear trailer
        colors = plt.cm.Set3(range(len(trailer.rear["items"])))
        for item, color in zip(trailer.rear["items"], colors):
            rect = patches.Rectangle(
                (item.x_pos + rear_x, item.y_pos), item.length_m, item.width_m,
                linewidth=2, edgecolor='blue', facecolor=color, alpha=0.7
            )
            ax.add_patch(rect)
            ax.text(item.x_pos + rear_x + item.length_m/2, item.y_pos + item.width_m/2,
                    f"{item.consignment}\n{item.mass_kg/1000:.1f}t",
                    ha='center', va='center', fontsize=8, fontweight='bold')
        
        # Add articulation gap label
        ax.annotate('Articulation Gap', xy=(trailer.front["length_m"] + 0.25, trailer.front["width_m"]/2),
                   xytext=(trailer.front["length_m"] + 0.25, trailer.front["width_m"]/2 + 0.3),
                   fontsize=8, ha='center')
        
        total_length = trailer.front["length_m"] + trailer.articulation_gap_m + trailer.rear["length_m"]
        ax.set_xlim(-0.5, total_length + 0.5)
        
    else:
        # Standard single trailer
        trailer_rect = patches.Rectangle(
            (0, 0), trailer.length_m, trailer.width_m,
            linewidth=2, edgecolor='black', facecolor='lightgray', alpha=0.3
        )
        ax.add_patch(trailer_rect)
        
        colors = plt.cm.Set3(range(len(trailer.items)))
        for item, color in zip(trailer.items, colors):
            rect = patches.Rectangle(
                (item.x_pos, item.y_pos), item.length_m, item.width_m,
                linewidth=2, edgecolor='blue', facecolor=color, alpha=0.7
            )
            ax.add_patch(rect)
            ax.text(item.x_pos + item.length_m/2, item.y_pos + item.width_m/2,
                    f"{item.consignment}\n{item.mass_kg/1000:.1f}t",
                    ha='center', va='center', fontsize=8, fontweight='bold')
        
        ax.set_xlim(-0.5, trailer.length_m + 0.5)
    
    # Common formatting
    ax.set_ylim(-0.2, max(trailer.width_m, 2.5) + 0.2)
    ax.set_xlabel('Length (meters)', fontsize=12)
    ax.set_ylabel('Width (meters)', fontsize=12)
    
    # Add load info
    if hasattr(trailer, 'calculate_axle_loads'):
        front, rear, cog = trailer.calculate_axle_loads()
    else:
        front, rear = 0, 0
    
    total_mass = trailer.total_mass_kg if hasattr(trailer, 'total_mass_kg') else sum(i.mass_kg for i in trailer.items)
    is_safe = trailer.is_safe()[0] if hasattr(trailer, 'is_safe') else True
    
    info_text = f"Trailer: {trailer.name} ({trailer.type_name})\n"
    info_text += f"Total: {total_mass/1000:.1f}t | "
    info_text += f"Front: {front/1000:.1f}t | Rear: {rear/1000:.1f}t\n"
    info_text += f"Status: {'SAFE' if is_safe else 'OVERLOADED'}"
    
    ax.set_title(info_text, fontsize=10, color='green' if is_safe else 'red')
    ax.grid(True, alpha=0.3)
    
    if parent_frame:
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        canvas = FigureCanvasTkAgg(fig, master=parent_frame)
        canvas.draw()
        return canvas.get_tk_widget()
    return fig