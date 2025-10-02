import os
import json
import requests
import pandas as pd
import streamlit as st

# Config: prefer secrets -> env -> default
API_BASE = st.secrets.get("API_BASE", os.getenv("API_BASE", "http://localhost:8000/api"))

st.set_page_config(
    page_title="DS Platform (Gemini) - Full Pipeline", 
    page_icon="🤖", 
    layout="wide"
)
st.title("🤖 Data Science Platform - Upload, Analysis, Preprocessing & Visualization")

# ---------- Helpers ----------
def upload_dataset(file, description: str):
    files = {"file": (file.name, file.getvalue(), file.type or "application/octet-stream")}
    data = {"description": description}
    return requests.post(f"{API_BASE}/upload/dataset", files=files, data=data, timeout=120)

def list_datasets():
    return requests.get(f"{API_BASE}/upload/datasets", timeout=60)

def analysis_summary(dataset_id: str):
    return requests.post(f"{API_BASE}/analysis/{dataset_id}/summary", timeout=300)

def preprocessing_profile(dataset_id: str):
    return requests.post(f"{API_BASE}/preprocessing/{dataset_id}/profile", timeout=300)

def preprocessing_apply(dataset_id: str, custom_plan: dict | None, persist: bool, persist_mode: str):
    url = f"{API_BASE}/preprocessing/{dataset_id}/apply"
    params = {"persist": str(persist).lower(), "persist_mode": persist_mode}
    return requests.post(url, json=custom_plan, params=params, timeout=300)

def viz_suggest_simple(dataset_id: str):
    return requests.get(f"{API_BASE}/visualization/{dataset_id}/suggest", timeout=60)

def viz_render_simple(dataset_id: str, specs: list, points: int | None):
    url = f"{API_BASE}/visualization/{dataset_id}/render"
    params = {"points": points} if points else {}
    return requests.post(url, json=specs, params=params, timeout=180)

def df_from_records(records: list) -> pd.DataFrame:
    try:
        return pd.DataFrame(records)
    except Exception:
        return pd.DataFrame()

def df_from_desc(desc_dict: dict) -> pd.DataFrame:
    try:
        df = pd.DataFrame(desc_dict)
        return df.T if not df.empty else df
    except Exception:
        return pd.DataFrame()

# ---------- Sidebar ----------
with st.sidebar:
    st.header("⚙️ Settings")
    st.caption("Backend API")
    st.text_input("API_BASE", value=API_BASE, key="api_base_display", disabled=True)
    
    if st.button("🔍 Check LLM Status"):
        try:
            r = requests.get(f"{API_BASE}/llm/status", timeout=30)
            if r.ok:
                status = r.json()
                st.success("✅ LLM Connected")
                st.json(status)
            else:
                st.error(f"❌ LLM Error: {r.status_code}")
        except Exception as e:
            st.error(f"❌ Connection Error: {str(e)}")
    
    st.divider()
    st.markdown("### 📋 Pipeline Steps")
    st.markdown("1. **Upload** dataset")
    st.markdown("2. **Select** dataset")
    st.markdown("3. **Analyze** with AI summary")
    st.markdown("4. **Preprocess** data")
    st.markdown("5. **Visualize** with charts")

# ---------- Main Content ----------

# ---------- 1. Upload ----------
st.header("1️⃣ Upload Dataset")
with st.container():
    col1, col2 = st.columns([2, 1])
    
    with col1:
        up_file = st.file_uploader(
            "Choose your dataset file",
            type=["csv", "xlsx", "xls", "json", "tsv"],
            help="Supported formats: CSV, Excel (XLSX/XLS), JSON, TSV"
        )
        description = st.text_area(
            "Dataset description *",
            placeholder="Describe your dataset purpose, target variable (if any), and any context...",
            height=100,
            max_chars=1000,
            help="Minimum 5 characters required"
        )
    
    with col2:
        st.markdown("### Upload Info")
        if up_file:
            st.info(f"**File:** {up_file.name}")
            st.info(f"**Size:** {up_file.size:,} bytes")
            st.info(f"**Type:** {up_file.type}")
        
        upload_disabled = not (up_file and description.strip() and len(description.strip()) >= 5)
        if st.button("📤 Upload Dataset", use_container_width=True, disabled=upload_disabled):
            with st.spinner("Uploading..."):
                try:
                    resp = upload_dataset(up_file, description.strip())
                    if resp.ok:
                        info = resp.json()
                        st.session_state["last_upload"] = info
                        st.success(f"✅ Uploaded: **{info.get('filename')}**")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error(f"❌ Upload failed: {resp.status_code} - {resp.text}")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

