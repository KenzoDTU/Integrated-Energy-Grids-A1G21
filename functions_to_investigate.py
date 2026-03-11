import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

# --- GLOBAL CONFIGURATION ---
# We place 'solar' last so it appears at the top of stacked charts
DESIRED_ORDER = ["wind_combined", "CCGT", "solar"]
COLORS = {"wind_combined": "#235ebc", "solar": "#f39c12", "CCGT": "#95a5a6"}

# --- 1. PLOT GENERATION MIX (Stacked Time Series) ---
def plot_generation_mix(n, start_date, end_date):
    """
    Plots the stacked generation by technology compared to the total demand 
    for a specific time window. Solar is placed on top due to its small contribution.
    """
    # Extracting and reordering generation data for the selected period
    p_gen = n.generators_t.p.loc[start_date:end_date][DESIRED_ORDER]
    
    # Extracting and summing the demand for the selected period
    load = n.loads_t.p_set.sum(axis=1).loc[start_date:end_date]
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Plotting stacked areas for generation
    p_gen.plot.area(
        ax=ax, 
        stacked=True, 
        color=[COLORS.get(c, '#333') for c in p_gen.columns], 
        alpha=0.8
    )
    
    # Plotting the total demand as a dashed black line for comparison
    load.plot(ax=ax, color='black', linewidth=2, label='Demand', linestyle='--')
    
    # Formatting titles and labels
    ax.set_title(f"Generation Mix vs Demand ({start_date} to {end_date})", fontsize=15)
    ax.set_ylabel("Power [MW]", fontsize=12)
    ax.set_xlabel("Time", fontsize=12)
    
    # Moving the legend outside the plot area for better visibility
    ax.legend(loc='upper left', bbox_to_anchor=(1, 1))
    ax.grid(True, linestyle='--', alpha=0.5)
    
    plt.tight_layout()
    plt.show()

# --- 2. PLOT PRICES & SCARCITY ---
def plot_prices_and_scarcity(n, start_date, end_date):
    """
    Plots the Market Price and the Scarcity Component for each technology.
    """
    # 1. Extract the Market Price for the selected period
    price = n.buses_t.marginal_price.loc[start_date:end_date, "Denmark"]
    
    # 2. Calculate the Scarcity Component for each technology in desired order
    scarcity = pd.DataFrame(index=price.index)
    for gen in DESIRED_ORDER:
        if gen in n.generators.index:
            mc = n.generators.loc[gen, "marginal_cost"]
            scarcity[gen] = (price - mc).clip(lower=0)
    
    # 3. Create the visualization with two subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    
    # Top Plot: Market Price (LMP)
    price.plot(ax=ax1, color='#e74c3c', linewidth=1.5, label='Market Price (LMP)')
    ax1.set_title(f"Market Prices ({start_date} to {end_date})", fontsize=14)
    ax1.set_ylabel("Price [$/MWh]")
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    # Bottom Plot: Scarcity Components per Technology
    scarcity.plot(ax=ax2, color=[COLORS.get(c) for c in scarcity.columns], linewidth=1.5)
    
    ax2.set_title("Scarcity Signal per Technology (Price - Marginal Cost)", fontsize=14)
    ax2.set_ylabel("Scarcity [$/MWh]")
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc='upper left', bbox_to_anchor=(1, 1))
    
    plt.tight_layout()
    plt.show()

