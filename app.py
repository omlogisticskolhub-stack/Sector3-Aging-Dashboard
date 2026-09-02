import streamlit as st
import pandas as pd
import plotly.express as px

# Page Setup
st.set_page_config(
    page_title="Transhipment Failure Report",
    page_icon="🚛",
    layout="wide"
)

# ==========================================
# 🔒 PASSWORD PROTECTION SYSTEM
# ==========================================
def check_password():
    """Returns True if the user had the correct password."""
    def password_entered():
        if st.session_state["password"] == "Dhiraj@01072026":
            st.session_state["password_correct"] = True
            del st.session_state["password"]  
        else:
            st.session_state["password_correct"] = False

    if st.session_state.get("password_correct", False):
        return True

    st.title("🔒 Restricted Access")
    st.markdown("This dashboard is highly secured. Please enter the password to continue.")
    
    st.text_input(
        "Enter Password:", 
        type="password", 
        on_change=password_entered, 
        key="password"
    )
    
    if "password_correct" in st.session_state and not st.session_state["password_correct"]:
        st.error("❌ Incorrect Password. Access Denied!")
        
    return False

if not check_password():
    st.stop()
# ==========================================

# Custom Styling to fix multi-select tag overflow and text hiding
st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; color: #0f172a; }
    
    /* Fix Multiselect Tag Wrapping so text never hides or goes inward */
    .stMultiSelect div[data-baseweb="select"] {
        flex-wrap: wrap !important;
        height: auto !important;
        min-height: 42px !important;
        padding-bottom: 4px !important;
    }
    .stMultiSelect span[data-baseweb="tag"] {
        white-space: normal !important;
        height: auto !important;
        margin: 2px !important;
    }

    div[data-testid="stMetric"] {
        background-color: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08) !important;
        border-radius: 8px !important;
        padding: 12px 14px !important;
        text-align: center !important;
        min-height: 90px !important;
    }
    div[data-testid="stMetricLabel"] {
        color: #475569 !important;
        font-weight: 600 !important;
        font-size: 0.8rem !important;
    }
    div[data-testid="stMetricValue"] {
        color: #0f172a !important;
        font-weight: 700 !important;
        font-size: 1.25rem !important;
    }
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
        dest_col = df_raw.columns[7] # Col H (DESTINATION_NAME)
    else:
        dest_col = next((c for c in df_raw.columns if 'DEST' in c.upper() or 'NAME' in c.upper() or 'TODIST' in c.upper()), df_raw.columns[1])

    pkt_col = next((c for c in df_raw.columns if 'PKT' in c.upper() or 'PKG' in c.upper() or 'BOX' in c.upper() or 'PACKAGE' in c.upper()), None)
    wt_col = next((c for c in df_raw.columns if 'TON' in c.upper() or 'WEIGHT' in c.upper() or 'WT' in c.upper()), None)
    aging_col = next((c for c in df_raw.columns if c.strip().upper() == 'HH' or 'HH' in c.upper() or 'AGING' in c.upper()), None)
    reason_col = next((c for c in df_raw.columns if 'REASON' in c.upper() or 'REMARK' in c.upper() or 'UNDLVRD' in c.upper() or 'UPDATE' in c.upper()), None)
    
    cee_col = next((c for c in df_raw.columns if 'CEE' in c.upper()), 'CEE_NAME')

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

    # Layout Container for KPIs
    kpi_container = st.container()
    st.markdown("---")

    # ==========================================
    # 2. FILTERS PANEL (2 WIDE COLUMNS)
    # ==========================================
    st.markdown("### 🔍 Filters Panel")
    
    dest_list = sorted(df[dest_col].dropna().astype(str).unique().tolist())
    cee_list = sorted(df[cee_col].dropna().astype(str).unique().tolist()) if cee_col in df.columns else []
    bucket_options = ['0-24 Hrs', '24-48 Hrs', '48-72 Hrs', '72+ Hrs']

    # Initialize session states
    if "dest_ms" not in st.session_state:
        st.session_state["dest_ms"] = dest_list
    if "cee_ms" not in st.session_state:
        st.session_state["cee_ms"] = cee_list if cee_list else []
    if "bucket_ms" not in st.session_state:
        st.session_state["bucket_ms"] = bucket_options

    fc1, fc2 = st.columns(2)

    with fc1:
        st.markdown("📍 **Destination Name**")
        def toggle_dest():
            if st.session_state.get("all_dest", False):
                st.session_state["dest_ms"] = dest_list
            else:
                st.session_state["dest_ms"] = []

        st.checkbox("Select All Destinations", value=True, key="all_dest", on_change=toggle_dest)
        selected_destinations = st.multiselect("Filter By Destination Name:", options=dest_list, key="dest_ms", label_visibility="collapsed")

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("⚡ **Reason Status**")
        status_filter = st.selectbox(
            "Filter By Reason Status:",
            options=["All Status", "Pending Reason Only", "Updated Reason Only"],
            label_visibility="collapsed"
        )

    with fc2:
        st.markdown("🏢 **Customer Name (CEE)**")
        if cee_list:
            def toggle_cee():
                if st.session_state.get("all_cee", False):
                    st.session_state["cee_ms"] = cee_list
                else:
                    st.session_state["cee_ms"] = []

            st.checkbox("Select All CEE", value=True, key="all_cee", on_change=toggle_cee)
            selected_cee = st.multiselect("Filter By Customer Name (CEE):", options=cee_list, key="cee_ms", label_visibility="collapsed")
        else:
            selected_cee = []

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("⏳ **Aging Buckets**")
        def toggle_buckets():
            if st.session_state.get("all_buckets", False):
                st.session_state["bucket_ms"] = bucket_options
            else:
                st.session_state["bucket_ms"] = []

        st.checkbox("Select All Buckets", value=True, key="all_buckets", on_change=toggle_buckets)
        selected_buckets = st.multiselect("Filter By Aging Buckets:", options=bucket_options, key="bucket_ms", label_visibility="collapsed")

    # APPLY FILTERS
    df_filtered = df.copy()
    if selected_destinations:
        df_filtered = df_filtered[df_filtered[dest_col].astype(str).isin(selected_destinations)]
    else:
        df_filtered = df_filtered.iloc[0:0]

    if cee_col in df.columns and selected_cee:
        df_filtered = df_filtered[df_filtered[cee_col].astype(str).isin(selected_cee)]
    elif cee_col in df.columns:
        df_filtered = df_filtered.iloc[0:0]

    if status_filter == "Pending Reason Only":
        df_filtered = df_filtered[df_filtered['Reason_Status'] == "Pending"]
    elif status_filter == "Updated Reason Only":
        df_filtered = df_filtered[df_filtered['Reason_Status'] == "Updated"]

    if selected_buckets:
        df_filtered = df_filtered[df_filtered['Aging_Bucket'].isin(selected_buckets)]
    else:
        df_filtered = df_filtered.iloc[0:0]

    st.markdown("---")

    # ==========================================
    # 3. TOP OPERATIONAL SUMMARY KPIS
    # ==========================================
    with kpi_container:
        st.markdown("### 📊 Operational Summary KPIs")
        
        tot_cn = len(df_filtered)
        tot_pkt = int(df_filtered['PKT_Numeric'].sum())
        tot_wt_raw = df_filtered['WT_Numeric'].sum()
        
        formatted_wt = f"{round(tot_wt_raw / 1000, 2):,} TON" if tot_wt_raw > 1000 else f"{round(tot_wt_raw, 2):,} TON"

        pending_cnt = len(df_filtered[df_filtered['Reason_Status'] == 'Pending'])
        updated_cnt = len(df_filtered[df_filtered['Reason_Status'] == 'Updated'])

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

    # ==========================================
    # 4. DESTINATION SUMMARY (LEFT) + AGING CHART (RIGHT)
    # ==========================================
    c_left, c_right = st.columns([1, 1])

    with c_left:
        st.markdown("### 📍 Destination Wise Summary")
        
        summary_cols = {
            'CN Count': (cn_col, 'count'),
            'CN Box Count': ('PKT_Numeric', 'sum'),
            'Total Weight (TON)': ('WT_Numeric', lambda x: round(x.sum() / (1000 if tot_wt_raw > 1000 else 1), 2)),
            'Max Aging (HH)': ('HH_Numeric', 'max')
        }
        
        group_cols = [dest_col]

        dest_summary = df_filtered.groupby(group_cols).agg(**summary_cols).reset_index()
        dest_summary = dest_summary.sort_values(by='CN Count', ascending=False)
        dest_summary = dest_summary.reset_index(drop=True)
        dest_summary.index = dest_summary.index + 1
        
        st.dataframe(dest_summary, height=240, use_container_width=True)

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
            height=240
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # ==========================================
    # 5. CEE / CUSTOMER NAME WISE ANALYSIS BOX
    # ==========================================
    if cee_col in df.columns:
        st.markdown("### 🏢 CEE-Wise Breakdown Analysis (Customer Name, CN Count, Box Count & Weight)")
        
        cee_summary = df_filtered.groupby([cee_col]).agg(
            CN_Count=(cn_col, 'count'),
            CN_Box_Count=('PKT_Numeric', 'sum'),
            Total_Weight_TON=('WT_Numeric', lambda x: round(x.sum() / (1000 if tot_wt_raw > 1000 else 1), 2)),
            Max_Aging_HH=('HH_Numeric', 'max')
        ).reset_index().sort_values(by='CN_Count', ascending=False)
        
        cee_summary = cee_summary.reset_index(drop=True)
        cee_summary.index = cee_summary.index + 1
        st.dataframe(cee_summary, height=220, use_container_width=True)
        st.markdown("---")

    # ==========================================
    # 6. FILTERED MASTER DETAILS TABLE
    # ==========================================
    st.markdown("### 📋 Filtered CN Master Details")
    
    display_cols = [cn_col, dest_col]
    if cee_col in df.columns: display_cols.append(cee_col)
    if pkt_col: display_cols.append(pkt_col)
    if wt_col: display_cols.append(wt_col)
    if reason_col: display_cols.append(reason_col)
    display_cols.append('Reason_Status')
    if aging_col: display_cols.append(aging_col)
    display_cols.append('Aging_Bucket')

    master_view = df_filtered[display_cols].copy().reset_index(drop=True)
    master_view.index = master_view.index + 1

    st.dataframe(master_view, height=300, use_container_width=True)

else:
    st.info("💡 Kripya **Transhipment Failure Report** Excel/CSV file upload karein analysis ke liye.")
