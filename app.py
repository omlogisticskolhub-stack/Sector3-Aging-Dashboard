import streamlit as st
import pandas as pd
import plotly.express as px

# Page Setup
st.set_page_config(
    page_title="Transhipment Failure Report",
    page_icon="🚛",
    layout="wide"
)

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

    # Aging Bucket Label Function
    def get_bucket_label(hh):
        if hh <= 24: return '0-24 Hrs'
        elif hh <= 48: return '24-48 Hrs'
        elif hh <= 72: return '48-72 Hrs'
        else: return '72+ Hrs'

    df['Aging_Bucket'] = df['HH_Numeric'].apply(get_bucket_label)

    # -------------------------------------------------------------
    # LAYOUT TRICK: Reserve space for KPIs on top, but calculate them AFTER filters
    # -------------------------------------------------------------
    kpi_container = st.container()

    st.markdown("---")

    # -------------------------------------------------------------
    # 2. FILTERS PANEL (Placing this before KPI calculations in logic)
    # -------------------------------------------------------------
    st.markdown("### 🔍 Filters Panel")
    f1, f2, f3 = st.columns(3)

    with f1:
        dest_list = sorted(df[dest_col].dropna().astype(str).unique().tolist())
        selected_destinations = st.multiselect(
            "📍 Filter By Destination Name (Col H):",
            options=dest_list,
            default=[]
        )

    with f2:
        status_filter = st.selectbox(
            "⚡ Filter By Reason Status:",
            options=["All Status", "Pending Reason Only", "Updated Reason Only"]
        )

    with f3:
        bucket_options = ['0-24 Hrs', '24-48 Hrs', '48-72 Hrs', '72+ Hrs']
        selected_buckets = st.multiselect(
            "⏳ Filter By Aging Buckets:",
            options=bucket_options,
            default=bucket_options
        )

    # APPLY FILTERS TO MASTER DATASET FIRST
    df_filtered = df.copy()
    if selected_destinations:
        df_filtered = df_filtered[df_filtered[dest_col].astype(str).isin(selected_destinations)]

    if status_filter == "Pending Reason Only":
        df_filtered = df_filtered[df_filtered['Reason_Status'] == "Pending"]
    elif status_filter == "Updated Reason Only":
        df_filtered = df_filtered[df_filtered['Reason_Status'] == "Updated"]

    if selected_buckets:
        df_filtered = df_filtered[df_filtered['Aging_Bucket'].isin(selected_buckets)]

    # -------------------------------------------------------------
    # 1. TOP 5 OPERATIONAL SUMMARY KPIS (Now rendering inside top container with Filtered Data)
    # -------------------------------------------------------------
    with kpi_container:
        st.markdown("### 📊 Operational Summary KPIs")
        
        # Calculations based on df_filtered (DYNAMIC)
        tot_cn = len(df_filtered)
        tot_pkt = int(df_filtered['PKT_Numeric'].sum())
        tot_wt_raw = df_filtered['WT_Numeric'].sum()
        
        # Weight Format with explicit 'TON'
        formatted_wt = f"{round(tot_wt_raw / 1000, 2):,} TON" if tot_wt_raw > 1000 else f"{round(tot_wt_raw, 2):,} TON"

        pending_cnt = len(df_filtered[df_filtered['Reason_Status'] == 'Pending'])
        updated_cnt = len(df_filtered[df_filtered['Reason_Status'] == 'Updated'])

        # Custom HTML to strictly enforce single line layout and Red borders
        custom_kpi_html = f"""
        <div style="display: flex; justify-content: space-between; gap: 15px; margin-bottom: 10px;">
            <div style="flex: 1; background-color: #ffffff; border: 1px solid #cbd5e1; border-radius: 8px; padding: 15px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.08);">
                <div style="color: #475569; font-weight: 600; font-size: 0.85rem; margin-bottom: 5px;">Total CN (Unique)</div>
                <div style="color: #0f172a; font-weight: 700; font-size: 1.35rem;">{tot_cn:,}</div>
            </div>
            <div style="flex: 1; background-color: #ffffff; border: 1px solid #cbd5e1; border-radius: 8px; padding: 15px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.08);">
                <div style="color: #475569; font-weight: 600; font-size: 0.85rem; margin-bottom: 5px;">Total PKT Count</div>
                <div style="color: #0f172a; font-weight: 700; font-size: 1.35rem;">{tot_pkt:,}</div>
            </div>
            <div style="flex: 1; background-color: #ffffff; border: 1px solid #cbd5e1; border-radius: 8px; padding: 15px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.08);">
                <div style="color: #475569; font-weight: 600; font-size: 0.85rem; margin-bottom: 5px;">Total Weight</div>
                <div style="color: #0f172a; font-weight: 700; font-size: 1.35rem;">{formatted_wt}</div>
            </div>
            <div style="flex: 1; background-color: #fef2f2; border: 2px solid #dc2626; border-radius: 8px; padding: 15px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.08);">
                <div style="color: #475569; font-weight: 600; font-size: 0.85rem; margin-bottom: 5px;">Pending Reason</div>
                <div style="color: #dc2626; font-weight: 700; font-size: 1.35rem;">{pending_cnt:,}</div>
            </div>
            <div style="flex: 1; background-color: #fef2f2; border: 2px solid #dc2626; border-radius: 8px; padding: 15px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.08);">
                <div style="color: #475569; font-weight: 600; font-size: 0.85rem; margin-bottom: 5px;">Reason Updated</div>
                <div style="color: #dc2626; font-weight: 700; font-size: 1.35rem;">{updated_cnt:,}</div>
            </div>
        </div>
        """
        st.markdown(custom_kpi_html, unsafe_allow_html=True)

    st.markdown("---")

    # -------------------------------------------------------------
    # 3. DESTINATION SUMMARY (LEFT) + AGING CHART (RIGHT)
    # -------------------------------------------------------------
    c_left, c_right = st.columns([1, 1])

    with c_left:
        st.markdown("### 📍 Destination Wise Summary")
        summary_cols = {
            'CN Count': (cn_col, 'count'),
            'Total PKT': ('PKT_Numeric', 'sum'),
            'Total Weight (TON)': ('WT_Numeric', lambda x: round(x.sum() / (1000 if tot_wt_raw > 1000 else 1), 2)),
            'Max Aging (HH)': ('HH_Numeric', 'max')
        }
        
        dest_summary = df_filtered.groupby(dest_col).agg(**summary_cols).reset_index()
        dest_summary = dest_summary.sort_values(by='CN Count', ascending=False)
        
        dest_summary = dest_summary.reset_index(drop=True)
        dest_summary.index = dest_summary.index + 1
        
        st.dataframe(dest_summary, height=360, use_container_width=True)

    with c_right:
        st.markdown("### 📊 Aging Distribution Chart")
        
        b_24 = len(df_filtered[df_filtered['Aging_Bucket'] == '0-24 Hrs'])
        b_48 = len(df_filtered[df_filtered['Aging_Bucket'] == '24-48 Hrs'])
        b_72 = len(df_filtered[df_filtered['Aging_Bucket'] == '48-72 Hrs'])
        b_96 = len(df_filtered[df_filtered['Aging_Bucket'] == '72+ Hrs'])

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
    # 4. FILTERED MASTER DETAILS TABLE (Sequential S.No 1, 2, 3...)
    # -------------------------------------------------------------
    st.markdown("### 📋 Filtered CN Master Details")
    
    display_cols = [cn_col, dest_col]
    if pkt_col: display_cols.append(pkt_col)
    if wt_col: display_cols.append(wt_col)
    if reason_col: display_cols.append(reason_col)
    display_cols.append('Reason_Status')
    if aging_col: display_cols.append(aging_col)
    display_cols.append('Aging_Bucket')

    master_view = df_filtered[display_cols].copy().reset_index(drop=True)
    master_view.index = master_view.index + 1

    st.dataframe(master_view, height=380, use_container_width=True)

else:
    st.info("💡 Kripya **Transhipment Failure Report** Excel/CSV file upload karein analysis ke liye.")
