import streamlit as st
import pandas as pd
import plotly.express as px

# Page Setup
st.set_page_config(
    page_title="Transhipment Failure Report",
    page_icon="🚛",
    layout="wide"
)

# Custom Styling (High-Contrast Clean Light Mode)
st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; color: #0f172a; }
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
        font-size: 0.88rem !important;
    }
    div[data-testid="stMetricValue"] {
        color: #0f172a !important;
        font-weight: 700 !important;
        font-size: 1.4rem !important;
    }
    </style>
""", unsafe_allow_html=True)

# Main Title
st.title("🚛 Transhipment Failure Report")
st.markdown("---")

# File Uploader
uploaded_file = st.file_uploader("📥 Upload Transhipment Operational File (Excel / CSV)", type=["xlsx", "csv"])

if uploaded_file is not None:
    # Load File
    if uploaded_file.name.endswith('.csv'):
        df_raw = pd.read_csv(uploaded_file)
    else:
        df_raw = pd.read_excel(uploaded_file)

    # -------------------------------------------------------------
    # COLUMN DETECTION & COLUMN H (DESTINATION NAME) SPECIFIC LOGIC
    # -------------------------------------------------------------
    cn_col = next((c for c in df_raw.columns if 'CN' in c.upper() or 'DOCKET' in c.upper()), df_raw.columns[0])
    
    # Destination Name: Direct Column H check or fallback to Name/Dest keywords
    if len(df_raw.columns) >= 8:
        dest_col = df_raw.columns[7] # Column H (0-indexed 7th)
    else:
        dest_col = next((c for c in df_raw.columns if 'DEST' in c.upper() or 'NAME' in c.upper() or 'TODIST' in c.upper()), df_raw.columns[1])

    pkg_col = next((c for c in df_raw.columns if 'PKG' in c.upper() or 'BOX' in c.upper()), None)
    wt_col = next((c for c in df_raw.columns if 'TON' in c.upper() or 'WEIGHT' in c.upper() or 'WT' in c.upper()), None)
    aging_col = next((c for c in df_raw.columns if c.strip().upper() == 'HH' or 'HH' in c.upper() or 'AGING' in c.upper()), None)
    reason_col = next((c for c in df_raw.columns if 'REASON' in c.upper() or 'REMARK' in c.upper() or 'UNDLVRD' in c.upper() or 'UPDATE' in c.upper()), None)

    # Clean CNs & Numeric Conversions
    raw_total_cnt = len(df_raw)
    df = df_raw.drop_duplicates(subset=[cn_col]).copy()
    
    df['HH_Numeric'] = pd.to_numeric(df[aging_col], errors='coerce').fillna(0) if aging_col else 0
    df['PKG_Numeric'] = pd.to_numeric(df[pkg_col], errors='coerce').fillna(0) if pkg_col else 0
    df['WT_Numeric'] = pd.to_numeric(df[wt_col], errors='coerce').fillna(0) if wt_col else 0

    # Reason Status Column Setup
    if reason_col:
        df['Reason_Status'] = df[reason_col].apply(lambda x: "Pending" if pd.isna(x) or str(x).strip() == "" or str(x).strip().upper() in ["NAN", "NONE"] else "Updated")
    else:
        df['Reason_Status'] = "Pending"

    # -------------------------------------------------------------
    # 1. TOP OPERATIONAL SUMMARY KPIS
    # -------------------------------------------------------------
    st.markdown("### 📊 Operational Summary KPIs")
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    
    k1.metric("Total CNs", f"{raw_total_cnt:,}")
    k2.metric("Total Unique CNs", f"{len(df):,}")
    
    pending_cnt = len(df[df['Reason_Status'] == 'Pending'])
    updated_cnt = len(df[df['Reason_Status'] == 'Updated'])
    k3.metric("Pending Reason", f"{pending_cnt:,}")
    k4.metric("Reason Updated", f"{updated_cnt:,}")
    
    k5.metric("Total Packages", f"{int(df['PKG_Numeric'].sum()):,}")
    k6.metric("Total Weight (Tons)", f"{round(df['WT_Numeric'].sum(), 2):,}")

    st.markdown("---")

    # -------------------------------------------------------------
    # 2. FILTER PANEL
    # -------------------------------------------------------------
    st.markdown("### 🔍 Filter Panel")
    f_col1, f_col2 = st.columns([2, 1])

    with f_col1:
        dest_list = ["All Destinations"] + sorted(df[dest_col].dropna().astype(str).unique().tolist())
        selected_dest = st.selectbox("📍 Filter By Destination Name (Col H):", dest_list)

    with f_col2:
        st.write("") # Spacing
        filter_blank_only = st.checkbox("⚠️ Filter Only Pending/Blank Reasons", value=False)

    # Filter Application
    df_filtered = df.copy()
    if selected_dest != "All Destinations":
        df_filtered = df_filtered[df_filtered[dest_col].astype(str) == selected_dest]
        
    if filter_blank_only:
        df_filtered = df_filtered[df_filtered['Reason_Status'] == "Pending"]

    st.markdown("---")

    # -------------------------------------------------------------
    # 3. DESTINATION SUMMARY (LEFT) + AGING CHART (RIGHT)
    # -------------------------------------------------------------
    c_left, c_right = st.columns([1, 1])

    with c_left:
        st.markdown("### 📍 Destination Wise Pending Summary")
        summary_cols = {
            'CN Count': (cn_col, 'count'),
            'Total PKG': ('PKG_Numeric', 'sum'),
            'Total Weight (Tons)': ('WT_Numeric', 'sum'),
            'Max Aging (HH)': ('HH_Numeric', 'max')
        }
        
        dest_summary = df_filtered.groupby(dest_col).agg(**summary_cols).reset_index()
        dest_summary['Total Weight (Tons)'] = dest_summary['Total Weight (Tons)'].round(2)
        dest_summary = dest_summary.sort_values(by='CN Count', ascending=False)
        
        st.dataframe(dest_summary, height=360, use_container_width=True)

    with c_right:
        st.markdown("### 📊 Aging Distribution Chart")
        
        b_24 = len(df_filtered[(df_filtered['HH_Numeric'] >= 0) & (df_filtered['HH_Numeric'] <= 24)])
        b_48 = len(df_filtered[(df_filtered['HH_Numeric'] > 24) & (df_filtered['HH_Numeric'] <= 48)])
        b_72 = len(df_filtered[(df_filtered['HH_Numeric'] > 48) & (df_filtered['HH_Numeric'] <= 72)])
        b_96 = len(df_filtered[df_filtered['HH_Numeric'] > 72])

        aging_chart_data = pd.DataFrame({
            'Aging Bucket': ['0-24 Hrs', '24-48 Hrs', '48-72 Hrs', '72+ Hrs'],
            'CN Count': [b_24, b_48, b_72, b_96]
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
            height=360
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # -------------------------------------------------------------
    # 4. FILTERED CN MASTER DETAILS (ALL CNs INCLUDED)
    # -------------------------------------------------------------
    st.markdown("### 📋 Filtered CN Master Details")
    
    def get_bucket_label(hh):
        if hh <= 24: return '0-24 Hrs'
        elif hh <= 48: return '24-48 Hrs'
        elif hh <= 72: return '48-72 Hrs'
        else: return '72+ Hrs'

    df_filtered['Aging_Bucket'] = df_filtered['HH_Numeric'].apply(get_bucket_label)

    # Ordered Display Columns
    display_cols = [cn_col, dest_col]
    if pkg_col: display_cols.append(pkg_col)
    if wt_col: display_cols.append(wt_col)
    if reason_col: display_cols.append(reason_col)
    display_cols.append('Reason_Status')
    if aging_col: display_cols.append(aging_col)
    display_cols.append('Aging_Bucket')

    st.dataframe(df_filtered[display_cols], height=380, use_container_width=True)

else:
    st.info("💡 Kripya **Transhipment Failure Report** Excel/CSV file upload karein analysis ke liye.")
