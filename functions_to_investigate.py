import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

# --- GLOBAL CONFIGURATION ---
# 'battery' is added to the order. It will appear on top of the stack.
DESIRED_ORDER = ["wind_combined", "CCGT", "solar", "battery"]
COLORS = {
    "wind_combined": "#235ebc", 
    "solar": "#f39c12", 
    "CCGT": "#95a5a6", 
    "battery": "#8e44ad"  # Purple for battery
}

# --- 1. PLOT GENERATION MIX (Universal: Gen + Storage) ---
def plot_generation_mix(n, start_date, end_date):
    """
    Plots stacked generation. Storage is shown as positive when discharging 
    and negative (below zero) when charging.
    """
    # Extract Generators
    p_gen = n.generators_t.p.loc[start_date:end_date]
    
    # Extract Storage Units (Discharging is +, Charging is -)
    if not n.storage_units.empty:
        p_store = n.storage_units_t.p.loc[start_date:end_date]
        p_store.columns = n.storage_units.carrier
        # Combine and reorder based on DESIRED_ORDER
        df = pd.concat([p_gen, p_store], axis=1)
        cols = [c for c in DESIRED_ORDER if c in df.columns]
        df = df[cols]
    else:
        df = p_gen[[c for c in DESIRED_ORDER if c in p_gen.columns]]
    
    load = n.loads_t.p_set.sum(axis=1).loc[start_date:end_date]
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Area plot handles negative values automatically (charging goes below 0)
    df.plot.area(
        ax=ax, 
        stacked=True, 
        color=[COLORS.get(c, '#333') for c in df.columns], 
        alpha=0.8
    )
    
    load.plot(ax=ax, color='black', linewidth=2, label='Demand', linestyle='--')
    
    ax.axhline(0, color='black', lw=1) # Zero line for charging/discharging
    ax.set_title(f"Generation Mix & Storage ({start_date} to {end_date})", fontsize=15)
    ax.set_ylabel("Power [MW]", fontsize=12)
    ax.legend(loc='upper left', bbox_to_anchor=(1, 1))
    ax.grid(True, axis='y', linestyle='--', alpha=0.5)
    
    plt.tight_layout()
    plt.show()

# --- 2. PLOT PRICES & SCARCITY ---
def plot_prices_and_scarcity(n, start_date, end_date):
    """
    Plots Market Price and Scarcity Component (Price - Marginal Cost).
    """
    price = n.buses_t.marginal_price.loc[start_date:end_date, "Denmark"]
    
    scarcity = pd.DataFrame(index=price.index)
    # Check both Generators and Storage Units for scarcity rents
    for carrier in DESIRED_ORDER:
        if carrier in n.generators.carrier.values:
            gen_name = n.generators[n.generators.carrier == carrier].index[0]
            mc = n.generators.loc[gen_name, "marginal_cost"]
            scarcity[carrier] = (price - mc).clip(lower=0)
        elif not n.storage_units.empty and carrier in n.storage_units.carrier.values:
            store_name = n.storage_units[n.storage_units.carrier == carrier].index[0]
            mc = n.storage_units.loc[store_name, "marginal_cost"]
            scarcity[carrier] = (price - mc).clip(lower=0)
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    
    price.plot(ax=ax1, color='#e74c3c', linewidth=1.5, label='Market Price (LMP)')
    ax1.set_title(f"Market Prices ({start_date} to {end_date})", fontsize=14)
    ax1.set_ylabel("Price [$/MWh]")
    ax1.grid(True, alpha=0.3)
    
    scarcity.plot(ax=ax2, color=[COLORS.get(c) for c in scarcity.columns], linewidth=1.5)
    ax2.set_title("Scarcity Signal (Price - Marginal Cost)", fontsize=14)
    ax2.set_ylabel("Scarcity [$/MWh]")
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc='upper left', bbox_to_anchor=(1, 1))
    
    plt.tight_layout()
    plt.show()