st.divider()

# ---------- 2. Select Dataset ----------
st.header("2️⃣ Select Dataset")
ds_list = []
try:
    r = list_datasets()
    if r.ok:
        ds_list = r.json()
    else:
        st.warning(f"Could not fetch datasets: {r.status_code}")
except Exception as e:
    st.warning(f"Error loading datasets: {str(e)}")

if ds_list:
    # Create options for selectbox
    options = {}
    for d in ds_list:
        label = f"📄 {d['filename']} ({d['id'][:8]}...) - {d['file_type'].upper()}"
        options[label] = d
    
    # Find default selection based on last upload
    default_idx = 0
    if "last_upload" in st.session_state:
        lu_id = st.session_state["last_upload"]["id"]
        for i, (label, d) in enumerate(options.items()):
            if d["id"] == lu_id:
                default_idx = i
                break
    
    selected_label = st.selectbox(
        "Choose a dataset to work with:",
        options=list(options.keys()),
        index=default_idx,
        help="Select from uploaded datasets"
    )
    selected_ds = options.get(selected_label)
    
    if selected_ds:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📊 File Size", f"{selected_ds.get('file_size', 0):,} bytes")
        with col2:
            st.metric("📅 Upload Date", selected_ds.get('upload_date', '').split('T')[0])
        with col3:
            st.metric("🏷️ File Type", selected_ds.get('file_type', '').upper())
        
        with st.expander("📝 Dataset Description"):
            st.write(selected_ds.get('description', 'No description provided'))
else:
    selected_ds = None
    st.info("📥 No datasets found. Please upload a dataset first.")

st.divider()

# ---------- 3. Analysis Summary ----------
st.header("3️⃣ Brief Analysis Summary")
if selected_ds:
    if st.button("🧠 Generate AI Summary", use_container_width=True):
        with st.spinner("🤖 Analyzing dataset..."):
            try:
                resp = analysis_summary(selected_ds["id"])
                if not resp.ok:
                    st.error(f"❌ Analysis failed: {resp.status_code} - {resp.text}")
                else:
                    data = resp.json()
                    st.session_state["analysis_data"] = data
                    st.success("✅ Analysis complete!")
                    st.rerun()
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
    
    # Display analysis results if available
    if "analysis_data" in st.session_state:
        data = st.session_state["analysis_data"]
        
        # Dataset Meta Info
        st.subheader("📊 Dataset Overview")
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            shape = tuple(data['dataset'].get('shape', [0, 0]))
            st.metric("Rows", f"{shape[0]:,}")
        with m2:
            st.metric("Columns", f"{shape[1]:,}")
        with m3:
            st.metric("File Size", f"{data['dataset']['file_size']:,} bytes")
        with m4:
            st.metric("File Type", data['dataset']['file_type'].upper())
        
        # Data Samples
        st.subheader("🔍 Data Samples")
        tab1, tab2, tab3 = st.tabs(["📄 First 10", "📄 Last 10", "🎲 Random 10"])
        
        with tab1:
            df_head = df_from_records(data["samples"]["head10"])
            if not df_head.empty:
                st.dataframe(df_head, use_container_width=True)
            else:
                st.info("No data to display")
        
        with tab2:
            df_tail = df_from_records(data["samples"]["tail10"])
            if not df_tail.empty:
                st.dataframe(df_tail, use_container_width=True)
            else:
                st.info("No data to display")
        
        with tab3:
            df_rand = df_from_records(data["samples"]["random10"])
            if not df_rand.empty:
                st.dataframe(df_rand, use_container_width=True)
            else:
                st.info("No data to display")
        
        # Descriptive Statistics
        st.subheader("📈 Descriptive Statistics")
        stat_tab1, stat_tab2 = st.tabs(["🔢 Numeric", "📝 Categorical"])
        
        with stat_tab1:
            df_num = df_from_desc(data["describe"]["numeric"])
            if not df_num.empty:
                st.dataframe(df_num, use_container_width=True)
            else:
                st.info("No numeric columns found")
        
        with stat_tab2:
            df_obj = df_from_desc(data["describe"]["object"])
            if not df_obj.empty:
                st.dataframe(df_obj, use_container_width=True)
            else:
                st.info("No categorical columns found")
        
        # AI Summary
        st.subheader("🤖 AI-Generated Summary")
        summary_text = data["llm_summary"]["text"]
        st.markdown(summary_text)
        
        if data["llm_summary"].get("bullets"):
            st.markdown("**Key Insights:**")
            for bullet in data["llm_summary"]["bullets"]:
                st.markdown(f"• {bullet}")
