import streamlit as st
import pandas as pd
import plotly.express as px

# 1. PAGE SETUP WITH CLEAN HIGH-VISIBILITY THEME
st.set_page_config(
    page_title="Transhipment Failure Report",
    page_icon="🚛",
    layout="wide"
)

# Custom High-Contrast Styling
st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; color: #0f172a; }
    
    /* Base Metric Card Styling */
    div[data-testid="stMetric"] {
        background-color: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08) !important;
        border-radius: 8px !important;
        padding: 12px 16px !important;
    }
    div[data-testid="stMetricLabel"] {
        color: #475569 !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
    }
    div[data-testid="stMetricValue"] {
        color: #0f172a !important;
        font-weight: 700 !important;
        font-size: 1.5rem !important;
    }

    /* Color Coded Metric Borders for Aging Buckets */
    .metric-green div[data-testid="stMetric"] { border-left: 6px solid #22c55e !important; }
    .metric-orange div[data-testid="stMetric"] { border-left: 6px solid #f97316 !important; }
    .metric-yellow div[data-testid="stMetric"] { border-left: 6px solid #eab308 !important; }
    .metric-red div[data-testid="stMetric"] { border-left: 6px solid #dc2626 !important; }
    </style>
""", unsafe_allow_html=True)

# Main Dashboard Title
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
    pkg_col = next((c for c in df_raw.columns if 'PKG' in c.upper() or 'BOX' in c.upper()), None)
    aging_col = next((c for c in df_raw.columns if c.strip().upper() == 'HH' or 'HH' in c.upper() or 'AGING' in c.upper()), None)
    reason_col = next((c for c in df_raw.columns if 'REASON' in c.upper() or 'REMARK' in c.upper() or 'UNDLVRD' in c.upper() or 'UPDATE' in c.upper()), None)

    # 1. DUPLICATE CN FILTERING
    total_raw_rows = len(df_raw)
    df = df_raw.drop_duplicates(subset=[cn_col]).copy()
    duplicate_count = total_raw_rows - len(df)

    # Numeric Aging Conversion
    if aging_col:
        df['HH_Numeric'] = pd.to_numeric(df[aging_col], errors='coerce').fillna(0)
    else:
        df['HH_Numeric'] = 0

    # Reason Status Column
    if reason_col:
        df['Reason_Status'] = df[reason_col].apply(lambda x: "Blank (Pending)" if pd.isna(x) or str(x).strip() == "" or str(x).strip().upper() == "NAN" else "Updated")
    else:
        df['Reason_Status'] = "Blank (Pending)"

    # -------------------------------------------------------------
    # 2. GLOBAL FILTERS PANEL (Updates Everything Below & Above)
    # -------------------------------------------------------------
    st.markdown("### 🔍 Filter Panel")
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

    # Apply Global Filter
    df_filtered = df.copy()
    if selected_dest != "All Destinations" and dest_col:
        df_filtered = df_filtered[df_filtered[dest_col].astype(str) == selected_dest]
        
    if only_blank_reasons:
        df_filtered = df_filtered[df_filtered['Reason_Status'] == "Blank (Pending)"]

    st.markdown("---")

    # -------------------------------------------------------------
    # 3. OPERATIONAL SUMMARY KPIS (DYNAMICALLY LINKED TO FILTERS)
    # -------------------------------------------------------------
    st.markdown("### 📊 Operational Summary KPIs")
    k1, k2, k3, k4 = st.columns(4)
    
    k1.metric("Total Unique CNs", f"{len(df_filtered):,}")
    k2.metric("Duplicates Removed", f"{duplicate_count:,}")
    
    blank_cnt = len(df_filtered[df_filtered['Reason_Status'] == 'Blank (Pending)'])
    k3.metric("Pending Reason CNs", f"{blank_cnt:,}")
    
    # Critical Load > 72 Hours
    critical_72_cnt = len(df_filtered[df_filtered['HH_Numeric'] > 72])
    k4.metric("🚨 Critical Load (>72 Hrs)", f"{critical_72_cnt:,}")

    st.markdown("---")

    # -------------------------------------------------------------
    # 4. COLOR-CODED AGING BUCKET SUMMARY
    # -------------------------------------------------------------
    b_24 = df_filtered[(df_filtered['HH_Numeric'] >= 0) & (df_filtered['HH_Numeric'] <= 24)]
    b_48 = df_filtered[(df_filtered['HH_Numeric'] > 24) & (df_filtered['HH_Numeric'] <= 48)]
    b_72 = df_filtered[(df_filtered['HH_Numeric'] > 48) & (df_filtered['HH_Numeric'] <= 72)]
    b_96 = df_filtered[df_filtered['HH_Numeric'] > 72]

    st.markdown("### ⏱️ Transhipment Aging Buckets Summary")
    a1, a2, a3, a4 = st.columns(4)
    
    with a1:
        st.markdown('<div class="metric-green">', unsafe_allow_html=True)
        st.metric("0 - 24 Hours", f"{len(b_24):,} CNs")
        st.markdown('</div>', unsafe_allow_html=True)

    with a2:
        st.markdown('<div class="metric-orange">', unsafe_allow_html=True)
        st.metric("24 - 48 Hours", f"{len(b_48):,} CNs")
        st.markdown('</div>', unsafe_allow_html=True)

    with a3:
        st.markdown('<div class="metric-yellow">', unsafe_allow_html=True)
        st.metric("48 - 72 Hours", f"{len(b_72):,} CNs")
        st.markdown('</div>', unsafe_allow_html=True)

    with a4:
        st.markdown('<div class="metric-red">', unsafe_allow_html=True)
        st.metric("72 - 96+ Hours (Cherry Red)", f"{len(b_96):,} CNs")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")

    # -------------------------------------------------------------
    # 5. SIDE-BY-SIDE: DESTINATION SUMMARY + COLOR-CODED CHART
    # -------------------------------------------------------------
    c_left, c_right = st.columns([1, 1])

    with c_left:
        st.markdown("### 📍 Destination Wise Pending Summary")
        if dest_col:
            summary_cols = {'Pending CNs': (cn_col, 'count'), 'Max Aging (HH)': ('HH_Numeric', 'max')}
            if pkg_col:
                summary_cols['Pending PKG'] = (pkg_col, 'sum')

            dest_summary = df_filtered.groupby(dest_col).agg(**summary_cols).reset_index()
            dest_summary = dest_summary.sort_values(by='Pending CNs', ascending=False)
            
            st.dataframe(dest_summary, height=350, use_container_width=True)
        else:
            st.warning("Destination column not detected.")

    with c_right:
        st.markdown("### 📊 Aging Distribution Chart")
        
        aging_chart_data = pd.DataFrame({
            'Aging Bucket': ['0-24 Hrs', '24-48 Hrs', '48-72 Hrs', '72+ Hrs'],
            'CN Count': [len(b_24), len(b_48), len(b_72), len(b_96)],
            'Color': ['#22c55e', '#f97316', '#eab308', '#dc2626'] # Green, Orange, Yellow, Cherry Red
        })
        
        fig = px.bar(
            aging_chart_data, x='Aging Bucket', y='CN Count', 
            text='CN Count',
            color='Aging Bucket',
            color_discrete_map={
                '0-24 Hrs': '#22c55e',
                '24-48 Hrs': '#f97316',
                '48-72 Hrs': '#eab308',
                '72+ Hrs': '#dc2626'
            },
            title="Aging Breakdown (Hours)"
        )
        fig.update_layout(
            paper_bgcolor="#ffffff", 
            plot_bgcolor="#f8fafc", 
            font_color="#0f172a",
            showlegend=False,
            height=350
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # -------------------------------------------------------------
    # 6. COMPACT MASTER DATA TABLE WITH AGING BUCKETS
    # -------------------------------------------------------------
    st.markdown("### 📋 Filtered CN Master Details")
    
    # Adding Aging Bucket Label in Data Frame
    def get_bucket_label(hh):
        if hh <= 24: return '0-24 Hrs'
        elif hh <= 48: return '24-48 Hrs'
        elif hh <= 72: return '48-72 Hrs'
        else: return '72+ Hrs'

    df_filtered['Aging_Bucket'] = df_filtered['HH_Numeric'].apply(get_bucket_label)

    # Select Key Columns to display
    display_cols = [cn_col]
    if dest_col: display_cols.append(dest_col)
    if aging_col: display_cols.append(aging_col)
    display_cols.append('Aging_Bucket')
    if pkg_col: display_cols.append(pkg_col)
    if reason_col: display_cols.append(reason_col)
    display_cols.append('Reason_Status')

    st.dataframe(df_filtered[display_cols], height=300, use_container_width=True)

else:
    st.info("💡 Kripya **Transhipment Failure Report** Excel/CSV file upload karein analysis ke liye.")
