import streamlit as st
import pandas as pd
import plotly.express as px

# 1. PAGE SETUP WITH CLEAN LIGHT THEME
st.set_page_config(
    page_title="Transhipment Failure Report",
    page_icon="🚛",
    layout="wide"
)

# Professional Light Theme CSS (High Contrast & Clear Visibility)
st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; color: #0f172a; }
    div[data-testid="stMetric"] {
        background-color: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1) !important;
        border-radius: 10px !important;
        padding: 15px !important;
    }
    div[data-testid="stMetricLabel"] {
        color: #475569 !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
    }
    div[data-testid="stMetricValue"] {
        color: #1e293b !important;
        font-weight: 700 !important;
    }
    .stTabs [aria-selected="true"] { color: #2563eb !important; font-weight: bold; }
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

    # Auto Column Detection
    cn_col = next((c for c in df_raw.columns if 'CN' in c.upper() or 'DOCKET' in c.upper()), df_raw.columns[0])
    dest_col = next((c for c in df_raw.columns if 'DEST' in c.upper() or 'TODIST' in c.upper() or 'HUB' in c.upper()), None)
    consignee_col = next((c for c in df_raw.columns if 'CONSIGNEE' in c.upper() or 'PARTY' in c.upper()), None)
    pkg_col = next((c for c in df_raw.columns if 'PKG' in c.upper() or 'BOX' in c.upper()), None)
    aging_col = next((c for c in df_raw.columns if c.strip().upper() == 'HH' or 'HH' in c.upper() or 'AGING' in c.upper()), None)
    
    # Reason / Remarks Column Detection (Y Column / Reason Updated)
    reason_col = next((c for c in df_raw.columns if 'REASON' in c.upper() or 'REMARK' in c.upper() or 'UNDLVRD' in c.upper() or 'UPDATE' in c.upper()), None)

    # 1. DUPLICATE CN FILTER
    total_raw_rows = len(df_raw)
    df = df_raw.drop_duplicates(subset=[cn_col]).copy()
    duplicate_count = total_raw_rows - len(df)

    # Numeric Aging Conversion
    if aging_col:
        df['HH_Numeric'] = pd.to_numeric(df[aging_col], errors='coerce').fillna(0)
    else:
        df['HH_Numeric'] = 0

    # Reason Blank/Updated Status Column Creation
    if reason_col:
        df['Reason_Status'] = df[reason_col].apply(lambda x: "Blank (Pending)" if pd.isna(x) or str(x).strip() == "" or str(x).strip().upper() == "NAN" else "Updated")
    else:
        df['Reason_Status'] = "Blank (Pending)"

    # 2. TOP OPERATIONAL SUMMARY KPIS
    st.markdown("### 📊 Operational Summary KPIs")
    k1, k2, k3, k4, k5 = st.columns(5)
    
    k1.metric("Total Unique CNs", f"{len(df):,}")
    k2.metric("Duplicates Removed", f"{duplicate_count:,}")
    
    blank_reasons_cnt = len(df[df['Reason_Status'] == 'Blank (Pending)'])
    k3.metric("Pending Reason CNs", f"{blank_reasons_cnt:,}")
    
    k4.metric("Critical Load (>48 Hrs)", f"{len(df[df['HH_Numeric'] > 48]):,}")
    k5.metric("Max Pending Aging", f"{int(df['HH_Numeric'].max())} Hrs" if len(df) > 0 else "0 Hrs")

    st.markdown("---")

    # 3. FILTERS PANEL (DESTINATION + REASON BLANK CHECKBOX)
    st.markdown("### 🔍 Filters Panel")
    f_col1, f_col2 = st.columns([2, 1])

    with f_col1:
        if dest_col:
            dest_list = ["All Destinations"] + sorted(df[dest_col].dropna().astype(str).unique().tolist())
            selected_dest = st.selectbox("📍 Filter By Destination (TODIST / HUB):", dest_list)
        else:
            selected_dest = "All Destinations"

    with f_col2:
        st.write("") # Spacing
        only_blank_reasons = st.checkbox("⚠️ Show Only Pending/Blank Reasons", value=True)

    # Apply Filters
    df_filtered = df.copy()
    if selected_dest != "All Destinations" and dest_col:
        df_filtered = df_filtered[df_filtered[dest_col].astype(str) == selected_dest]
        
    if only_blank_reasons:
        df_filtered = df_filtered[df_filtered['Reason_Status'] == "Blank (Pending)"]

    st.markdown("---")

    # 4. AGING BUCKET SUMMARY (24, 48, 72, 96+ Hours)
    b_24 = df_filtered[(df_filtered['HH_Numeric'] >= 0) & (df_filtered['HH_Numeric'] <= 24)]
    b_48 = df_filtered[(df_filtered['HH_Numeric'] > 24) & (df_filtered['HH_Numeric'] <= 48)]
    b_72 = df_filtered[(df_filtered['HH_Numeric'] > 48) & (df_filtered['HH_Numeric'] <= 72)]
    b_96 = df_filtered[df_filtered['HH_Numeric'] > 72]

    st.markdown("### ⏱️ Transhipment Aging Buckets Summary")
    a1, a2, a3, a4 = st.columns(4)
    a1.metric("0 - 24 Hours", f"{len(b_24):,} CNs")
    a2.metric("24 - 48 Hours", f"{len(b_48):,} CNs")
    a3.metric("48 - 72 Hours", f"{len(b_72):,} CNs")
    a4.metric("72 - 96+ Hours (Critical)", f"{len(b_96):,} CNs")

    st.markdown("---")

    # 5. DETAILED VIEWS TABS
    tab1, tab2, tab3 = st.tabs([
        "⏱️ Aging Distribution Chart", 
        "👤 Consignee Wise Summary", 
        "📋 Filtered Master Data"
    ])

    # --- TAB 1: CHART ---
    with tab1:
        st.subheader("Transhipment Aging Load Breakdown")
        
        aging_chart_data = pd.DataFrame({
            'Aging Bucket': ['0-24 Hrs', '24-48 Hrs', '48-72 Hrs', '72+ Hrs'],
            'CN Count': [len(b_24), len(b_48), len(b_72), len(b_96)]
        })
        
        fig = px.bar(
            aging_chart_data, x='Aging Bucket', y='CN Count', 
            text='CN Count', color='CN Count',
            color_continuous_scale='Blues',
            title="Transhipment Failure Aging Distribution"
        )
        fig.update_layout(
            paper_bgcolor="#ffffff", 
            plot_bgcolor="#f8fafc", 
            font_color="#0f172a"
        )
        st.plotly_chart(fig, use_container_width=True)

    # --- TAB 2: CONSIGNEE SUMMARY ---
    with tab2:
        st.subheader("Consignee Wise Pending CN & Hour Summary")
        if consignee_col:
            summary_cols = {'Total_Pending_CNs': (cn_col, 'count'), 'Max_Aging_Hours': ('HH_Numeric', 'max')}
            if pkg_col:
                summary_cols['Total_Packages'] = (pkg_col, 'sum')

            cons_summary = df_filtered.groupby(consignee_col).agg(**summary_cols).reset_index()
            cons_summary = cons_summary.sort_values(by='Total_Pending_CNs', ascending=False)
            
            st.dataframe(cons_summary, height=400, use_container_width=True)
        else:
            st.warning("Consignee column auto-detection pending.")

    # --- TAB 3: MASTER DATA ---
    with tab3:
        st.subheader("Filtered Master Data Table")
        st.dataframe(df_filtered, height=400, use_container_width=True)

else:
    st.info("💡 Kripya **Transhipment Failure Report** Excel/CSV file upload karein analysis ke liye.")