# --- 3. PRICE DURATION CURVE ---
def plot_price_duration_curve(n, start_date, end_date):
    prices = n.buses_t.marginal_price["Denmark"].loc[start_date:end_date]
    prices_sorted = prices.sort_values(ascending=False).values
    
    plt.figure(figsize=(8, 5))
    plt.plot(np.arange(len(prices_sorted)), prices_sorted, color='crimson', linewidth=2)
    plt.title(f"Price Duration Curve ({start_date} to {end_date})")
    plt.ylabel("Price [$/MWh]")
    plt.xlabel("Hours")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()

# --- 4. ENERGY PRODUCTION & STORAGE DISCHARGE ---
def plot_energy_production(n, start_date, end_date):
    """
    Plots total energy production by technology and storage discharge.
    Labels are horizontal and values are displayed on top of each bar.
    """
    # 1. Calculate production (Generators + Storage Discharge)
    prod_gen = (n.generators_t.p.loc[start_date:end_date].sum() / 1e6)
    
    if not n.storage_units.empty:
        # Only consider discharging (positive power)
        prod_store = (n.storage_units_t.p.loc[start_date:end_date].clip(lower=0).sum() / 1e6)
        prod_store.index = n.storage_units.carrier
        # Combine and sum by carrier
        production = pd.concat([prod_gen, prod_store]).groupby(level=0).sum()
    else:
        production = prod_gen
    
    # Reindex based on DESIRED_ORDER and fill missing values with 0
    production = production.reindex([c for c in DESIRED_ORDER if c in production.index]).fillna(0)
    
    # 2. Plotting
    plt.figure(figsize=(10, 6))
    
    # Create the plot and get the 'ax' object
    ax = production.plot(
        kind='bar', 
        color=[COLORS.get(i, '#333') for i in production.index], 
        alpha=0.8,
        edgecolor='black',
        linewidth=0.5
    )
    
    # Set titles and labels
    plt.title(f"Total Energy Production/Discharge\n({start_date} to {end_date})", fontsize=14, pad=15)
    plt.ylabel("Energy [TWh]", fontsize=12)
    plt.xlabel("Technology", fontsize=12)
    
    # FORCE horizontal labels
    plt.xticks(rotation=0)
    
    # 3. ADD NUMBERS ON TOP OF BARS
    # We iterate through the 'patches' (the bar rectangles)
    for p in ax.patches:
        height = p.get_height()
        if height > 0: # Only label bars with values
            ax.annotate(f"{height:.2f}", 
                        (p.get_x() + p.get_width() / 2., height), 
                        ha='center', va='center', 
                        xytext=(0, 10), 
                        textcoords='offset points',
                        fontweight='bold',
                        fontsize=11)

    # Styling
    plt.grid(axis='y', linestyle='--', alpha=0.3)
    ax.set_axisbelow(True) # Ensure grid is behind bars
    
    # Extend y-axis slightly to fit labels on top of the tallest bar
    plt.ylim(0, production.max() * 1.15)
    
    plt.tight_layout()
    plt.show()
    # --- 5. ENERGY CURTAILMENT ---
def plot_curtailment(n, start_date, end_date):
    """
    Plots curtailment per technology and total.
    Labels are horizontal and values are displayed on top of each bar.
    """
    potential = n.generators_t.p_max_pu.loc[start_date:end_date].multiply(n.generators.p_nom_opt)
    actual = n.generators_t.p.loc[start_date:end_date]
    
    curtailment = ((potential - actual).sum() / 1e6).reindex([c for c in DESIRED_ORDER if c != "battery"])
    curtailment = curtailment.dropna()
    
    total = curtailment.sum()
    curtailment["Total"] = total
    curtailment = curtailment[curtailment > 0.0001]
    
    if curtailment.empty:
        print("No significant curtailment.")
        return

    plt.figure(figsize=(10, 6))
    colors_list = [COLORS.get(col, "#555555") for col in curtailment.index]
    ax = curtailment.plot(kind='bar', color=colors_list, alpha=0.8, edgecolor='black', linewidth=0.5)
    
    plt.title(f"Energy Curtailment ({start_date} to {end_date})", fontsize=14, pad=15)
    plt.ylabel("Energy [TWh]", fontsize=12)
    plt.xticks(rotation=0)
    
    # Add values on top
    for p in ax.patches:
        height = p.get_height()
        ax.annotate(f"{height:.3f}", (p.get_x() + p.get_width() / 2., height),
                    ha='center', va='center', xytext=(0, 10), 
                    textcoords='offset points', fontweight='bold')

    plt.ylim(0, curtailment.max() * 1.15)
    plt.grid(axis='y', linestyle='--', alpha=0.3)
    plt.tight_layout()
    plt.show()
