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
    plt.title(f"Total Energy Production/Discharge (if battery)\n({start_date} to {end_date})", fontsize=14, pad=15)
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
def plot_mismatch_analysis(n, start_date, end_date):
    """
    Plots the Potential Mismatch Duration Curve: (Potential RE - Load).
    Positive Area (>0) = Potential Curtailment (Excess RE).
    Negative Area (<0) = Backup Energy Needed (Deficit).
    """
    # 1. Extract Load
    load = n.loads_t.p_set.sum(axis=1).loc[start_date:end_date]
    
    # 2. Calculate POTENTIAL Generation (Availability * Capacity)
    # Using p_max_pu to see what the weather actually offers
    pot_wind = n.generators_t.p_max_pu.loc[start_date:end_date, "wind_combined"] * n.generators.at["wind_combined", "p_nom_opt"]
    pot_solar = n.generators_t.p_max_pu.loc[start_date:end_date, "solar"] * n.generators.at["solar", "p_nom_opt"]
    
    total_pot_re = pot_wind + pot_solar
    
    # 3. Calculate Mismatch: RE - Load
    # Positive values: Surplus (Curtailment)
    # Negative values: Deficit (Backup)
    mismatch = total_pot_re - load
    
    # 4. Sort for Duration Curve (Highest surplus to highest deficit)
    mismatch_sorted = mismatch.sort_values(ascending=False).values
    x_axis = np.arange(len(mismatch_sorted))
    
    # 5. Numerical Calculations (Areas)
    # Surplus (Curtailment) is the positive part
    curtailment_twh = mismatch.clip(lower=0).sum() / 1e6
    # Deficit (Backup) is the absolute value of the negative part
    backup_needed_twh = mismatch.clip(upper=0).abs().sum() / 1e6
    
    # 6. Plotting
    plt.figure(figsize=(10, 6))
    plt.plot(x_axis, mismatch_sorted, color='black', lw=2, label='RE - Load Mismatch')
    
    # Fill Positive Area (Curtailment)
    plt.fill_between(x_axis, 0, mismatch_sorted, 
                     where=(mismatch_sorted > 0), color='#2ecc71', alpha=0.5, label='Potential Curtailment (Excess)')
    
    # Fill Negative Area (Backup Needed)
    plt.fill_between(x_axis, 0, mismatch_sorted, 
                     where=(mismatch_sorted < 0), color='#e74c3c', alpha=0.5, label='Backup Energy Needed (Deficit)')
    
    plt.axhline(0, color='black', linestyle='-', lw=1.5)
    
    # Formatting
    plt.title(f"Mismatch Duration Curve ({start_date} to {end_date})", fontsize=14, pad=15)
    plt.ylabel("Power [MW]", fontsize=12)
    plt.xlabel("Hours (Sorted by Surplus)", fontsize=12)
    plt.grid(alpha=0.3, linestyle='--')
    
    # Add energy info in legend
    plt.legend([
        f'Mismatch Curve',
        f'Curtailment: {curtailment_twh:.2f} TWh',
        f'Backup Energy Needed: {backup_needed_twh:.2f} TWh'
    ], loc='upper right')
    
    plt.tight_layout()
    plt.show()

    print(f"Analysis Results:")
    print(f" - Total Potential Curtailment: {curtailment_twh:.3f} TWh")
    print(f" - Total Backup Energy Needed:  {backup_needed_twh:.3f} TWh")
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
def plot_system_costs(n):
    """
    Plots total ANNUAL system costs (Full CAPEX + Full Year OPEX).
    Use this for the final balance of the investment.
    """
    # 1. CAPEX (Full Annualized Cost)
    capex_gen = (n.generators.p_nom_opt * n.generators.capital_cost)
    
    # 2. OPEX (Summed over all snapshots available in the model, usually 8760h)
    opex_gen = (n.generators_t.p.sum() * n.generators.marginal_cost)
    
    costs_gen = (capex_gen + opex_gen).groupby(n.generators.carrier).sum()
    
    # 3. Storage Costs
    if not n.storage_units.empty:
        capex_store = (n.storage_units.p_nom_opt * n.storage_units.capital_cost)
        # OPEX for storage (discharging energy * marginal cost)
        p_dis = n.storage_units_t.p.clip(lower=0)
        opex_store = (p_dis.sum() * n.storage_units.marginal_cost)
        costs_store = (capex_store + opex_store).groupby(n.storage_units.carrier).sum()
        total_costs = pd.concat([costs_gen, costs_store]).groupby(level=0).sum()
    else:
        total_costs = costs_gen

    # Conversion to Million $ and reindex
    total_costs = (total_costs / 1e6).reindex([c for c in DESIRED_ORDER if c in total_costs.index]).fillna(0)
    
    # Plotting
    plt.figure(figsize=(10, 6))
    ax = total_costs.plot(kind='bar', color='#8e44ad', alpha=0.8, edgecolor='black', linewidth=0.5)
    
    plt.title("Total Annual System Costs (CAPEX + OPEX)", fontsize=14, pad=15)
    plt.ylabel("Million $ / Year", fontsize=12)
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

