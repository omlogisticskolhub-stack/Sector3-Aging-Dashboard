import streamlit as st
import pandas as pd
import plotly.express as px

# Page Setup
st.set_page_config(
    page_title="Sector 3 - Operations & Aging Dashboard",
    page_icon="🚚",
    layout="wide"
)

# Title & Subtitle
st.title("🚚 Sector 3 - Operations & Aging Analysis Dashboard")
st.caption("Sector 3 Operations Tracker for Own Pickup & FOC, Transshipment, and Pending Delivery")

# -------------------------------------------------------------
# 1. FILE UPLOAD SECTION (3 SEPARATE FILES FOR SECTOR 3)
# -------------------------------------------------------------
st.markdown("### 📤 Sector 3 Data Upload Panel")
col1, col2, col3 = st.columns(3)

with col1:
    file_pickup = st.file_uploader("1. Own Pickup & FOC File", type=["xlsx", "csv"], key="f1")

with col2:
    file_trans = st.file_uploader("2. Transshipment Aging File", type=["xlsx", "csv"], key="f2")

with col3:
    file_deliv = st.file_uploader("3. Pending Delivery File", type=["xlsx", "csv"], key="f3")

st.markdown("---")

def load_data(file):
    if file is not None:
        if file.name.endswith('.csv'):
            return pd.read_csv(file)
        else:
            return pd.read_excel(file)
    return None

# Tabs Selection for Sector 3
tab1, tab2, tab3 = st.tabs([
    "🚚 Sector 3: Own Pickup & FOC", 
    "🔄 Sector 3: Transshipment Aging", 
    "📦 Sector 3: Pending Delivery"
])

# -------------------------------------------------------------
# TAB 1: OWN PICKUP & FOC
# -------------------------------------------------------------
with tab1:
    st.subheader("Sector 3 - Own Pickup & FOC Analysis (Prefix: 814 / 809)")
    df1 = load_data(file_pickup)
    
    if df1 is not None:
        cn_col = next((c for c in df1.columns if 'CN' in c.upper() or 'DOCKET' in c.upper()), df1.columns[0])
        manual_col = next((c for c in df1.columns if 'MANUAL' in c.upper()), df1.columns[1] if len(df1.columns)>1 else df1.columns[0])
        type_col = next((c for c in df1.columns if 'TYPE' in c.upper() or 'FOC' in c.upper() or 'REASON' in c.upper()), None)
        
        df1['Hub Prefix'] = df1[cn_col].astype(str).str[:3]
        
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total Unique CNs", f"{len(df1):,}")
        k2.metric("Dankuni (814)", f"{len(df1[df1['Hub Prefix']=='814']):,}")
        k3.metric("Dhulagadh (809)", f"{len(df1[df1['Hub Prefix']=='809']):,}")
        
        foc_cnt = len(df1[df1[type_col].astype(str).str.contains('FOC|FREE', case=False, na=False)]) if type_col else 0
        k4.metric("FOC Count", f"{foc_cnt:,}")
        
        st.markdown("---")
        c1, c2 = st.columns([1, 1])
        with c1:
            fig_hub = px.pie(df1, names='Hub Prefix', title="Hub Prefix Breakdown", hole=0.4)
            st.plotly_chart(fig_hub, use_container_width=True)
        with c2:
            st.markdown("##### 📌 Sector 3: CN & Manual Number Extraction")
            show_c = [cn_col, manual_col, 'Hub Prefix']
            if type_col: show_c.append(type_col)
            st.dataframe(df1[show_c], height=350, use_container_width=True)
    else:
        st.info("💡 Kripya Own Pickup & FOC file upload karein.")

