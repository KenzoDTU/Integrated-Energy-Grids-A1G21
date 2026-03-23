import matplotlib.pyplot as plt
import pandas as pd
import numpy as np


# --- STEP A ---
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
    plt.ylim(0, 200)
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

# --- PLOT ANNUAL ELECTRICITY MIX (Pie Chart) ---
def plot_annual_mix(n):
    """
    Plots a pie chart of the annual electricity mix.
    """
    annual_prod = n.generators_t.p.sum()
    
    # Reorder based on DESIRED_ORDER
    ordered = [c for c in DESIRED_ORDER if c in annual_prod.index]
    annual_prod = annual_prod[ordered]
    
    fig, ax = plt.subplots(figsize=(7, 7))
    ax.pie(
        annual_prod.values, 
        labels=annual_prod.index, 
        colors=[COLORS.get(c, '#333') for c in annual_prod.index], 
        autopct='%1.1f%%', 
        startangle=90, 
        textprops={'fontsize': 13}
    )
    ax.set_title("Annual Electricity Mix", fontsize=15)
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










# STEP B: INTERANNUAL VARIABILITY FUNCTIONS

# --- 1. Capacities per year + Box plot ---
def plot_capacity_by_year(results):
    """
    Bar chart of capacities per year (bottom) + box plot (top).
    """
    years = sorted(results.keys())
    techs = [t for t in DESIRED_ORDER if t in results[years[0]]["p_nom_opt"].index]
    year_colors = {2015: '#2d4a7a', 2016: '#5b8c85', 2017: '#c17f59', 2018: '#8b5e83'}
    
    fig, (ax_box, ax_bar) = plt.subplots(2, 1, figsize=(10, 8),
                                          gridspec_kw={'height_ratios': [1, 2]}, sharex=False)
    
    x = np.arange(len(techs))
    width = 0.18
    
    # --- Bottom: bar chart per year ---
    for i, year in enumerate(years):
        vals = [results[year]["p_nom_opt"][tech] / 1e3 for tech in techs]
        bars = ax_bar.bar(x + i * width, vals, width, label=str(year),
                          color=year_colors[year], edgecolor='white')
        for bar, val in zip(bars, vals):
            ax_bar.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.03,
                        f'{val:.1f}', ha='center', va='bottom', fontsize=8)
    
    ax_bar.set_ylabel("Optimal Capacity [GW]", fontsize=12)
    ax_bar.set_xticks(x + width * 1.5)
    ax_bar.set_xticklabels(techs, fontsize=11)
    ax_bar.legend(title="Year", loc='upper right')
    ax_bar.grid(True, axis='y', linestyle='--', alpha=0.4)
    
    # --- Top: box plot ---
    box_data = []
    positions = []
    colors_list = []
    for j, tech in enumerate(techs):
        vals = [results[y]["p_nom_opt"][tech] / 1e3 for y in years]
        box_data.append(vals)
        positions.append(j)
        colors_list.append(COLORS.get(tech, '#333'))
    
    bp = ax_box.boxplot(box_data, positions=positions, widths=0.5, patch_artist=True,
                        showmeans=True, 
                        meanprops=dict(marker='D', markerfacecolor='black', markersize=5),
                        medianprops=dict(color='black', linewidth=1.5))
    for patch, color in zip(bp['boxes'], colors_list):
        patch.set_facecolor(color)
        patch.set_alpha(0.35)
    
    # Annotate mean ± std
    for j, tech in enumerate(techs):
        vals = [results[y]["p_nom_opt"][tech] / 1e3 for y in years]
        mean = np.mean(vals)
        std = np.std(vals)
        ax_box.text(positions[j] + 0.35, mean, f'{mean:.1f} ± {std:.2f}',
                    ha='left', va='center', fontsize=9, fontstyle='italic')
    
    ax_box.set_xticks(positions)
    ax_box.set_xticklabels(techs, fontsize=11)
    ax_box.set_ylabel("GW", fontsize=10)
    ax_box.set_title("Optimal Installed Capacity by Weather Year", fontsize=15)
    ax_box.grid(True, axis='y', linestyle='--', alpha=0.4)
    
    plt.tight_layout()
    plt.show()