else:
    st.info("👆 Please select a dataset to enable analysis.")

st.divider()

# ---------- 4. Preprocessing ----------
st.header("4️⃣ Data Preprocessing")

if selected_ds:
    tab1, tab2 = st.tabs(["🔍 Profile Data", "🛠️ Apply Preprocessing"])
    
    with tab1:
        if st.button("📊 Profile Preprocessing Needs", use_container_width=True):
            with st.spinner("🔍 Profiling data quality..."):
                try:
                    resp = preprocessing_profile(selected_ds["id"])
                    if not resp.ok:
                        st.error(f"❌ Profiling failed: {resp.status_code} - {resp.text}")
                    else:
                        prof = resp.json()
                        st.session_state["preprocessing_profile"] = prof
                        st.success("✅ Profiling complete!")
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
        
        # Display profile results
        if "preprocessing_profile" in st.session_state:
            prof = st.session_state["preprocessing_profile"]
            
            st.subheader("🎯 Suggested Preprocessing Plan")
            st.json(prof["profile"]["plan"])
            
            st.subheader("📋 Column Analysis")
            cols_df = pd.DataFrame(prof["profile"]["columns"])
            view_cols = [
                "name", "dtype", "non_null", "missing", "missing_pct", "unique",
                "suggested_role", "suggested_imputation", "suggested_encoding",
                "suggested_scaling", "outlier_count_iqr", "outlier_count_z"
            ]
            view_cols = [c for c in view_cols if c in cols_df.columns]
            st.dataframe(cols_df[view_cols], use_container_width=True)
            
            st.subheader("⚠️ Outliers Detected")
            outlier_data = []
            for col, details in prof["profile"]["outliers"].items():
                outlier_data.append({
                    "column": col,
                    "iqr_outliers": details["iqr_count"],
                    "zscore_outliers": details["zscore_count"],
                })
            
            if outlier_data:
                outlier_df = pd.DataFrame(outlier_data)
                outlier_df = outlier_df.sort_values(["iqr_outliers", "zscore_outliers"], ascending=False)
                st.dataframe(outlier_df, use_container_width=True)
            else:
                st.info("No outliers detected")
    
    with tab2:
        st.markdown("### Customize Preprocessing Plan (Optional)")
        override_text = st.text_area(
            "Custom plan JSON (leave empty for suggested plan)",
            value="",
            placeholder='{"drops": ["id"], "imputations": {"age": {"strategy": "median"}}, "encodings": {"city": {"method": "onehot"}}, "scalings": {"income": {"method": "standard"}}, "datetime_parse": ["purchase_date"]}',
            height=150,
            help="Edit the JSON plan or leave empty to use suggested plan"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            persist = st.checkbox("💾 Save processed data to disk", value=False)
        with col2:
            persist_mode = st.selectbox(
                "Save mode",
                ["versioned", "overwrite"],
                index=0,
                disabled=not persist,
                help="Versioned keeps original, overwrite replaces it"
            )
        
        if st.button("🛠️ Apply Preprocessing", use_container_width=True):
            with st.spinner("⚙️ Processing data..."):
                try:
                    custom_plan = None
                    if override_text.strip():
                        try:
                            custom_plan = json.loads(override_text)
                        except json.JSONDecodeError as e:
                            st.error(f"❌ Invalid JSON: {str(e)}")
                            st.stop()
                    
                    resp = preprocessing_apply(selected_ds["id"], custom_plan, persist, persist_mode)
                    if not resp.ok:
                        st.error(f"❌ Processing failed: {resp.status_code} - {resp.text}")
                    else:
                        data = resp.json()
                        st.success("✅ Preprocessing complete!")
                        
                        # Show results
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Rows Before", data["shape_before"][0])
                        with col2:
                            st.metric("Rows After", data["shape_after"][0])
                        with col3:
                            st.metric("Cols Before", data["shape_before"][1])
                        with col4:
                            st.metric("Cols After", data["shape_after"][1])
                        
                        if data["persisted"]:
                            st.info(f"💾 Saved to: {data['saved_path']}")
                            if data.get("version_path"):
                                st.info(f"🔄 Version: {data['version_path']}")
                        
                        st.subheader("📋 Applied Plan")
                        st.json(data["applied_plan"])
                        
                        st.subheader("👀 Preview (First 50 Rows)")
                        preview_df = pd.DataFrame(data["rows_transformed_preview"])
                        if not preview_df.empty:
                            st.dataframe(preview_df, use_container_width=True)
                        else:
                            st.info("No preview data available")
                            
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
else:
    st.info("👆 Please select a dataset to enable preprocessing.")

st.divider()

# ---------- 5. Visualization (Simple) ----------
st.header("5️⃣ Visualization (Simple)")

if selected_ds:
    # Controls
    c1, c2 = st.columns([1, 2])
    with c1:
        get_btn = st.button("🎨 Get Suggestions", use_container_width=True)
    with c2:
        points = st.slider(
            "Max points (sample for plotting)",
            min_value=5, max_value=10000, value=15, step=500,
            help="Sampling helps render faster on large datasets."
        )

    if get_btn:
        with st.spinner("Asking AI for chart suggestions..."):
            try:
                r = viz_suggest_simple(selected_ds["id"])
                if r.ok:
                    suggestions = r.json().get("suggestions", [])
                    # Keep only minimal fields
                    simple_specs = []
                    for s in suggestions:
                        simple_specs.append({
                            "title": s.get("title"),
                            "type": s.get("type"),
                            "x": s.get("x"),
                            "y": s.get("y"),
                            "hue": s.get("hue"),
                        })
                    st.session_state["simple_viz_specs"] = simple_specs[:6]  # cap to 6 charts for simplicity
                    st.success(f"Got {len(simple_specs[:6])} suggestions")
                else:
                    st.error(f"{r.status_code}: {r.text}")
            except Exception as e:
                st.error(str(e))

    specs = st.session_state.get("simple_viz_specs", [])
    if specs:
        # Render directly
        if st.button("🖼️ Render Charts", use_container_width=True):
            with st.spinner("Rendering charts..."):
                try:
                    r = viz_render_simple(selected_ds["id"], specs, points)
                    if not r.ok:
                        st.error(f"{r.status_code}: {r.text}")
                    else:
                        data = r.json()
                        images = data.get("images", [])
                        if not images:
                            st.info("No charts returned")
                        else:
                            st.success(f"✅ Generated {len(images)} chart(s)")
                            for i, item in enumerate(images):
                                title = item.get("title") or item.get("type") or f"Chart {i+1}"
                                st.markdown(f"### {title}")
                                if "img_base64" in item:
                                    st.image("data:image/png;base64," + item["img_base64"], use_container_width=True)
                                else:
                                    st.warning(f"Could not render: {item.get('error','Unknown error')}")
                                if i < len(images) - 1:
                                    st.divider()
                except Exception as e:
                    st.error(str(e))

        # Show a quick, readable view of the JSON used
        with st.expander("View chart JSON"):
            st.json(specs)
    else:
        st.info("Click 'Get Suggestions' to fetch simple chart ideas.")
else:
    st.info("Select a dataset to enable visualization.")

# ---------- Footer ----------
st.divider()
with st.container():
    col1, col2, col3 = st.columns(3)
    with col1:
        st.caption("🔧 **Backend API:**")
        st.caption(f"`{API_BASE}`")
    with col2:
        st.caption("🤖 **AI Service:**")
        st.caption("Google Gemini 2.0 Flash")
    with col3:
        st.caption("📊 **Features:**")
        st.caption("Upload • Analyze • Preprocess • Visualize")