# -------------------------------------------------------------
# TAB 2: TRANSSHIPMENT AGING
# -------------------------------------------------------------
with tab2:
    st.subheader("Sector 3 - Transshipment Dwell Aging Summary")
    df2 = load_data(file_trans)
    
    if df2 is not None:
        cn_col2 = next((c for c in df2.columns if 'CN' in c.upper() or 'DOCKET' in c.upper()), df2.columns[0])
        manual_col2 = next((c for c in df2.columns if 'MANUAL' in c.upper()), df2.columns[1] if len(df2.columns)>1 else df2.columns[0])
        todist_col = next((c for c in df2.columns if 'TODIST' in c.upper() or 'DEST' in c.upper() or 'HUB' in c.upper()), None)
        aging_col = next((c for c in df2.columns if 'AGING' in c.upper() or 'HOUR' in c.upper() or 'DAY' in c.upper()), None)
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Transshipment Count", f"{len(df2):,}")
        if aging_col:
            m2.metric("Max Aging", f"{df2[aging_col].max()}")
        m3.metric("Destination Hubs", f"{df2[todist_col].nunique()}" if todist_col else "N/A")
        
        st.markdown("---")
        d1, d2 = st.columns([1, 1])
        with d1:
            if todist_col:
                h_sum = df2[todist_col].value_counts().reset_index()
                h_sum.columns = ['Destination Hub (TODIST)', 'Pending CN Count']
                fig_trans = px.bar(h_sum.head(10), x='Pending CN Count', y='Destination Hub (TODIST)', 
                                   orientation='h', title="Top Destination Hub Load", color='Pending CN Count')
                st.plotly_chart(fig_trans, use_container_width=True)
        with d2:
            st.markdown("##### 📌 Sector 3: Transshipment CN & Manual Details")
            show_c2 = [cn_col2, manual_col2]
            if todist_col: show_c2.append(todist_col)
            if aging_col: show_c2.append(aging_col)
            st.dataframe(df2[show_c2], height=350, use_container_width=True)
    else:
        st.info("💡 Kripya Transshipment Aging file upload karein.")

# -------------------------------------------------------------
# TAB 3: PENDING DELIVERY
# -------------------------------------------------------------
with tab3:
    st.subheader("Sector 3 - Pending Delivery Analysis")
    df3 = load_data(file_deliv)
    
    if df3 is not None:
        cn_col3 = next((c for c in df3.columns if 'CN' in c.upper() or 'DOCKET' in c.upper()), df3.columns[0])
        manual_col3 = next((c for c in df3.columns if 'MANUAL' in c.upper()), df3.columns[1] if len(df3.columns)>1 else df3.columns[0])
        reason_col = next((c for c in df3.columns if 'REASON' in c.upper() or 'UNDLVRD' in c.upper()), None)
        pkg_col = next((c for c in df3.columns if 'PKG' in c.upper() or 'BOX' in c.upper()), None)
        
        p1, p2, p3 = st.columns(3)
        p1.metric("Pending Deliveries", f"{len(df3):,}")
        p2.metric("Total Packages (Boxes)", f"{df3[pkg_col].sum():,}" if pkg_col else "N/A")
        blank_r = df3[reason_col].isna().sum() if reason_col else 0
        p3.metric("Missing UNDLVRD Reason", f"{blank_r:,}")
        
        st.markdown("---")
        e1, e2 = st.columns([1, 1])
        with e1:
            if reason_col:
                r_sum = df3[reason_col].fillna("No Reason Filled").value_counts().reset_index()
                r_sum.columns = ['Reason', 'Count']
                fig_r = px.bar(r_sum.head(8), x='Count', y='Reason', orientation='h', 
                               title="Undelivered Reasons Summary", color='Count', color_continuous_scale='Reds')
                st.plotly_chart(fig_r, use_container_width=True)
        with e2:
            st.markdown("##### 📌 Sector 3: Pending Delivery CN & Manual Details")
            show_c3 = [cn_col3, manual_col3]
            if reason_col: show_c3.append(reason_col)
            if pkg_col: show_c3.append(pkg_col)
            st.dataframe(df3[show_c3], height=350, use_container_width=True)
    else:
        st.info("💡 Kripya Pending Delivery file upload karein.")