# --- 2. Production per year + Box plot ---
def plot_production_by_year(results):
    """
    Bar chart of production per year (bottom) + box plot (top).
    """
    years = sorted(results.keys())
    techs = [t for t in DESIRED_ORDER if t in results[years[0]]["production_twh"].index]
    year_colors = {2015: '#2d4a7a', 2016: '#5b8c85', 2017: '#c17f59', 2018: '#8b5e83'}
    
    fig, (ax_box, ax_bar) = plt.subplots(2, 1, figsize=(10, 8),
                                          gridspec_kw={'height_ratios': [1, 2]}, sharex=False)
    
    x = np.arange(len(techs))
    width = 0.18
    
    # --- Bottom: bar chart per year ---
    for i, year in enumerate(years):
        vals = [results[year]["production_twh"][tech] for tech in techs]
        bars = ax_bar.bar(x + i * width, vals, width, label=str(year),
                          color=year_colors[year], edgecolor='white')
        for bar, val in zip(bars, vals):
            ax_bar.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                        f'{val:.1f}', ha='center', va='bottom', fontsize=8)
    
    ax_bar.set_ylabel("Annual Production [TWh]", fontsize=12)
    ax_bar.set_xticks(x + width * 1.5)
    ax_bar.set_xticklabels(techs, fontsize=11)
    ax_bar.legend(title="Year", loc='upper right')
    ax_bar.grid(True, axis='y', linestyle='--', alpha=0.4)
    
    # --- Top: box plot ---
    box_data = []
    positions = []
    colors_list = []
    for j, tech in enumerate(techs):
        vals = [results[y]["production_twh"][tech] for y in years]
        box_data.append(vals)
        positions.append(j)
        colors_list.append(COLORS.get(tech, '#333'))
    
    bp = ax_box.boxplot(box_data, positions=positions, widths=0.5, patch_artist=True,
                        showmeans=True,
                        meanprops=dict(marker='D', markerfacecolor='black', markersize=5),
                        medianprops=dict(color='black', linewidth=1.5))
    for patch, color in zip(bp['boxes'], colors_list):
        patch.set_facecolor(color)
        patch.set_alpha(0.35)
    
    # Annotate mean ± std
    for j, tech in enumerate(techs):
        vals = [results[y]["production_twh"][tech] for y in years]
        mean = np.mean(vals)
        std = np.std(vals)
        ax_box.text(positions[j] + 0.35, mean, f'{mean:.1f} ± {std:.1f}',
                    ha='left', va='center', fontsize=9, fontstyle='italic')
    
    ax_box.set_xticks(positions)
    ax_box.set_xticklabels(techs, fontsize=11)
    ax_box.set_ylabel("TWh", fontsize=10)
    ax_box.set_title("Annual Energy Production by Weather Year", fontsize=15)
    ax_box.grid(True, axis='y', linestyle='--', alpha=0.4)
    
    plt.tight_layout()
    plt.show()


# --- 3. BAR CHART: Capacity factors per year ---
def plot_cf_by_year(results):
    """
    Grouped bar chart of average wind and solar capacity factors per year.
    """
    years = sorted(results.keys())
    cf_wind = [results[y]["cf_wind"] * 100 for y in years]
    cf_solar = [results[y]["cf_solar"] * 100 for y in years]
    
    x = np.arange(len(years))
    width = 0.35
    
    fig, ax = plt.subplots(figsize=(8, 6))
    bars1 = ax.bar(x - width/2, cf_wind, width, label="Wind", color="#2ecc71")
    bars2 = ax.bar(x + width/2, cf_solar, width, label="Solar", color="#e74c3c")
    
    for bar, val in zip(bars1, cf_wind):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
                f'{val:.1f}%', ha='center', va='bottom', fontsize=10)
    for bar, val in zip(bars2, cf_solar):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
                f'{val:.1f}%', ha='center', va='bottom', fontsize=10)
    
    ax.set_xlabel("Weather Year", fontsize=12)
    ax.set_ylabel("Average Capacity Factor [%]", fontsize=12)
    ax.set_title("Wind & Solar Capacity Factors by Weather Year", fontsize=15)
    ax.set_xticks(x)
    ax.set_xticklabels(years)
    ax.legend()
    ax.grid(True, axis='y', linestyle='--', alpha=0.5)
    plt.tight_layout()
    plt.show()


