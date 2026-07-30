import streamlit as st
import pandas as pd
import plotly.express as px

# Page Config
st.set_page_config(
    page_title="Sector 3 - Shipment Failure & Aging Tracker",
    page_icon="🚨",
    layout="wide"
)

st.title("🚨 Sector 3 - Shipment Failure & Priority Aging Tracker")
st.caption("Upload Failure/Incoming Shipment file to analyze high-aging cases & Consignee details.")

# -------------------------------------------------------------
# 1. FILE UPLOAD SECTION
# -------------------------------------------------------------
uploaded_file = st.file_uploader("📥 Upload Failure / Operational Data File (Excel or CSV)", type=["xlsx", "csv"])

if uploaded_file is not None:
    # Load File
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    st.success(f"File Uploaded Successfully! Total Rows: {len(df):,}")
    st.markdown("---")

    # Column Auto-detection
    dest_col = next((c for c in df.columns if 'DEST' in c.upper() or 'HUB' in c.upper()), None)
    consignee_col = next((c for c in df.columns if 'CONSIGNEE' in c.upper() or 'PARTY' in c.upper()), None)
    cn_col = next((c for c in df.columns if 'CN' in c.upper() or 'DOCKET' in c.upper()), df.columns[0])
    pkg_col = next((c for c in df.columns if 'PKG' in c.upper() or 'BOX' in c.upper()), None)
    
    # HH (Aging) Column Detection
    aging_col = next((c for c in df.columns if c.strip().upper() == 'HH' or 'HH' in c.upper() or 'AGING' in c.upper()), None)

    # Convert HH column to numeric for bucketing
    if aging_col:
        df['HH_Numeric'] = pd.to_numeric(df[aging_col], errors='coerce').fillna(0)
    else:
        df['HH_Numeric'] = 0

    # -------------------------------------------------------------
    # 2. FILTERS SECTION
    # -------------------------------------------------------------
    st.markdown("### 🔍 Filters Panel")
    f_col1, f_col2 = st.columns(2)

    with f_col1:
        if dest_col:
            dest_list = ["All Destinations"] + sorted(df[dest_col].dropna().astype(str).unique().tolist())
            selected_dest = st.selectbox("📍 Select Destination Name:", dest_list)
        else:
            selected_dest = "All Destinations"

    with f_col2:
        if consignee_col:
            consignee_list = ["All Consignees"] + sorted(df[consignee_col].dropna().astype(str).unique().tolist())
            selected_consignee = st.selectbox("👤 Select Consignee Name:", consignee_list)
        else:
            selected_consignee = "All Consignees"

    # Filter Logic
    df_filtered = df.copy()
    if selected_dest != "All Destinations" and dest_col:
        df_filtered = df_filtered[df_filtered[dest_col].astype(str) == selected_dest]
    
    if selected_consignee != "All Consignees" and consignee_col:
        df_filtered = df_filtered[df_filtered[consignee_col].astype(str) == selected_consignee]

    st.markdown("---")

    # -------------------------------------------------------------
    # 3. HIGH AGING SEPARATION (0-24 Hrs vs >24 Hrs)
    # -------------------------------------------------------------
    df_normal_aging = df_filtered[df_filtered['HH_Numeric'] <= 24]      # 1 to 24 Hours
    df_high_aging = df_filtered[df_filtered['HH_Numeric'] > 24]        # Critical (>24 Hours)

    # Top KPI Summary Cards
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Shipments", f"{len(df_filtered):,}")
    m2.metric("Normal Aging (0 - 24 Hrs)", f"{len(df_normal_aging):,}")
    m3.metric("⚠️ HIGH AGING (> 24 Hrs)", f"{len(df_high_aging):,}", delta_color="inverse")
    
    if pkg_col:
        m4.metric("Total Packages/Boxes", f"{int(df_filtered[pkg_col].sum()):,}")

    st.markdown("---")

    # -------------------------------------------------------------
    # 4. AGING BUCKET TABS
    # -------------------------------------------------------------
    tab_high, tab_normal, tab_all = st.tabs([
        "🔥 CRITICAL: High Aging (> 24 Hours)", 
        "⏱️ Normal Aging (1 to 24 Hours)", 
        "📋 Complete Data Table"
    ])

    # --- TAB 1: HIGH AGING (>24 HRS) ---
    with tab_high:
        st.subheader("⚠️ Priority High Aging Action Panel (> 24 Hours HH)")
        if len(df_high_aging) > 0:
            st.error(f"Attention! Total {len(df_high_aging)} Shipments are pending beyond 24 Hours!")
            
            c1, c2 = st.columns([1, 1])
            with c1:
                # Top Consignees in High Aging
                if consignee_col:
                    high_cons = df_high_aging[consignee_col].value_counts().reset_index().head(10)
                    high_cons.columns = ['Consignee Name', 'High Aging CN Count']
                    fig_high = px.bar(high_cons, x='High Aging CN Count', y='Consignee Name', orientation='h',
                                      title="Top Consignees with High Aging (>24 Hrs)", color='High Aging CN Count',
                                      color_continuous_scale='Reds')
                    st.plotly_chart(fig_high, use_container_width=True)
            
            with c2:
                # Data Table for High Aging
                st.markdown("##### 📌 High Aging Shipments List")
                display_cols = [cn_col]
                if consignee_col: display_cols.append(consignee_col)
                if dest_col: display_cols.append(dest_col)
                if aging_col: display_cols.append(aging_col)
                if pkg_col: display_cols.append(pkg_col)
                
                st.dataframe(df_high_aging[display_cols], height=350, use_container_width=True)
        else:
            st.balloons()
            st.success("Great! No high aging shipments pending beyond 24 hours.")

    # --- TAB 2: NORMAL AGING (1-24 HRS) ---
    with tab_normal:
        st.subheader("⏱️ Shipments within 1 to 24 Hours Aging")
        if len(df_normal_aging) > 0:
            st.info(f"Total {len(df_normal_aging)} Shipments are in the 1-24 Hours timeline.")
            
            display_cols_n = [cn_col]
            if consignee_col: display_cols_n.append(consignee_col)
            if dest_col: display_cols_n.append(dest_col)
            if aging_col: display_cols_n.append(aging_col)
            if pkg_col: display_cols_n.append(pkg_col)
            
            st.dataframe(df_normal_aging[display_cols_n], height=350, use_container_width=True)
        else:
            st.write("No shipments found in 1-24 Hours range.")

    # --- TAB 3: COMPLETE DATA TABLE ---
    with tab_all:
        st.subheader("📋 Filtered Shipment Master View")
        st.dataframe(df_filtered, height=400, use_container_width=True)

else:
    st.info("💡 Kripya operational failure/incoming file upload karein analysis ke liye.")