# --- 6. INSTALLED CAPACITY (Gen + Storage) ---
def plot_installed_capacity(n):
    """
    Plots optimized capacity for generators and storage units.
    Labels are horizontal and values (GW) are displayed on top.
    """
    cap_gen = (n.generators.p_nom_opt / 1e3)
    if not n.storage_units.empty:
        cap_store = (n.storage_units.p_nom_opt / 1e3)
        cap_store.index = n.storage_units.carrier
        capacity = pd.concat([cap_gen, cap_store]).groupby(level=0).sum()
    else:
        capacity = cap_gen
        
    capacity = capacity.reindex([c for c in DESIRED_ORDER if c in capacity.index]).fillna(0)
    
    plt.figure(figsize=(10, 6))
    ax = capacity.plot(kind='bar', color='#27ae60', alpha=0.8, edgecolor='black', linewidth=0.5)
    
    plt.title("Optimized Installed Capacity", fontsize=14, pad=15)
    plt.ylabel("Capacity [GW]", fontsize=12)
    plt.xticks(rotation=0)
    
    for p in ax.patches:
        height = p.get_height()
        ax.annotate(f"{height:.2f}", (p.get_x() + p.get_width() / 2., height),
                    ha='center', va='center', xytext=(0, 10), 
                    textcoords='offset points', fontweight='bold')

    plt.ylim(0, capacity.max() * 1.15)
    plt.grid(axis='y', linestyle='--', alpha=0.3)
    plt.tight_layout()
    plt.show()

# --- 7. SYSTEM COSTS (CAPEX + OPEX: Universal) ---
def plot_system_costs(n, start_date, end_date):
    """
    Plots total system costs (CAPEX scaled + OPEX) including Storage.
    Labels are horizontal and values (Million $) are displayed on top.
    """
    selected_snaps = n.snapshots[n.snapshots.slice_indexer(start_date, end_date)]
    scale_factor = len(selected_snaps) / 8760
    
    # Generators Costs
    capex_gen = (n.generators.p_nom_opt * n.generators.capital_cost * scale_factor)
    opex_gen = (n.generators_t.p.loc[start_date:end_date].sum() * n.generators.marginal_cost)
    costs_gen = (capex_gen + opex_gen).groupby(n.generators.carrier).sum()
    
    # Storage Costs
    if not n.storage_units.empty:
        capex_store = (n.storage_units.p_nom_opt * n.storage_units.capital_cost * scale_factor)
        p_dis = n.storage_units_t.p.loc[start_date:end_date].clip(lower=0)
        opex_store = (p_dis.sum() * n.storage_units.marginal_cost)
        costs_store = (capex_store + opex_store).groupby(n.storage_units.carrier).sum()
        total_costs = pd.concat([costs_gen, costs_store]).groupby(level=0).sum()
    else:
        total_costs = costs_gen

    total_costs = (total_costs / 1e6).reindex([c for c in DESIRED_ORDER if c in total_costs.index]).fillna(0)
    
    plt.figure(figsize=(10, 6))
    ax = total_costs.plot(kind='bar', color='#8e44ad', alpha=0.8, edgecolor='black', linewidth=0.5)
    
    plt.title(f"Total System Costs ({start_date} to {end_date})", fontsize=14, pad=15)
    plt.ylabel("Cost [Million $]", fontsize=12)
    plt.xticks(rotation=0)
    
    for p in ax.patches:
        height = p.get_height()
        ax.annotate(f"{height:.2f}", (p.get_x() + p.get_width() / 2., height),
                    ha='center', va='center', xytext=(0, 10), 
                    textcoords='offset points', fontweight='bold')

    plt.ylim(0, total_costs.max() * 1.15)
    plt.grid(axis='y', linestyle='--', alpha=0.3)
    plt.tight_layout()
    plt.show()