# --- 4. DISPATCH: Best vs Worst wind year (winter week) ---
def plot_dispatch_best_worst(results):
    """
    Side-by-side dispatch for a winter week in the best and worst wind years.
    """
    years = sorted(results.keys())
    wind_prod = {y: results[y]["production_twh"]["wind_combined"] for y in years}
    best_year = max(wind_prod, key=wind_prod.get)
    worst_year = min(wind_prod, key=wind_prod.get)
    
    fig, axes = plt.subplots(2, 1, figsize=(14, 10), sharex=False)
    
    for ax, year, label in zip(axes, [best_year, worst_year], ["Best Wind Year", "Worst Wind Year"]):
        n = results[year]["network"]
        start = f"{year}-01-15"
        end = f"{year}-01-22"
        
        p_gen = n.generators_t.p.loc[start:end]
        load = n.loads_t.p_set.sum(axis=1).loc[start:end]
        
        techs = [c for c in DESIRED_ORDER if c in p_gen.columns]
        p_gen = p_gen[techs]
        
        p_gen.plot.area(ax=ax, stacked=True, 
                        color=[COLORS.get(c, '#333') for c in techs], alpha=0.8)
        load.plot(ax=ax, color='black', linewidth=2, label='Demand', linestyle='--')
        
        ax.set_title(f"{label}: {year} (Jan 15–22)", fontsize=14)
        ax.set_ylabel("Power [MW]", fontsize=12)
        ax.legend(loc='upper left', bbox_to_anchor=(1, 1))
        ax.grid(True, axis='y', linestyle='--', alpha=0.5)
    
    plt.tight_layout()
    plt.show()

# --- 5. DISPATCH: Best vs Worst solar year (summer week) ---
def plot_dispatch_best_worst_solar(results):
    """
    Side-by-side dispatch for a summer week in the best and worst solar years.
    """
    years = sorted(results.keys())
    solar_prod = {y: results[y]["production_twh"]["solar"] for y in years}
    best_year = max(solar_prod, key=solar_prod.get)
    worst_year = min(solar_prod, key=solar_prod.get)
    
    fig, axes = plt.subplots(2, 1, figsize=(14, 10), sharex=False)
    
    for ax, year, label in zip(axes, [best_year, worst_year], ["Best Solar Year", "Worst Solar Year"]):
        n = results[year]["network"]
        start = f"{year}-07-01"
        end = f"{year}-07-08"
        
        p_gen = n.generators_t.p.loc[start:end]
        load = n.loads_t.p_set.sum(axis=1).loc[start:end]
        
        techs = [c for c in DESIRED_ORDER if c in p_gen.columns]
        p_gen = p_gen[techs]
        
        p_gen.plot.area(ax=ax, stacked=True,
                        color=[COLORS.get(c, '#333') for c in techs], alpha=0.8)
        load.plot(ax=ax, color='black', linewidth=2, label='Demand', linestyle='--')
        
        ax.set_title(f"{label}: {year} (Jul 1–8)", fontsize=14)
        ax.set_ylabel("Power [MW]", fontsize=12)
        ax.legend(loc='upper left', bbox_to_anchor=(1, 1))
        ax.grid(True, axis='y', linestyle='--', alpha=0.5)
    
    plt.tight_layout()
    plt.show()


