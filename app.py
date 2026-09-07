"""
Streamlit web app for Fantasy Football Draft Simulator
Mobile-friendly interface for iPhone, Android, and desktop browsers
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import json

from src.simulator import DraftSimulator
from src.player import PlayerDataLoader, PlayerPool
from config import CONFIG

# Page configuration
st.set_page_config(
    page_title="Fantasy Draft Simulator",
    page_icon="🏈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for mobile optimization
st.markdown("""
    <style>
    .main {
        padding: 1rem;
    }
    .stButton>button {
        width: 100%;
        padding: 0.75rem;
        font-size: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .header-text {
        font-size: 1.5rem;
        font-weight: bold;
        margin: 1rem 0;
    }
    .warning-box {
        background-color: #ffe6e6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #ff4444;
        margin: 1rem 0;
    }
    .success-box {
        background-color: #e6ffe6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #44ff44;
        margin: 1rem 0;
    }
    .info-box {
        background-color: #e6f2ff;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #4488ff;
        margin: 1rem 0;
    }
    </style>
    """, unsafe_allow_html=True)

# Initialize session state
if 'simulation_results' not in st.session_state:
    st.session_state.simulation_results = None
if 'simulation_complete' not in st.session_state:
    st.session_state.simulation_complete = False

# Title
st.markdown("# 🏈 Fantasy Football Draft Simulator")
st.markdown("Monte Carlo simulation with injury risk modeling")

# Sidebar configuration
st.sidebar.markdown("## ⚙️ League Settings")

col1, col2 = st.sidebar.columns(2)
with col1:
    draft_position = st.sidebar.slider(
        "Your Draft Position",
        min_value=1,
        max_value=12,
        value=10,
        help="Pick order in your league"
    )

with col2:
    num_teams = st.sidebar.slider(
        "Number of Teams",
        min_value=8,
        max_value=14,
        value=10,
        help="Total teams in your league"
    )

ppr_scoring = st.sidebar.checkbox("PPR Scoring", value=True, help="Points per reception")

st.sidebar.markdown("## 🎲 Simulation Settings")

simulation_speed = st.sidebar.select_slider(
    "Simulation Speed",
    options=["Fast (100k)", "Medium (500k)", "Thorough (1M)"],
    value="Thorough (1M)"
)

# Map speed to simulation count
sim_count_map = {
    "Fast (100k)": 100000,
    "Medium (500k)": 500000,
    "Thorough (1M)": 1000000
}
num_simulations = sim_count_map[simulation_speed]

# Data source
st.sidebar.markdown("## 📊 Player Data")
data_source = st.sidebar.radio(
    "Data Source",
    ["Sample Data", "Upload CSV"],
    help="Use built-in sample or upload your own player data"
)

# Main content
if data_source == "Sample Data":
    st.info("📌 Using sample player data for demonstration")
    use_sample = True
else:
    uploaded_file = st.file_uploader(
        "Upload Player CSV",
        type=['csv'],
        help="CSV with columns: player_id, name, position, nfl_team, age, adp, bye_week, projected_points, floor, ceiling, snap_count_pct, target_share, carry_share, red_zone_touches_pct"
    )
    use_sample = uploaded_file is None

# Main tabs
tab1, tab2, tab3, tab4 = st.tabs(["🎯 Dashboard", "📈 Analysis", "⚠️ Risk", "💡 Strategy"])

with tab1:
    st.markdown("### Simulation Dashboard")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Draft Position", f"#{draft_position}", f"of {num_teams}")
    with col2:
        st.metric("Simulation Count", f"{num_simulations:,}")
    with col3:
        st.metric("Scoring", "PPR" if ppr_scoring else "Standard")
    
    st.markdown("---")
    
    # Run simulation button
    run_button_col1, run_button_col2 = st.columns([3, 1])
    with run_button_col1:
        if st.button("🚀 Run Simulation", key="run_sim", use_container_width=True):
            with st.spinner(f"Running {num_simulations:,} simulations... This may take a few minutes."):
                try:
                    # Configure league
                    CONFIG.update_league(
                        draft_position=draft_position,
                        num_teams=num_teams,
                        ppr_scoring=ppr_scoring
                    )
                    
                    CONFIG.update_simulation(
                        num_simulations=num_simulations
                    )
                    
                    # Load player data
                    if use_sample:
                        player_pool = PlayerDataLoader.create_sample_pool()
                    else:
                        player_pool = PlayerDataLoader.load_from_csv("temp_upload.csv")
                    
                    # Run simulator
                    simulator = DraftSimulator(CONFIG.league, CONFIG.simulation)
                    results = simulator.run_simulations(player_pool, num_simulations)
                    
                    st.session_state.simulation_results = results
                    st.session_state.simulation_complete = True
                    
                    st.success("✅ Simulation Complete!")
                    st.balloons()
                    
                except Exception as e:
                    st.error(f"❌ Error running simulation: {str(e)}")
    
    # Display results if available
    if st.session_state.simulation_complete and st.session_state.simulation_results:
        results = st.session_state.simulation_results
        stats = results['statistics']
        
        st.markdown("---")
        st.markdown("### 📊 Season Points Projection")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(
                "Expected (Mean)",
                f"{stats['mean_points']:.0f}",
                f"±{stats['std_dev']:.0f}",
                delta_color="off"
            )
        with col2:
            st.metric(
                "Median",
                f"{stats['median_points']:.0f}",
                "50th %ile"
            )
        with col3:
            st.metric(
                "Floor",
                f"{stats['percentile_1']:.0f}",
                "1st %ile"
            )
        with col4:
            st.metric(
                "Ceiling",
                f"{stats['percentile_99']:.0f}",
                "99th %ile"
            )
        
        # Distribution chart
        st.markdown("### Points Distribution")
        scores = results['lineup_scores']
        
        chart_data = pd.DataFrame({
            'Points': scores,
            'Count': np.histogram(scores, bins=50)[0]
        })
        
        import plotly.express as px
        fig = px.histogram(
            {'Points': scores},
            nbins=50,
            title="Season Points Distribution (All Simulations)",
            labels={'Points': 'Total Points', 'count': 'Frequency'}
        )
        fig.update_xaxes(title_text="Total Season Points")
        fig.update_yaxes(title_text="Frequency")
        st.plotly_chart(fig, use_container_width=True)
        
        # Percentile breakdown
        st.markdown("### Percentile Breakdown")
        percentile_data = {
            'Percentile': ['1st', '25th', '50th', '75th', '99th'],
            'Points': [
                stats['percentile_1'],
                stats['percentile_25'],
                stats['percentile_50'],
                stats['percentile_75'],
                stats['percentile_99']
            ]
        }
        percentile_df = pd.DataFrame(percentile_data)
        st.dataframe(percentile_df, use_container_width=True, hide_index=True)

with tab2:
    if st.session_state.simulation_complete and st.session_state.simulation_results:
        results = st.session_state.simulation_results
        stats = results['statistics']
        
        st.markdown("### 📈 Detailed Statistics")
        
        stats_data = {
            'Metric': [
                'Mean Points',
                'Median Points',
                'Standard Deviation',
                'Minimum',
                'Maximum',
                'Win Probability'
            ],
            'Value': [
                f"{stats['mean_points']:.1f}",
                f"{stats['median_points']:.1f}",
                f"{stats['std_dev']:.1f}",
                f"{stats['min_points']:.1f}",
                f"{stats['max_points']:.1f}",
                f"{stats['win_probability']*100:.1f}%"
            ]
        }
        
        stats_df = pd.DataFrame(stats_data)
        st.dataframe(stats_df, use_container_width=True, hide_index=True)
        
        st.markdown("### 💡 Interpretation")
        st.markdown(f"""
        - **Expected Value**: Your team will average **{stats['mean_points']:.0f}** points
        - **Consistency**: Results vary by ±{stats['std_dev']:.0f} points (standard deviation)
        - **Best Case**: You could score up to **{stats['percentile_99']:.0f}** points (99th percentile)
        - **Worst Case**: You could score as low as **{stats['percentile_1']:.0f}** points (1st percentile)
        - **Win Rate**: You'll win ~{stats['win_probability']*100:.0f}% of the time (beat median)
        """)
    else:
        st.info("👆 Run a simulation first to see analysis")

with tab3:
    if st.session_state.simulation_complete and st.session_state.simulation_results:
        results = st.session_state.simulation_results
        recs = results['recommendations']
        
        st.markdown("### ⚠️ High-Risk Running Backs")
        st.markdown("These RBs have high injury probability. Consider avoiding or stacking their backup.")
        
        if recs['high_risk_rbs']:
            high_risk_data = {
                'Rank': range(1, len(recs['high_risk_rbs'][:10]) + 1),
                'Player': [p[0] for p in recs['high_risk_rbs'][:10]],
                'Injury Risk': [f"{p[1]*100:.1f}%" for p in recs['high_risk_rbs'][:10]]
            }
            high_risk_df = pd.DataFrame(high_risk_data)
            st.dataframe(high_risk_df, use_container_width=True, hide_index=True)
            
            st.markdown("""
            **Handcuff Strategy**: When you draft a high-risk RB, consider also drafting their backup:
            - Lower risk spread (backup takes over if injury happens)
            - Get both upside scenarios
            - Works especially well in later rounds
            """)
        
        st.markdown("---")
        st.markdown("### 🚨 Heavy Usage Teams")
        st.markdown("Teams with one dominant RB (high injury risk). Monitor workload all season.")
        
        if recs['heavy_usage_teams']:
            heavy_usage_data = {
                'Team': [t['team'] for t in recs['heavy_usage_teams'][:8]],
                'Primary RB': [t['primary_player'] for t in recs['heavy_usage_teams'][:8]],
                'Usage %': [f"{t['usage_pct']*100:.1f}%" for t in recs['heavy_usage_teams'][:8]],
                'Risk': ['🔴 HIGH' if t['is_concerning'] else '🟡 MODERATE' for t in recs['heavy_usage_teams'][:8]]
            }
            heavy_usage_df = pd.DataFrame(heavy_usage_data)
            st.dataframe(heavy_usage_df, use_container_width=True, hide_index=True)
    else:
        st.info("👆 Run a simulation first to see risk analysis")

with tab4:
    if st.session_state.simulation_complete and st.session_state.simulation_results:
        results = st.session_state.simulation_results
        recs = results['recommendations']
        
        st.markdown("### ✓ Backup RB Opportunities")
        st.markdown("Backup RBs with high upside if starter gets injured. Great late-round picks!")
        
        if recs['backup_opportunities']:
            backup_data = {
                'Backup': [o['backup'] for o in recs['backup_opportunities'][:8]],
                'Team': [o['team'] for o in recs['backup_opportunities'][:8]],
                'ADP': [f"{o['backup_adp']:.1f}" for o in recs['backup_opportunities'][:8]],
                'Opportunity': [f"{o['opportunity_score']:.2f}" for o in recs['backup_opportunities'][:8]],
                'Ceiling Upside': [f"{o['upside_points']:.0f} pts" for o in recs['backup_opportunities'][:8]]
            }
            backup_df = pd.DataFrame(backup_data)
            st.dataframe(backup_df, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.markdown("### 📋 Round-by-Round Strategy")
        
        for strategy in recs['strategy'][:5]:
            round_num = strategy.get('round', 'N/A')
            st.markdown(f"#### Round {round_num}")
            st.markdown(f"**Strategy:** {strategy['strategy']}")
            if 'avoid' in strategy:
                st.warning(f"⚠️ Avoid: {strategy['avoid']}")
            if 'key_insight' in strategy:
                st.info(f"💡 Key Insight: {strategy['key_insight']}")
    else:
        st.info("👆 Run a simulation first to see draft strategy")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: gray; font-size: 0.8rem; margin-top: 2rem;">
📱 Mobile-Friendly Fantasy Football Draft Simulator<br>
🏈 Works on iPhone, Android, and Desktop<br>
⚡ Powered by Monte Carlo Simulations<br>
</div>
""", unsafe_allow_html=True)