# --- 3. PRICE DURATION CURVE ---
def plot_price_duration_curve(n, start_date, end_date):
    """
    Plots the price duration curve for a specific time window.
    """
    prices = n.buses_t.marginal_price["Denmark"].loc[start_date:end_date]
    prices_sorted = prices.sort_values(ascending=False).values
    
    plt.figure(figsize=(8, 5))
    plt.plot(np.arange(len(prices_sorted)), prices_sorted, color='crimson', linewidth=2)
    
    plt.title(f"Price Duration Curve ({start_date} to {end_date})", fontsize=14)
    plt.ylabel("Price [$/MWh]", fontsize=12)
    plt.xlabel("Hours", fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()

# --- 4. STACKED DURATION CURVE (Contribution by Technology) ---
def plot_stacked_duration_curve(n, start_date, end_date):
    """
    Plots the stacked generation duration curve ordered by demand level.
    """
    load = n.loads_t.p_set["dnk_demand"].loc[start_date:end_date]
    # Reorder generators here as well
    gen = n.generators_t.p.loc[start_date:end_date][DESIRED_ORDER]
    
    order = load.sort_values(ascending=False).index
    gen_sorted = gen.loc[order]
    load_sorted = load.loc[order].values
    
    plt.figure(figsize=(10, 6))
    plt.stackplot(np.arange(len(gen_sorted)), 
                  [gen_sorted[c] for c in gen_sorted.columns], 
                  labels=gen_sorted.columns, 
                  colors=[COLORS.get(c, '#333') for c in gen_sorted.columns], 
                  alpha=0.8)
    
    plt.plot(np.arange(len(load_sorted)), load_sorted, color='black', label='Demand', linewidth=2)
    
    plt.title(f"Stacked Generation Duration Curve ({start_date} to {end_date})", fontsize=14)
    plt.ylabel("Power [MW]", fontsize=12)
    plt.xlabel("Hours (Sorted by Demand Level)", fontsize=12)
    plt.legend(loc='upper right')
    plt.grid(alpha=0.2)
    plt.tight_layout()
    plt.show()

# --- 5. ENERGY PRODUCTION & BACKUP ENERGY ---
def plot_energy_production(n, start_date, end_date):
    """
    Plots total energy production in TWh using the desired order.
    """
    production = (n.generators_t.p.loc[start_date:end_date].sum() / 1e6).reindex(DESIRED_ORDER)
    
    plt.figure(figsize=(8, 5))
    production.plot(kind='bar', color=[COLORS.get(i, '#333') for i in production.index])
    
    plt.title(f"Total Energy Production ({start_date} to {end_date})", fontsize=14)
    plt.ylabel("Energy [TWh]", fontsize=12)
    plt.xticks(rotation=0)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    for i, v in enumerate(production):
        plt.text(i, v + (production.max()*0.02), f"{v:.2f}", ha='center', fontweight='bold')
        
    plt.tight_layout()
    plt.show()

# --- 6. ENERGY CURTAILMENT ---
def plot_curtailment(n, start_date, end_date):
    """
    Plots curtailment per technology and the total curtailment 
    for the specified period in TWh.
    """
    # 1. Calculate Potential vs Actual generation
    # Potential = theoretical max (p_max_pu * p_nom_opt)
    potential = n.generators_t.p_max_pu.loc[start_date:end_date].multiply(n.generators.p_nom_opt)
    actual = n.generators_t.p.loc[start_date:end_date]
    
    # 2. Calculate curtailment per technology in TWh
    curtailment = ((potential - actual).sum() / 1e6).reindex(DESIRED_ORDER)
    curtailment = curtailment.dropna()
    
    # 3. Add the Total Curtailment as a new entry
    total_curtailment = curtailment.sum()
    curtailment["Total"] = total_curtailment
    
    # Filter out insignificant values (less than 1 GWh) to keep the plot clean
    curtailment = curtailment[curtailment > 0.001]
    
    if curtailment.empty or total_curtailment < 0.001:
        print(f"No significant curtailment detected from {start_date} to {end_date}.")
        return

    # 4. Plotting
    plt.figure(figsize=(8, 6))
    
    # Define colors: standard technology colors + dark grey for the Total
    bar_colors = [COLORS.get(col, "#555555") for col in curtailment.index]
    
    curtailment.plot(kind='bar', color=bar_colors, alpha=0.85)
    
    plt.title(f"Energy Curtailment ({start_date} to {end_date})", fontsize=14)
    plt.ylabel("Energy [TWh]", fontsize=12)
    plt.xlabel("Technology", fontsize=12)
    plt.xticks(rotation=0)
    plt.grid(axis='y', linestyle='--', alpha=0.6)
    
    # Add data labels on top of bars for precision
    for i, v in enumerate(curtailment):
        plt.text(i, v + (curtailment.max() * 0.02), f"{v:.3f}", ha='center', fontweight='bold')
    
    plt.tight_layout()
    plt.show()

# --- 7. INSTALLED CAPACITY ---
def plot_installed_capacity(n):
    """
    Plots optimized capacity in GW using the desired order.
    """
    capacity = (n.generators.p_nom_opt.reindex(DESIRED_ORDER) / 1e3)
    
    plt.figure(figsize=(8, 5))
    capacity.plot(kind='bar', color='#27ae60')
    plt.title("Optimized Installed Capacity (Total Scenario)", fontsize=14)
    ax = plt.gca()
    ax.set_ylabel("Capacity [GW]", fontsize=12)
    plt.xticks(rotation=0)
    plt.grid(axis='y', alpha=0.3)
    
    for i, v in enumerate(capacity):
        plt.text(i, v + (capacity.max()*0.02), f"{v:.2f}", ha='center')
        
    plt.tight_layout()
    plt.show()

# --- 8. SYSTEM COSTS (CAPEX & OPEX) ---
def plot_system_costs(n, start_date, end_date):
    """
    Plots total system costs (CAPEX + OPEX) in Million $ using the desired order.
    CAPEX is scaled based on the number of hours in the selected window.
    """
    # 1. Correct way to count hours in the selected window
    # We slice the index directly using start_date and end_date
    selected_snapshots = n.snapshots[n.snapshots.slice_indexer(start_date, end_date)]
    window_hours = len(selected_snapshots)
    
    total_hours = 8760 # Standard year
    scale_factor = window_hours / total_hours
    
    # 2. Calculate OPEX for the period
    # Generation [MW] * Marginal Cost [$/MWh] = $
    p_gen = n.generators_t.p.loc[start_date:end_date]
    opex = (p_gen.sum() * n.generators.marginal_cost).reindex(DESIRED_ORDER)
    
    # 3. Calculate CAPEX scaled for the period
    # (Capacity * Capital Cost) * (hours_in_window / 8760)
    capex = (n.generators.p_nom_opt * n.generators.capital_cost * scale_factor).reindex(DESIRED_ORDER)
    
    # Total costs in Million $
    total_costs = (capex + opex) / 1e6
    
    # 4. Plotting
    plt.figure(figsize=(8, 5))
    total_costs.plot(kind='bar', color='#8e44ad', alpha=0.8)
    
    plt.title(f"Total System Costs ({start_date} to {end_date})", fontsize=14)
    plt.ylabel("Cost [Million $]", fontsize=12)
    plt.xlabel("Technology", fontsize=12)
    plt.xticks(rotation=0)
    plt.grid(axis='y', linestyle='--', alpha=0.3)
    
    # Add data labels
    for i, v in enumerate(total_costs):
        plt.text(i, v + (total_costs.max()*0.02), f"{v:.2f}", ha='center', fontweight='bold')
        
    plt.tight_layout()
    plt.show()