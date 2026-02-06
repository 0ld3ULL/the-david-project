"""
Chart Generator - Creates visual charts for David's tweets.

Generates clean, dark-themed charts that match David's aesthetic.
"""

import io
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Ensure output directory exists
Path("data/charts").mkdir(parents=True, exist_ok=True)


def generate_debasement_chart(
    m2_data: dict,
    output_path: Optional[str] = None,
) -> str:
    """
    Generate a chart showing M2 money supply and purchasing power loss.

    Args:
        m2_data: Dict with latest_value, year_change, year_change_pct
        output_path: Where to save the image (default: data/charts/debasement_YYYYMMDD.png)

    Returns:
        Path to generated image
    """
    try:
        import matplotlib.pyplot as plt
        import matplotlib.ticker as ticker
    except ImportError:
        logger.error("matplotlib not installed. Run: pip install matplotlib")
        return None

    # Extract data
    current_value = m2_data.get("latest_value", 0)  # In billions
    year_change = m2_data.get("year_change", 0)
    year_pct = m2_data.get("year_change_pct", 0)
    latest_date = m2_data.get("latest_date", datetime.now().strftime("%Y-%m-%d"))

    # Calculate values for visualization
    year_ago_value = current_value - year_change if year_change else current_value * 0.95

    # Calculate purchasing power loss on $100k
    loss_pct = year_pct
    savings = 100000
    effective_value = savings * (1 - loss_pct / 100)
    loss_amount = savings - effective_value

    # Dark theme setup
    plt.style.use('dark_background')
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    fig.patch.set_facecolor('#1a1a2e')

    # Chart 1: M2 Money Supply Bar Chart
    ax1.set_facecolor('#1a1a2e')
    bars = ax1.bar(
        ['12 Months Ago', 'Today'],
        [year_ago_value, current_value],
        color=['#4a5568', '#e53e3e'],
        width=0.6,
        edgecolor='white',
        linewidth=0.5
    )

    # Add value labels on bars
    for bar, val in zip(bars, [year_ago_value, current_value]):
        height = bar.get_height()
        ax1.annotate(
            f'${val:,.0f}B',
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 5),
            textcoords="offset points",
            ha='center', va='bottom',
            fontsize=14,
            fontweight='bold',
            color='white'
        )

    # Add change arrow and percentage
    ax1.annotate(
        f'+{year_pct:.1f}%',
        xy=(0.5, (year_ago_value + current_value) / 2),
        fontsize=18,
        fontweight='bold',
        color='#e53e3e',
        ha='center'
    )

    ax1.set_ylabel('Billions USD', fontsize=12, color='#a0aec0')
    ax1.set_title('M2 Money Supply', fontsize=16, fontweight='bold', color='white', pad=15)
    ax1.tick_params(colors='#a0aec0')
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    ax1.spines['left'].set_color('#4a5568')
    ax1.spines['bottom'].set_color('#4a5568')

    # Set y-axis to start from a reasonable base (not zero) for better visualization
    ax1.set_ylim(year_ago_value * 0.95, current_value * 1.08)
    ax1.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: f'${x/1000:.1f}T'))

    # Chart 2: Purchasing Power Loss
    ax2.set_facecolor('#1a1a2e')

    # Stacked bar showing what you kept vs lost
    kept = effective_value
    lost = loss_amount

    bar_kept = ax2.bar(['Your $100k'], [kept], color='#48bb78', width=0.5, label='Remaining Value')
    bar_lost = ax2.bar(['Your $100k'], [lost], bottom=[kept], color='#e53e3e', width=0.5, label='Lost to Printing')

    # Add labels
    ax2.annotate(
        f'${kept:,.0f}',
        xy=(0, kept / 2),
        ha='center', va='center',
        fontsize=14,
        fontweight='bold',
        color='white'
    )
    ax2.annotate(
        f'-${lost:,.0f}',
        xy=(0, kept + lost / 2),
        ha='center', va='center',
        fontsize=14,
        fontweight='bold',
        color='white'
    )

    ax2.set_ylabel('USD', fontsize=12, color='#a0aec0')
    ax2.set_title('Your Savings (12 Months)', fontsize=16, fontweight='bold', color='white', pad=15)
    ax2.tick_params(colors='#a0aec0')
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)
    ax2.spines['left'].set_color('#4a5568')
    ax2.spines['bottom'].set_color('#4a5568')
    ax2.set_ylim(0, 110000)
    ax2.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: f'${x/1000:.0f}k'))
    ax2.legend(loc='upper right', facecolor='#1a1a2e', edgecolor='#4a5568')

    # Add source and branding
    fig.text(
        0.5, 0.02,
        f'Source: Federal Reserve (FRED) | Data as of {latest_date} | flipt.ai',
        ha='center',
        fontsize=10,
        color='#718096'
    )

    plt.tight_layout(rect=[0, 0.05, 1, 1])

    # Save
    if not output_path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"data/charts/debasement_{timestamp}.png"

    plt.savefig(output_path, dpi=150, facecolor='#1a1a2e', edgecolor='none', bbox_inches='tight')
    plt.close()

    logger.info(f"Generated debasement chart: {output_path}")
    return output_path


def generate_simple_stat_image(
    main_stat: str,
    subtitle: str,
    footer: str = "flipt.ai",
    output_path: Optional[str] = None,
) -> str:
    """
    Generate a simple stat card image.

    Good for single-stat tweets like "$4,605 lost"
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return None

    fig, ax = plt.subplots(figsize=(8, 4.5))
    fig.patch.set_facecolor('#1a1a2e')
    ax.set_facecolor('#1a1a2e')

    # Remove axes
    ax.axis('off')

    # Main stat (big number)
    ax.text(
        0.5, 0.6,
        main_stat,
        ha='center', va='center',
        fontsize=48,
        fontweight='bold',
        color='#e53e3e'
    )

    # Subtitle
    ax.text(
        0.5, 0.35,
        subtitle,
        ha='center', va='center',
        fontsize=16,
        color='#a0aec0',
        wrap=True
    )

    # Footer/branding
    ax.text(
        0.5, 0.08,
        footer,
        ha='center', va='center',
        fontsize=12,
        color='#718096'
    )

    if not output_path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"data/charts/stat_{timestamp}.png"

    plt.savefig(output_path, dpi=150, facecolor='#1a1a2e', bbox_inches='tight')
    plt.close()

    return output_path
