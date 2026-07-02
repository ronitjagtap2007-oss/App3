import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="EcoRoute - Fleet Logistics Optimizer",
    page_icon="🚚",
    layout="wide"
)

# --- CUSTOM CSS FOR UI/UX ---
st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    div[data-testid="stMetricValue"] { font-size: 1.8rem; font-weight: 700; color: #0f172a; }
    .stButton > button { width: 100%; border-radius: 6px; font-weight: 600; }
    </style>
""", unsafe_allow_html=True)

st.title("🚚 EcoRoute: Logistics & Carbon Optimizer")
st.caption("Optimize delivery sequences, minimize fuel expenses, and track fleet Scope 3 carbon emissions.")

# --- SIDEBAR: FLEET CONFIGURATION ---
st.sidebar.header("Fleet Settings")

vehicle_type = st.sidebar.selectbox(
    "Vehicle Fleet Type",
    options=["Heavy Duty Diesel Truck", "Light Commercial Van", "Electric Delivery Van", "Gasoline Freight Carrier"]
)

# Set emissions factors (kg CO2 per km) based on vehicle selection
emissions_factors = {
    "Heavy Duty Diesel Truck": 0.95,
    "Light Commercial Van": 0.45,
    "Electric Delivery Van": 0.08, # Regional grid average
    "Gasoline Freight Carrier": 0.72
}
co2_factor = emissions_factors[vehicle_type]

fuel_cost_per_km = st.sidebar.slider("Estimated Fuel/Energy Cost per KM ($)", 0.10, 2.50, 0.45)

# --- MOCK BUSINESS DATA GENERATION ---
# Simulating a distribution hub in a central location with surrounding delivery destinations
@st.cache_data
def get_delivery_data():
    np.random.seed(42)
    # Central Hub (e.g., Chicago area baseline)
    hub_lat, hub_lon = 41.8781, -87.6298
    
    names = [f"Stop #{i}: Client Delivery" for i in range(1, 9)]
    lats = hub_lat + np.random.uniform(-0.15, 0.15, size=8)
    lons = hub_lon + np.random.uniform(-0.15, 0.15, size=8)
    demands = np.random.randint(5, 40, size=8) # packages or crates
    
    df = pd.DataFrame({
        "Destination": names,
        "Latitude": lats,
        "Longitude": lons,
        "Payload Demand (Crates)": demands
    })
    return hub_lat, hub_lon, df

hub_lat, hub_lon, destinations_df = get_delivery_data()

# --- MAIN CONTENT LAYOUT ---
col_map, col_controls = st.columns([2, 1])

with col_controls:
    st.subheader("Manage Deliveries")
    st.write("Select the active drop-off points for today's dispatch loop:")
    
    # Interactive multi-select for stops
    selected_stops = st.multiselect(
        "Active Destinations",
        options=destinations_df["Destination"].tolist(),
        default=destinations_df["Destination"].tolist()[:5]
    )
    
    optimize_click = st.button("⚡ Optimize Route Sequence", type="primary")

# Filter data based on user selection
active_df = destinations_df[destinations_df["Destination"].isin(selected_stops)].copy()

# Simple Routing Logic (Nearest Neighbor heuristic calculation for simulation)
if len(active_df) > 0:
    # Always start at the hub
    route_sequence = [{"name": "Central Distribution Hub", "lat": hub_lat, "lon": hub_lon}]
    remaining = active_df.to_dict('records')
    
    curr_lat, curr_lon = hub_lat, hub_lon
    total_distance = 0.0
    
    while remaining:
        # Calculate straight-line rough matrix calculation scaled to approximate road distance (x 1.25)
        closest_idx = np.argmin([
            (np.sqrt((r['Latitude'] - curr_lat)**2 + (r['Longitude'] - curr_lon)**2) * 111) for r in remaining
        ])
        closest_stop = remaining.pop(closest_idx)
        
        # Add approximate road distance
        step_dist = np.sqrt((closest_stop['Latitude'] - curr_lat)**2 + (closest_stop['Longitude'] - curr_lon)**2) * 111 * 1.25
        total_distance += step_dist
        
        route_sequence.append({
            "name": closest_stop["Destination"],
            "lat": closest_stop["Latitude"],
            "lon": closest_stop["Longitude"]
        })
        curr_lat, curr_lon = closest_stop["Latitude"], closest_stop["Longitude"]
        
    # Return to hub
    final_return = np.sqrt((hub_lat - curr_lat)**2 + (hub_lon - curr_lon)**2) * 111 * 1.25
    total_distance += final_return
    route_sequence.append({"name": "Central Distribution Hub (Return)", "lat": hub_lat, "lon": hub_lon})
    
    # Calculate Impact Metrics
    total_co2 = (total_distance * co2_factor) / 1000 # convert to Metric Tons
    total_fuel_expense = total_distance * fuel_cost_per_km
    
    # If not optimized, show unoptimized penalties (simulated baseline comparison)
    if not optimize_click:
        total_distance *= 1.32
        total_co2 *= 1.32
        total_fuel_expense *= 1.32

    # --- METRICS DISPLAY ---
    st.markdown("### Core KPIs")
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric(
            label="Total Trip Distance", 
            value=f"{total_distance:.1f} KM",
            delta="-24.2% (Optimized)" if optimize_click else "Unoptimized Base"
        )
    with m2:
        st.metric(
            label="Carbon Footprint (Scope 3)", 
            value=f"{total_co2:.3f} MT CO2e",
            delta=f"-{(total_co2 * 0.24):.3f} MT Saved" if optimize_click else "High Impact"
        )
    with m3:
        st.metric(
            label="Projected Dispatch Cost", 
            value=f"${total_fuel_expense:,.2f}",
            delta=f"-${(total_fuel_expense * 0.24):.2f}" if optimize_click else "Standard Rates"
        )

    # --- MAP & VISUALIZATIONS ---
    with col_map:
        st.subheader("Dispatched Fleet Dispatch View")
        
        route_df = pd.DataFrame(route_sequence)
        
        # Plotly map representation
        fig = px.scatter_mapbox(
            route_df, 
            lat="lat", 
            lon="lon", 
            hover_name="name", 
            zoom=11, 
            height=500
        )
        
        # Draw dispatch paths
        fig.add_trace(go.Scattermapbox(
            lat=route_df["lat"],
            lon=route_df["lon"],
            mode="lines+markers",
            line=dict(width=3.5, color="#10b981" if optimize_click else "#ef4444"),
            name="Fleet Sequence Path"
        ))
        
        fig.update_layout(
            mapbox_style="carto-positron",
            margin={"r":0,"t":0,"l":0,"b":0}
        )
        st.plotly_chart(fig, use_container_width=True)

    # Detailed Dispatch Breakdown Table
    st.subheader("📋 Manifest & Schedule Execution Order")
    manifest_df = pd.DataFrame(route_sequence).rename(columns={"name": "Location Point", "lat": "Latitude", "lon": "Longitude"})
    st.dataframe(manifest_df, use_container_width=True)

else:
    st.warning("Please pick at least one destination from the control panel to generate dispatch insights.")
