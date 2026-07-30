import streamlit as st
import pandas as pd
import plotly.express as px

# Page Setup
st.set_page_config(
    page_title="Transhipment Failure Report",
    page_icon="🚛",
    layout="wide"
)

# Custom Styling (High Contrast, Centered KPIs & Colored Borders)
st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; color: #0f172a; }
    
    /* Base Metric Box */
    div[data-testid="stMetric"] {
        background-color: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08) !important;
        border-radius: 8px !important;
        padding: 10px 14px !important;
        text-align: center !important;
    }
    div[data-testid="stMetricLabel"] {
        color: #475569 !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
        justify-content: center !alignment;
    }
    div[data-testid="stMetricValue"] {
        color: #0f172a !important;
        font-weight: 700 !important;
        font-size: 1.35rem !important;
    }

    /* Red Outer Border for Pending Reason */
    .metric-pending div[data-testid="stMetric"] {
        border: 2px solid #ef4444 !important;
        background-color: #fef2f2 !important;
    }
    .metric-pending div[data-testid="stMetricValue"] { color: #dc2626 !important; }

    /* Green Outer Border for Updated Reason */
    .metric-updated div[data-testid="stMetric"] {
        border: 2px solid #22c55e !important;
        background-color: #f0fdf4 !important;
    }
    .metric-updated div[data-testid="stMetricValue"] { color: #16a34a !important; }
    </style>
""", unsafe_allow_html=True)

# Dashboard Title
st.title("🚛 Transhipment Failure Report")
st.markdown("---")

# File Upload
uploaded_file = st.file_uploader("📥 Upload Transhipment Operational File (Excel / CSV)", type=["xlsx", "csv"])

if uploaded_file is not None:
    # Load File
    if uploaded_file.name.endswith('.csv'):
        df_raw = pd.read_csv(uploaded_file)
    else:
        df_raw = pd.read_excel(uploaded_file)

    # Auto Detect Columns
    cn_col = next((c for c in df_raw.columns if 'CN' in c.upper() or 'DOCKET' in c.upper()), df_raw.columns[0])
    
    if len(df_raw.columns) >= 8:
        dest_col = df_raw.columns[7] # Col H
    else:
        dest_col = next((c for c in df_raw.columns if 'DEST' in c.upper() or 'NAME' in c.upper() or 'TODIST' in c.upper()), df_raw.columns[1])

    pkt_col = next((c for c in df_raw.columns if 'PKT' in c.upper() or 'PKG' in c.upper() or 'BOX' in c.upper() or 'PACKAGE' in c.upper()), None)
    wt_col = next((c for c in df_raw.columns if 'TON' in c.upper() or 'WEIGHT' in c.upper() or 'WT' in c.upper()), None)
    aging_col = next((c for c in df_raw.columns if c.strip().upper() == 'HH' or 'HH' in c.upper() or 'AGING' in c.upper()), None)
    reason_col = next((c for c in df_raw.columns if 'REASON' in c.upper() or 'REMARK' in c.upper() or 'UNDLVRD' in c.upper() or 'UPDATE' in c.upper()), None)

    # 1. Deduplication (Unique CNs)
    df = df_raw.drop_duplicates(subset=[cn_col]).copy()
    
    df['HH_Numeric'] = pd.to_numeric(df[aging_col], errors='coerce').fillna(0) if aging_col else 0
    df['PKT_Numeric'] = pd.to_numeric(df[pkt_col], errors='coerce').fillna(0) if pkt_col else 0
    df['WT_Numeric'] = pd.to_numeric(df[wt_col], errors='coerce').fillna(0) if wt_col else 0

    # Reason Status Column
    if reason_col:
        df['Reason_Status'] = df[reason_col].apply(lambda x: "Pending" if pd.isna(x) or str(x).strip() == "" or str(x).strip().upper() in ["NAN", "NONE"] else "Updated")
    else:
        df['Reason_Status'] = "Pending"

    # -------------------------------------------------------------
    # FILTER CONTROLS (Top Filters applied FIRST)
    # -------------------------------------------------------------
    st.markdown("### 🔍 Filters Panel")
    f_col1, f_col2 = st.columns([1, 1])

    with f_col1:
        dest_list = ["All Destinations"] + sorted(df[dest_col].dropna().astype(str).unique().tolist())
        selected_dest = st.selectbox("📍 Filter By Destination Name (Col H):", dest_list)

    with f_col2:
        status_filter = st.selectbox(
            "⚡ Filter By Reason Status:",
            options=["All Status", "Pending Reason Only", "Updated Reason Only"]
        )

    # Master Data Filter Application
    df_filtered = df.copy()
    if selected_dest != "All Destinations":
        df_filtered = df_filtered[df_filtered[dest_col].astype(str) == selected_dest]

    if status_filter == "Pending Reason Only":
        df_filtered = df_filtered[df_filtered['Reason_Status'] == "Pending"]
    elif status_filter == "Updated Reason Only":
        df_filtered = df_filtered[df_filtered['Reason_Status'] == "Updated"]

    st.markdown("---")

    # -------------------------------------------------------------
    # 1. TOP 5 KPIS IN A SINGLE ROW (Fully Dynamic to Filters)
    # -------------------------------------------------------------
    st.markdown("### 📊 Operational Summary KPIs")
    
    k1, k2, k3, k4, k5 = st.columns(5)

    # Calculate Filtered Values
    tot_cn = len(df_filtered)
    tot_pkt = int(df_filtered['PKT_Numeric'].sum())
    
    tot_wt_raw = df_filtered['WT_Numeric'].sum()
    formatted_wt = f"{round(tot_wt_raw / 1000, 2):,} T" if tot_wt_raw > 1000 else f"{round(tot_wt_raw, 2):,} T"

    pending_cnt = len(df_filtered[df_filtered['Reason_Status'] == 'Pending'])
    updated_cnt = len(df_filtered[df_filtered['Reason_Status'] == 'Updated'])

    k1.metric("Total CN (Unique)", f"{tot_cn:,}")
    k2.metric("Total PKT Count", f"{tot_pkt:,}")
    k3.metric("Total Weight", formatted_wt)

    with k4:
        st.markdown('<div class="metric-pending">', unsafe_allow_html=True)
        st.metric("Pending Reason", f"{pending_cnt:,}")
        st.markdown('</div>', unsafe_allow_html=True)

    with k5:
        st.markdown('<div class="metric-updated">', unsafe_allow_html=True)
        st.metric("Reason Updated", f"{updated_cnt:,}")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")

    # -------------------------------------------------------------
    # 2. DESTINATION SUMMARY (LEFT) + AGING CHART (RIGHT)
    # -------------------------------------------------------------
    c_left, c_right = st.columns([1, 1])

    with c_left:
        st.markdown("### 📍 Destination Wise Summary")
        summary_cols = {
            'CN Count': (cn_col, 'count'),
            'Total PKT': ('PKT_Numeric', 'sum'),
            'Total Weight (T)': ('WT_Numeric', lambda x: round(x.sum() / (1000 if tot_wt_raw > 1000 else 1), 2)),
            'Max Aging (HH)': ('HH_Numeric', 'max')
        }
        
        dest_summary = df_filtered.groupby(dest_col).agg(**summary_cols).reset_index()
        dest_summary = dest_summary.sort_values(by='CN Count', ascending=False)
        
        # Reset Index for Sequential Serial Number (1, 2, 3...)
        dest_summary = dest_summary.reset_index(drop=True)
        dest_summary.index = dest_summary.index + 1
        
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
    # 3. FILTERED MASTER DETAILS TABLE (Sequential S.No 1, 2, 3...)
    # -------------------------------------------------------------
    st.markdown("### 📋 Filtered CN Master Details")
    
    def get_bucket_label(hh):
        if hh <= 24: return '0-24 Hrs'
        elif hh <= 48: return '24-48 Hrs'
        elif hh <= 72: return '48-72 Hrs'
        else: return '72+ Hrs'

    df_filtered['Aging_Bucket'] = df_filtered['HH_Numeric'].apply(get_bucket_label)

    display_cols = [cn_col, dest_col]
    if pkt_col: display_cols.append(pkt_col)
    if wt_col: display_cols.append(wt_col)
    if reason_col: display_cols.append(reason_col)
    display_cols.append('Reason_Status')
    if aging_col: display_cols.append(aging_col)
    display_cols.append('Aging_Bucket')

    # Sequential Index Reset for Master Table
    master_view = df_filtered[display_cols].copy().reset_index(drop=True)
    master_view.index = master_view.index + 1

    st.dataframe(master_view, height=380, use_container_width=True)

else:
    st.info("💡 Kripya **Transhipment Failure Report** Excel/CSV file upload karein analysis ke liye.")
