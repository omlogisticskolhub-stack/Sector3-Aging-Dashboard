import streamlit as st
import pandas as pd
import plotly.express as px

# Page Config & Soft Dark Theme (Bright Contrast Removed)
st.set_page_config(
    page_title="Transhipment Failure Report",
    page_icon="🚛",
    layout="wide"
)

# Custom Styling for Low-Brightness UI
st.markdown("""
    <style>
    .main { background-color: #1e242b; color: #e1e6ed; }
    div[data-testid="stMetric"] {
        background-color: #2a323d;
        border: 1px solid #3d4856;
        border-radius: 8px;
        padding: 15px;
        color: #e1e6ed;
    }
    .stTabs [data-baseweb="tab-list"] { background-color: #2a323d; border-radius: 6px; }
    .stTabs [data-baseweb="tab"] { color: #a0aec0; }
    .stTabs [aria-selected="true"] { color: #63b3ed !important; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# Main Title
st.title("🚛 Transhipment Failure Report")
st.markdown("---")

# File Upload Section
uploaded_file = st.file_uploader("📥 Upload Transhipment Operational File (Excel / CSV)", type=["xlsx", "csv"])

if uploaded_file is not None:
    # Load File
    if uploaded_file.name.endswith('.csv'):
        df_raw = pd.read_csv(uploaded_file)
    else:
        df_raw = pd.read_excel(uploaded_file)

    # Column Auto-detection
    cn_col = next((c for c in df_raw.columns if 'CN' in c.upper() or 'DOCKET' in c.upper()), df_raw.columns[0])
    dest_col = next((c for c in df_raw.columns if 'DEST' in c.upper() or 'TODIST' in c.upper() or 'HUB' in c.upper()), None)
    consignee_col = next((c for c in df_raw.columns if 'CONSIGNEE' in c.upper() or 'PARTY' in c.upper()), None)
    pkg_col = next((c for c in df_raw.columns if 'PKG' in c.upper() or 'BOX' in c.upper()), None)
    aging_col = next((c for c in df_raw.columns if c.strip().upper() == 'HH' or 'HH' in c.upper() or 'AGING' in c.upper()), None)

    # 1. DUPLICATE CN FILTER LOGIC
    total_raw_rows = len(df_raw)
    df = df_raw.drop_duplicates(subset=[cn_col]).copy()
    duplicate_count = total_raw_rows - len(df)

    # Numeric Aging Processing
    if aging_col:
        df['HH_Numeric'] = pd.to_numeric(df[aging_col], errors='coerce').fillna(0)
    else:
        df['HH_Numeric'] = 0

    # 2. TOP 5 KEY KPIs PANEL
    st.markdown("### 📊 Operational Summary KPIs")
    k1, k2, k3, k4, k5 = st.columns(5)
    
    k1.metric("Total Unique CNs", f"{len(df):,}")
    k2.metric("Duplicates Removed", f"{duplicate_count:,}")
    k3.metric("Total Packages", f"{int(df[pkg_col].sum()):,}" if pkg_col else "N/A")
    k4.metric("Critical Load (>48 Hrs)", f"{len(df[df['HH_Numeric'] > 48]):,}")
    k5.metric("Max Pending Aging", f"{int(df['HH_Numeric'].max())} Hrs" if len(df) > 0 else "0 Hrs")

    st.markdown("---")

    # 3. DESTINATION FILTER PANEL
    st.markdown("### 🔍 Destination Filter Panel")
    if dest_col:
        dest_list = ["All Destinations"] + sorted(df[dest_col].dropna().astype(str).unique().tolist())
        selected_dest = st.selectbox("📍 Filter By Destination (TODIST / HUB):", dest_list)
    else:
        selected_dest = "All Destinations"

    # Filter Application
    df_filtered = df.copy()
    if selected_dest != "All Destinations" and dest_col:
        df_filtered = df_filtered[df_filtered[dest_col].astype(str) == selected_dest]

    st.markdown("---")

    # 4. AGING BUCKET SEGREGATION (24, 48, 72, 96+ Hours)
    b_24 = df_filtered[(df_filtered['HH_Numeric'] >= 0) & (df_filtered['HH_Numeric'] <= 24)]
    b_48 = df_filtered[(df_filtered['HH_Numeric'] > 24) & (df_filtered['HH_Numeric'] <= 48)]
    b_72 = df_filtered[(df_filtered['HH_Numeric'] > 48) & (df_filtered['HH_Numeric'] <= 72)]
    b_96 = df_filtered[df_filtered['HH_Numeric'] > 72]

    # Aging Buckets KPI Display
    st.markdown("### ⏱️ Transhipment Aging Buckets Summary")
    a1, a2, a3, a4 = st.columns(4)
    a1.metric("0 - 24 Hours", f"{len(b_24):,} CNs")
    a2.metric("24 - 48 Hours", f"{len(b_48):,} CNs")
    a3.metric("48 - 72 Hours", f"{len(b_72):,} CNs")
    a4.metric("72 - 96+ Hours (Critical)", f"{len(b_96):,} CNs")

    st.markdown("---")

    # 5. TABS FOR DETAILED VIEWS
    tab1, tab2, tab3 = st.tabs([
        "⏱️ Aging Wise Analysis", 
        "👤 Consignee Wise CN & Hour Summary", 
        "📋 Filtered Master Data"
    ])

    # --- TAB 1: AGING BUCKETS BREAKDOWN ---
    with tab1:
        st.subheader("Aging Wise Breakup Table")
        
        # Chart Representation
        aging_chart_data = pd.DataFrame({
            'Aging Bucket': ['0-24 Hrs', '24-48 Hrs', '48-72 Hrs', '72+ Hrs'],
            'CN Count': [len(b_24), len(b_48), len(b_72), len(b_96)]
        })
        
        fig = px.bar(
            aging_chart_data, x='Aging Bucket', y='CN Count', 
            title="Transhipment Failure Aging Distribution",
            color='CN Count', color_continuous_scale='Darkmint', text='CN Count'
        )
        fig.update_layout(paper_bgcolor="#1e242b", plot_bgcolor="#1e242b", font_color="#e1e6ed")
        st.plotly_chart(fig, use_container_width=True)

    # --- TAB 2: CONSIGNEE WISE SUMMARY ---
    with tab2:
        st.subheader("Consignee Wise Pending CN & Package Count")
        if consignee_col:
            summary_cols = {'CN_Count': (cn_col, 'count'), 'Max_Aging_Hours': ('HH_Numeric', 'max')}
            if pkg_col:
                summary_cols['Total_Packages'] = (pkg_col, 'sum')

            cons_summary = df_filtered.groupby(consignee_col).agg(**summary_cols).reset_index()
            cons_summary = cons_summary.sort_values(by='CN_Count', ascending=False)
            
            st.dataframe(cons_summary, height=400, use_container_width=True)
        else:
            st.warning("Consignee column auto-detection pending in uploaded file.")

    # --- TAB 3: MASTER DATA ---
    with tab3:
        st.subheader("Unique Deduplicated Data View")
        st.dataframe(df_filtered, height=400, use_container_width=True)

else:
    st.info("💡 Kripya **Transhipment Failure Report** Excel/CSV file upload karein analysis ke liye.")
