# # app/analysis/plots.py
# import matplotlib.pyplot as plt
# import seaborn as sns
# from utils.fig_to_base64 import fig_to_base64

# sns.set_style("whitegrid")

# def line_plot_years(x, ys, labels, title, xlabel="Year", ylabel="", figsize=(8,3)):
#     fig, ax = plt.subplots(figsize=figsize)
#     for y, lab in zip(ys, labels):
#         ax.plot(x, y, marker='o', label=lab)
#     ax.set_title(title)
#     ax.set_xlabel(xlabel)
#     ax.set_ylabel(ylabel)
#     ax.legend()
#     return fig_to_base64(fig)

# def barh_plot(y, x, title, xlabel="", figsize=(8,3)):
#     fig, ax = plt.subplots(figsize=figsize)
#     ax.barh(y, x)
#     ax.invert_yaxis()
#     ax.set_title(title)
#     ax.set_xlabel(xlabel)
#     return fig_to_base64(fig)
import matplotlib.pyplot as plt
import seaborn as sns
from utils.fig_to_base64 import fig_to_base64

# --- GLOBAL STUNNING THEME SETUP ---
# Use a clean, professional theme with enhanced typography and axis styling.
sns.set_theme(
    style="whitegrid",
    rc={
        "figure.figsize": (10, 5),
        "axes.edgecolor": "#A0A0A0",
        "axes.labelcolor": "#333333",
        "xtick.color": "#333333",
        "ytick.color": "#333333",
        "font.family": "sans-serif",
        "grid.linestyle": "--",
        "grid.color": "#E5E5E5"
    }
)

# --- CUSTOM PALETTES ---
# Defining sequential and single colors for consistency and impact
LINE_PALETTE = sns.color_palette("viridis", 6)
BAR_COLOR = "#009688"  # A professional teal/green for bars

def line_plot_years(x, ys, labels, title, xlabel="Year", ylabel="", figsize=(10, 5)):
    """
    Generates a stunning line plot showing trends over time for multiple series (e.g., states).
    """
    fig, ax = plt.subplots(figsize=figsize)
    
    # 1. Use the custom palette for distinct lines
    for i, (y, lab) in enumerate(zip(ys, labels)):
        ax.plot(
            x, y, 
            marker='o', 
            label=lab, 
            color=LINE_PALETTE[i % len(LINE_PALETTE)],
            linewidth=2.5,  # Thicker lines for better visual weight
            markersize=6,   # Larger markers
            alpha=0.8
        )
        
    # 2. Enhanced Title and Labels
    ax.set_title(title, fontsize=16, weight='bold', pad=15, color='#34495e')
    ax.set_xlabel(xlabel, fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    
    # 3. Clean Legend and Layout
    ax.legend(frameon=False, loc='upper left', bbox_to_anchor=(1, 1), title='Series')
    sns.despine(left=True, bottom=True) # Remove unnecessary outside borders
    plt.tight_layout()
    
    return fig_to_base64(fig)

def barh_plot(y, x, title, xlabel="Deviation", figsize=(9, 4)):
    """
    Generates a gorgeous horizontal bar plot (ideal for ranking 'worst' stations).
    """
    fig, ax = plt.subplots(figsize=figsize)
    
    # 1. Use Seaborn barplot for aesthetic default styling
    sns.barplot(
        x=x, 
        y=y, 
        ax=ax, 
        color=BAR_COLOR, # Single impactful color
        edgecolor=".2", # Darker edge for definition
        linewidth=1
    )
    
    ax.invert_yaxis()
    
    # 2. Enhanced Title and Labels
    ax.set_title(title, fontsize=16, weight='bold', pad=15, color='#34495e')
    ax.set_xlabel(xlabel, fontsize=12)
    ax.set_ylabel("") # Remove y-axis label since the ticks are the station names
    
    # 3. Clean Layout (Only keep the grid that helps compare values)
    ax.xaxis.grid(True, linestyle='--', alpha=0.6)
    ax.yaxis.grid(False) # Remove horizontal grid lines for cleaner presentation
    sns.despine(left=True, bottom=True)
    
    plt.tight_layout()
    
    return fig_to_base64(fig)