def calculate_system_metrics(n, start_date, end_date):
    """
    Calculates and prints Average Capacity Factors and total Backup Energy (CCGT).
    """
    # 1. Capacity Factors Calculation
    # Formula: Production / (Capacity * Hours)
    p_gen = n.generators_t.p.loc[start_date:end_date]
    capacity = n.generators.p_nom_opt
    hours = len(p_gen.index)
    
    cf = (p_gen.sum() / (capacity * hours)) * 100 # In percentage
    
    print("-" * 30)
    print(f"METRICS ({start_date} to {end_date})")
    print("-" * 30)
    print("Average Capacity Factors [%]:")
    for gen, value in cf.items():
        print(f"  * {gen:15}: {value:6.2f}%")
    
    # 2. Backup Energy (CCGT Production)
    if "CCGT" in p_gen.columns:
        backup_twh = p_gen["CCGT"].sum() / 1e6
        print(f"\nTotal Backup Energy (CCGT): {backup_twh:.3f} TWh")
    
    # 3. Renewable Share
    total_gen = p_gen.sum().sum()
    re_gen = p_gen[[c for c in p_gen.columns if c != "CCGT"]].sum().sum()
    re_share = (re_gen / total_gen) * 100 if total_gen > 0 else 0
    print(f"Renewable Share:         {re_share:.2f}%")
    print("-" * 30)

def plot_mismatch_duration_curve(n, start_date, end_date):
    """
    Plots the duration curve of the POTENTIAL energy mismatch.
    Mismatch = Load - (Potential Wind + Potential Solar).
    This shows how much RE is available before curtailment.
    """
    # 1. Extract Load
    load = n.loads_t.p_set.sum(axis=1).loc[start_date:end_date]
    
    # 2. Calculate POTENTIAL Generation (Capacity * Availability Profile)
    # This represents what the wind/solar WOULD have produced if never curtailed
    potential_wind = n.generators_t.p_max_pu.loc[start_date:end_date, "wind_combined"] * n.generators.at["wind_combined", "p_nom_opt"]
    potential_solar = n.generators_t.p_max_pu.loc[start_date:end_date, "solar"] * n.generators.at["solar", "p_nom_opt"]
    
    total_potential_re = potential_wind + potential_solar
    
    # 3. Calculate Potential Mismatch
    # Positive = Deficit (Need Gas/Storage)
    # Negative = Excess (Available for Storage or lost as Curtailment)
    mismatch = load - total_potential_re
    
    # 4. Sort values for the Duration Curve
    mismatch_sorted = mismatch.sort_values(ascending=False).values
    
    # 5. Plotting
    plt.figure(figsize=(10, 6))
    plt.plot(np.arange(len(mismatch_sorted)), mismatch_sorted, color='black', lw=2, label='Potential Net Load')
    
    # Fill areas
    plt.fill_between(np.arange(len(mismatch_sorted)), 0, mismatch_sorted, 
                     where=(mismatch_sorted > 0), color='#e74c3c', alpha=0.4, label='Energy Deficit')
    plt.fill_between(np.arange(len(mismatch_sorted)), 0, mismatch_sorted, 
                     where=(mismatch_sorted < 0), color='#2ecc71', alpha=0.4, label='Energy Surplus (Potential RE)')
    
    plt.axhline(0, color='black', linestyle='-', lw=1)
    plt.title(f"Potential Mismatch Duration Curve ({start_date} to {end_date})", fontsize=14)
    plt.xlabel("Hours (Sorted)", fontsize=12)
    plt.ylabel("Power Mismatch [MW]", fontsize=12)
    plt.grid(alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.show()

    # Optional: Print the total potential surplus
    surplus_twh = mismatch.clip(upper=0).abs().sum() / 1e6
    print(f"Total Potential Surplus Energy: {surplus_twh:.3f} TWh")