# --- 6. Generation Duration Curves: Best vs Worst year ---
def plot_duration_curves_comparison(results, resource="wind"):
    """
    Generation duration curves (lines only, no fill) for best vs worst year.
    Each technology sorted independently.
    """
    years = sorted(results.keys())
    
    if resource == "wind":
        prod = {y: results[y]["production_twh"]["wind_combined"] for y in years}
    else:
        prod = {y: results[y]["production_twh"]["solar"] for y in years}
    
    best_year = max(prod, key=prod.get)
    worst_year = min(prod, key=prod.get)
    
    fig, axes = plt.subplots(1, 2, figsize=(16, 6), sharey=True)
    
    for ax, year, label in zip(axes, [best_year, worst_year],
                                [f"Best {resource.capitalize()} Year",
                                 f"Worst {resource.capitalize()} Year"]):
        n = results[year]["network"]
        hours = np.arange(len(n.snapshots))
        
        # Each technology sorted independently
        for tech in ["wind_combined", "solar", "CCGT"]:
            sorted_vals = n.generators_t.p[tech].sort_values(ascending=False).values
            ax.plot(hours, sorted_vals, color=COLORS[tech], linewidth=2, label=tech)
        
        # Demand duration curve
        load_sorted = n.loads_t.p_set.sum(axis=1).sort_values(ascending=False).values
        ax.plot(hours, load_sorted, color='black', linewidth=2, linestyle='--', label='Demand')
        
        ax.set_title(f"{label}: {year}", fontsize=14)
        ax.set_xlabel("Hours (sorted independently)", fontsize=12)
        ax.legend(loc='upper right', fontsize=10)
        ax.grid(True, linestyle='--', alpha=0.4)
    
    axes[0].set_ylabel("Power [MW]", fontsize=12)
    fig.suptitle(f"Generation Duration Curves — Best vs Worst {resource.capitalize()} Year",
                 fontsize=15, y=1.02)
    plt.tight_layout()
    plt.show()

# --- 7. Economic comparison across years ---
def plot_economic_comparison(results):
    """
    Stacked bar chart of annual system costs (CAPEX + OPEX) per technology per year,
    with total system cost annotated on top.
    """
    years = sorted(results.keys())
    techs = [t for t in DESIRED_ORDER if t in results[years[0]]["network"].generators.index]
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    # --- Left: Stacked costs per year ---
    cost_data = {tech: [] for tech in techs}
    
    for year in years:
        n = results[year]["network"]
        costs_total = n.statistics.capex().add(n.statistics.opex(), fill_value=0)
        for tech in techs:
            carrier = n.generators.loc[tech, "carrier"]
            try:
                cost_data[tech].append(costs_total.loc["Generator", carrier] / 1e9)
            except KeyError:
                cost_data[tech].append(0)
    
    x = np.arange(len(years))
    width = 0.6
    bottom = np.zeros(len(years))
    
    for tech in techs:
        vals = np.array(cost_data[tech])
        ax1.bar(x, vals, width, bottom=bottom, label=tech,
                color=COLORS.get(tech, '#333'), alpha=0.85)
        bottom += vals
    
    for i, year in enumerate(years):
        ax1.text(i, bottom[i] + 0.01, f'{bottom[i]:.2f}', ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    ax1.set_xlabel("Weather Year", fontsize=12)
    ax1.set_ylabel("Annual Cost [B$/y]", fontsize=12)
    ax1.set_title("Total System Cost by Year", fontsize=14)
    ax1.set_xticks(x)
    ax1.set_xticklabels(years)
    ax1.legend(loc='upper left', bbox_to_anchor=(0, -0.12), ncol=3, fontsize=10)
    ax1.grid(True, axis='y', linestyle='--', alpha=0.4)
    
    # --- Right: CAPEX vs OPEX split per year ---
    total_capex = []
    total_opex = []
    for year in years:
        n = results[year]["network"]
        total_capex.append(n.statistics.capex().sum() / 1e9)
        total_opex.append(n.statistics.opex().sum() / 1e9)
    
    ax2.bar(x - 0.15, total_capex, 0.3, label='CAPEX', color='#2d4a7a', alpha=0.85)
    ax2.bar(x + 0.15, total_opex, 0.3, label='OPEX', color='#c17f59', alpha=0.85)
    
    for i in range(len(years)):
        ax2.text(i - 0.15, total_capex[i] + 0.01, f'{total_capex[i]:.2f}', ha='center', va='bottom', fontsize=9)
        ax2.text(i + 0.15, total_opex[i] + 0.01, f'{total_opex[i]:.2f}', ha='center', va='bottom', fontsize=9)
    
    ax2.set_xlabel("Weather Year", fontsize=12)
    ax2.set_ylabel("Annual Cost [B$/y]", fontsize=12)
    ax2.set_title("CAPEX vs OPEX by Year", fontsize=14)
    ax2.set_xticks(x)
    ax2.set_xticklabels(years)
    ax2.legend(loc='upper left', bbox_to_anchor=(0, -0.12), ncol=2, fontsize=10)
    ax2.grid(True, axis='y', linestyle='--', alpha=0.4)
    
    plt.tight_layout()
    plt.show()

# --- 8. Monthly profit comparison across years ---
def plot_monthly_profit(results):
    """
    Line chart of monthly profit (revenue - opex) for each weather year.
    """
    year_colors = {2015: '#2d4a7a', 2016: '#5b8c85', 2017: '#c17f59', 2018: '#8b5e83'}
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
              'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 9), sharex=True)
    
    for year in sorted(results.keys()):
        n = results[year]["network"]
        
        # Hourly revenue: generation * marginal price
        hourly_revenue = n.generators_t.p.multiply(
            n.buses_t.marginal_price.values
        ).sum(axis=1)
        
        # Hourly opex: generation * marginal cost
        marginal_costs = n.generators.marginal_cost
        hourly_opex = (n.generators_t.p * marginal_costs).sum(axis=1)
        
        # Hourly profit
        hourly_profit = hourly_revenue - hourly_opex
        
        # Monthly aggregation
        monthly_revenue = hourly_revenue.groupby(hourly_revenue.index.month).sum() / 1e6
        monthly_opex = hourly_opex.groupby(hourly_opex.index.month).sum() / 1e6
        monthly_profit = hourly_profit.groupby(hourly_profit.index.month).sum() / 1e6
        
        color = year_colors[year]
        ax1.plot(months, monthly_revenue.values, color=color, linewidth=2, 
                 marker='o', markersize=5, label=str(year))
        ax2.plot(months, monthly_profit.values, color=color, linewidth=2,
                 marker='o', markersize=5, label=str(year))
    
    ax1.set_ylabel("Monthly Revenue [M$]", fontsize=12)
    ax1.set_title("Monthly Revenue by Year", fontsize=14)
    ax1.legend(title="Year")
    ax1.grid(True, linestyle='--', alpha=0.4)
    
    ax2.set_ylabel("Monthly Profit [M$]", fontsize=12)
    ax2.set_title("Monthly Profit (Revenue − OPEX) by Year", fontsize=14)
    ax2.set_xlabel("Month", fontsize=12)
    ax2.axhline(0, color='black', linewidth=0.8, linestyle='-')
    ax2.legend(title="Year")
    ax2.grid(True, linestyle='--', alpha=0.4)
    
    plt.tight_layout()
    plt.show()

# --- 9. Monthly profit heatmap ---
def plot_profit_heatmap(results):
    """
    Heatmap of monthly profit (revenue - opex) per technology, averaged across years,
    plus a bar chart showing total annual profit split by technology.
    """
    years = sorted(results.keys())
    techs = [t for t in DESIRED_ORDER if t in results[years[0]]["network"].generators.index]
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
              'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    
    # Collect monthly profit per tech per year
    all_data = {tech: np.zeros((len(years), 12)) for tech in techs}
    
    for i, year in enumerate(years):
        n = results[year]["network"]
        prices = n.buses_t.marginal_price.values
        
        for tech in techs:
            gen = n.generators_t.p[tech]
            mc = n.generators.loc[tech, "marginal_cost"]
            hourly_profit = gen * (prices.flatten() - mc)
            monthly = hourly_profit.groupby(hourly_profit.index.month).sum() / 1e6
            all_data[tech][i, :] = monthly.values
    
    fig, axes = plt.subplots(len(techs), 1, figsize=(12, 3.5 * len(techs)), sharex=True)
    
    for ax, tech in zip(axes, techs):
        data = all_data[tech]
        
        im = ax.imshow(data, aspect='auto', cmap='coolwarm',
                        vmin=np.min([v.min() for v in all_data.values()]),
                        vmax=np.max([v.max() for v in all_data.values()]))
        
        ax.set_yticks(range(len(years)))
        ax.set_yticklabels(years)
        ax.set_xticks(range(12))
        ax.set_xticklabels(months)
        ax.set_title(f"{tech} — Monthly Profit [M$]", fontsize=13, fontweight='bold')
        
        # Annotate values
        for yi in range(len(years)):
            for xi in range(12):
                val = data[yi, xi]
                color = 'white' if abs(val) > (data.max() - data.min()) * 0.6 else 'black'
                ax.text(xi, yi, f'{val:.0f}', ha='center', va='center', fontsize=8, color=color)
        
        cbar = fig.colorbar(im, ax=ax, shrink=0.8, pad=0.02)
        cbar.set_label("M$", fontsize=9)
    
    axes[-1].set_xlabel("Month", fontsize=12)
    fig.suptitle("Monthly Scarcity Profit by Technology & Year", fontsize=16, y=1.01)
    plt.tight_layout()
    plt.show()










# STEP C: STORAGE ANALYSIS FUNCTIONS

# --- 1. PLOT GENERATION MIX WITH STORAGE ---
def plot_generation_mix_storage(n, start_date, end_date):
    """
    Plots stacked generation with storage. Discharge is stacked positive,
    charging is shown below zero.
    """
    p_gen = n.generators_t.p.loc[start_date:end_date]
    p_store = n.storage_units_t.p.loc[start_date:end_date]
    p_store.columns = n.storage_units.carrier
    
    p_discharge = p_store.clip(lower=0)
    p_charge = p_store.clip(upper=0)
    
    df_pos = pd.concat([p_gen, p_discharge], axis=1)
    cols_pos = [c for c in DESIRED_ORDER if c in df_pos.columns]
    df_pos = df_pos[cols_pos]
    
    load = n.loads_t.p_set.sum(axis=1).loc[start_date:end_date]
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    df_pos.plot.area(
        ax=ax, stacked=True,
        color=[COLORS.get(c, '#333') for c in df_pos.columns],
        alpha=0.8
    )
    
    for col in p_charge.columns:
        ax.fill_between(p_charge.index, p_charge[col], 0,
                        color=COLORS.get(col, '#333'), alpha=0.8,
                        label=f'{col} (charging)', zorder=5)
    
    load.plot(ax=ax, color='black', linewidth=2, label='Demand', linestyle='--')
    
    ax.axhline(0, color='black', lw=1)
    
    # Force y-axis to include negative values
    y_min = p_charge.min().min() * 1.1
    y_max = ax.get_ylim()[1]
    ax.set_ylim(y_min, y_max)
    
    ax.set_title(f"Generation Mix & Storage ({start_date} to {end_date})", fontsize=15)
    ax.set_ylabel("Power [MW]", fontsize=12)
    ax.legend(loc='upper left', bbox_to_anchor=(1, 1))
    ax.grid(True, axis='y', linestyle='--', alpha=0.5)
    
    plt.tight_layout()
    plt.show()

# --- 2. Battery State of Charge ---
# --- C1. Battery State of Charge ---
def plot_battery_soc(n, max_hours):
    """
    Heatmap of SOC (days x hours) + summer/winter week detail.
    """
    soc = n.storage_units_t.state_of_charge.iloc[:, 0]
    soc_pct = soc / (n.storage_units.p_nom_opt.iloc[0] * max_hours) * 100
    year = str(soc.index[0].year)
    
    fig, axes = plt.subplots(3, 1, figsize=(14, 13),
                              gridspec_kw={'height_ratios': [2, 1, 1]})
    
    # --- Top: Heatmap ---
    pivot = soc_pct.to_frame('soc')
    pivot['day'] = pivot.index.dayofyear
    pivot['hour'] = pivot.index.hour
    heatmap_data = pivot.pivot_table(index='hour', columns='day', values='soc')
    
    im = axes[0].imshow(heatmap_data.values, aspect='auto', cmap='YlGnBu',
                         origin='lower', vmin=0, vmax=100,
                         extent=[1, 365, 0, 24])
    axes[0].set_title(f"Battery State of Charge — {year}", fontsize=14)
    axes[0].set_xlabel("Day of Year")
    axes[0].set_ylabel("Hour of Day")
    cbar = fig.colorbar(im, ax=axes[0], shrink=0.8, pad=0.02)
    cbar.set_label("SOC [%]", fontsize=10)
    
    # --- Middle: Summer week ---
    soc_pct.loc[f'{year}-07-01':f'{year}-07-08'].plot(ax=axes[1], color='#8e44ad', linewidth=1.5)
    axes[1].set_title("Summer Week (Jul 1–8)", fontsize=13)
    axes[1].set_ylabel("SOC [%]")
    axes[1].set_ylim(0, 100)
    axes[1].grid(True, linestyle='--', alpha=0.4)
    
    # --- Bottom: Winter week ---
    soc_pct.loc[f'{year}-01-01':f'{year}-01-08'].plot(ax=axes[2], color='#8e44ad', linewidth=1.5)
    axes[2].set_title("Winter Week (Jan 1–8)", fontsize=13)
    axes[2].set_ylabel("SOC [%]")
    axes[2].set_ylim(0, 100)
    axes[2].grid(True, linestyle='--', alpha=0.4)
    
    plt.tight_layout()
    plt.show()


# --- 3. Battery operation at different time scales ---
def plot_battery_timescales(n):
    """
    Plots average battery dispatch by hour of day, day of week, and month.
    Shows how the battery balances at intraday, weekly, and seasonal scales.
    """
    battery_p = n.storage_units_t.p.iloc[:, 0]
    
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    
    # Intraday
    hourly_avg = battery_p.groupby(battery_p.index.hour).mean()
    axes[0].bar(hourly_avg.index, hourly_avg.values, color='#8e44ad', alpha=0.8)
    axes[0].axhline(0, color='black', linewidth=0.8)
    axes[0].set_xlabel("Hour of Day")
    axes[0].set_ylabel("Avg Power [MW]")
    axes[0].set_title("Intraday Pattern", fontsize=13)
    axes[0].grid(True, axis='y', linestyle='--', alpha=0.4)
    
    # Weekly
    daily_avg = battery_p.groupby(battery_p.index.dayofweek).mean()
    days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    axes[1].bar(days, daily_avg.values, color='#8e44ad', alpha=0.8)
    axes[1].axhline(0, color='black', linewidth=0.8)
    axes[1].set_ylabel("Avg Power [MW]")
    axes[1].set_title("Weekly Pattern", fontsize=13)
    axes[1].grid(True, axis='y', linestyle='--', alpha=0.4)
    
    # Seasonal
    monthly_avg = battery_p.groupby(battery_p.index.month).mean()
    months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
    axes[2].bar(months, monthly_avg.values, color='#8e44ad', alpha=0.8)
    axes[2].axhline(0, color='black', linewidth=0.8)
    axes[2].set_ylabel("Avg Power [MW]")
    axes[2].set_title("Seasonal Pattern", fontsize=13)
    axes[2].tick_params(axis='x', rotation=45)
    axes[2].grid(True, axis='y', linestyle='--', alpha=0.4)
    
    plt.suptitle("Battery Operation at Different Time Scales", fontsize=15, y=1.02)
    plt.tight_layout()
    plt.show()