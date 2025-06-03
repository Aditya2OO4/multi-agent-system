import streamlit as st
import requests
import json
from streamlit_ace import st_ace

# Configuration
API_BASE_URL = "http://localhost:8000"

st.set_page_config(
    page_title="Multi-Agent System Interface",
    page_icon="🤖",
    layout="wide"
)

st.title("Multi-Format Autonomous AI System")
st.markdown("Upload documents for processing by our AI agents")

# Sidebar for system info
st.sidebar.header("System Status")
if st.sidebar.button("Check API Status"):
    try:
        response = requests.get(f"{API_BASE_URL}/")
        if response.status_code == 200:
            st.sidebar.success("API is running ✅")
        else:
            st.sidebar.error(f"API error: {response.status_code}")
    except requests.exceptions.ConnectionError:
        st.sidebar.error("API not reachable. Is the server running?")

# File upload section
upload_tab, history_tab = st.tabs(["Upload Documents", "Request History"])

with upload_tab:
    st.subheader("Upload a Document")
    input_type = st.radio(
        "Select document type:",
        ("Email", "JSON", "PDF"),
        horizontal=True
    )

    uploaded_file = st.file_uploader(
        f"Upload {input_type} file",
        type=["txt", "json", "pdf"] if input_type != "JSON" else ["json"]
    )

    content_text = st.text_area(
        "Or paste content directly:",
        height=150,
        placeholder="Paste email content, JSON, or PDF text here..."
    )

    if st.button("Process Document"):
        if not uploaded_file and not content_text:
            st.error("Please upload a file or enter content")
            st.stop()

        with st.spinner("Processing with AI agents..."):
            try:
                if uploaded_file:
                    files = {"file": (uploaded_file.name, uploaded_file, "multipart/form-data")}
                    params = {"input_type": input_type.lower()}
                    response = requests.post(
                        f"{API_BASE_URL}/process",
                        params=params,
                        files=files
                    )
                else:
                    data = {"content": content_text, "input_type": input_type.lower()}
                    response = requests.post(
                        f"{API_BASE_URL}/process",
                        json=data
                    )

                if response.status_code == 200:
                    result = response.json()
                    request_id = result["request_id"]
                    st.success("Document processed successfully!")
                    st.session_state.current_request = result
                    st.session_state.current_request_id = request_id
                else:
                    st.error(f"Error processing document: {response.text}")

            except Exception as e:
                st.error(f"An error occurred: {str(e)}")

# Display results if available
if "current_request" in st.session_state:
    req = st.session_state.current_request

    # Add download button for full results
    json_str = json.dumps(req, indent=2)
    st.download_button(
        label="📥 Download Full Results",
        data=json_str,
        file_name=f"results_{st.session_state.current_request_id}.json",
        mime="application/json",
        use_container_width=True
    )

    st.divider()
    st.subheader("Processing Results")

    # Classification results
    with st.expander("Classification Results", expanded=True):
        col1, col2, col3 = st.columns(3)
        col1.metric("Format", req["classification"].get("format", "Unknown"))
        col2.metric("Intent", req["classification"].get("intent", "Unknown").title())
        confidence_value = req['classification'].get('confidence', 0)
        try:
            confidence_float = float(confidence_value)
            col3.metric("Confidence", f"{confidence_float * 100:.1f}%")
        except ValueError:
            col3.metric("Confidence", str(confidence_value))

    # Agent results
    st.subheader("Agent Analysis")
    agent_results = req.get("agent_results", {})

    if agent_results:
        if "error" in agent_results:
            st.error(f"Agent error: {agent_results['error']}")
        else:
            # Display based on input type
            if req["classification"]["format"] == "email":
                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("### Sender Information")
                    sender = agent_results.get("sender", {})
                    st.write(f"**Name:** {sender.get('name', 'Unknown')}")
                    st.write(f"**Email:** {sender.get('email', 'Unknown')}")

                    st.markdown("### Tone Analysis")
                    tone = agent_results.get("tone", "neutral")
                    if tone == "angry":
                        st.error(f"😠 {tone.title()} (Escalation detected)")
                    elif tone == "polite":
                        st.success(f"😊 {tone.title()}")
                    else:
                        st.info(f"😐 {tone.title()}")

                with col2:
                    st.markdown("### Content Analysis")
                    st.write(f"**Urgency:** {agent_results.get('urgency', 'medium').title()}")
                    st.write(f"**Main Issue:** {agent_results.get('issue', 'Not identified')}")
                    st.write(f"**Escalation:** {'Yes' if agent_results.get('is_escalation') else 'No'}")

            elif req["classification"]["format"] == "json":
                # Validation summary
                col1, col2 = st.columns([1, 2])

                with col1:
                    st.markdown("### Validation Summary")
                    is_valid = agent_results.get("valid", False)
                    st.metric("Schema Valid", "✅ Yes" if is_valid else "❌ No")

                    anomalies = agent_results.get("anomalies", [])
                    st.metric("Anomalies Found", len(anomalies),
                             delta_color="off",
                             help="Data type mismatches or format issues")

                    missing = agent_results.get("required_fields_missing", [])
                    st.metric("Missing Fields", len(missing),
                             delta_color="off",
                             help="Required fields not found in JSON")

                    if anomalies:
                        with st.expander("View Anomalies", expanded=False):
                            for issue in anomalies:
                                st.error(f"⚠️ {issue}")

                    if missing:
                        with st.expander("View Missing Fields", expanded=False):
                            for field in missing:
                                st.warning(f"🔍 {field}")

                with col2:
                    st.markdown("### Field Structure")
                    field_types = agent_results.get("field_types", {})

                    def display_schema(data, depth=0):
                        indent = "&nbsp;" * depth * 4
                        if isinstance(data, dict):
                            for key, value in data.items():
                                st.markdown(f"{indent}▸ **{key}**:", unsafe_allow_html=True)
                                display_schema(value, depth + 1)
                        elif isinstance(data, list) and data:
                            if isinstance(data[0], dict):
                                st.markdown(f"{indent}• Array of objects:", unsafe_allow_html=True)
                                display_schema(data[0], depth + 1)
                            else:
                                st.markdown(f"{indent}• Array of: `{data[0]}`", unsafe_allow_html=True)
                        else:
                            st.markdown(f"{indent}→ Type: `{data}`", unsafe_allow_html=True)

                    display_schema(field_types)

                # Raw JSON viewer
                st.markdown("### Full JSON Data")
                st_ace(
                    value=json.dumps(agent_results.get("original_data", {}), indent=2),
                    language="json",
                    theme="chrome",
                    font_size=12,
                    height=300,
                    readonly=True
                )

            elif req["classification"]["format"] == "pdf":
                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("### Document Summary")
                    st.write(f"**Document Type:** {agent_results.get('document_type', 'Unknown')}")

                    amount_exceeds = agent_results.get("amount_exceeds_10k", False)
                    st.metric("Amount > $10k", "✅ Yes" if amount_exceeds else "❌ No")

                    regulations = agent_results.get("regulations_mentioned", [])
                    st.metric("Regulations Found", len(regulations))

                    if regulations:
                        with st.expander("Regulations List", expanded=False):
                            for reg in regulations:
                                st.info(f"📜 {reg}")

                with col2:
                    st.markdown("### Extracted Fields")
                    fields = agent_results.get("fields", {})
                    if fields:
                        for key, value in fields.items():
                            st.write(f"**{key.replace('_', ' ').title()}:** {value}")
                    else:
                        st.info("No specific fields extracted")

    # Actions
    st.subheader("Triggered Actions")
    if req["actions"]:
        for action in req["actions"]:
            st.info(f"✅ {action.replace('_', ' ').title()}")

        # Action results visualization
        action_results = req["action_results"]
        if action_results:
            with st.expander("Action Execution Details", expanded=False):
                for action_name, result in action_results.items():
                    st.write(f"**{action_name.replace('_', ' ').title()}**")
                    st.json(result)
    else:
        st.info("No actions triggered")

    # Raw response
    with st.expander("Raw API Response", expanded=False):
        st_ace(
            value=json.dumps(req, indent=2),
            language="json",
            theme="twilight",
            font_size=12,
            height=400,
            readonly=True
        )

# History tab
with history_tab:
    st.subheader("Recent Processing Requests")
    try:
        response = requests.get(f"{API_BASE_URL}/requests")
        if response.status_code == 200:
            requests_data = response.json()

            if requests_data:
                for req in requests_data:
                    with st.container(border=True):
                        cols = st.columns([1, 2, 1, 1])
                        cols[0].write(f"**ID:** `{req['request_id']}`")
                        cols[1].write(f"**Type:** {req['input_type']}")
                        cols[2].write(f"**Time:** {req['timestamp'][11:19]}")
                        if cols[3].button("Load", key=req['request_id']):
                            response = requests.get(f"{API_BASE_URL}/request/{req['request_id']}")
                            if response.status_code == 200:
                                st.session_state.current_request = response.json()
                                st.session_state.current_request_id = req['request_id']
                                st.experimental_rerun()

            else:
                st.info("No processing requests yet")
        else:
            st.error(f"Error fetching history: {response.status_code}")
    except requests.exceptions.ConnectionError:
        st.error("API not reachable. Start the server with 'python app.py'")

# Footer
st.divider()
st.caption("Multi-Agent System | Built with FastAPI and Streamlit")

# Custom styling
st.markdown("""
<style>
    .stMetric {
        background-color: #0e1117;
        border: 1px solid #2a2d3a;
        border-radius: 10px;
        padding: 15px;
        text-align: center;
    }
    .stMetric label {
        font-size: 0.9rem !important;
        color: #9ea3b0 !important;
    }
    .stMetric div[data-testid="stMetricValue"] {
        font-size: 1.5rem !important;
        font-weight: bold;
    }
    .stButton>button {
        width: 100%;
        background: linear-gradient(45deg, #6a11cb 0%, #2575fc 100%);
        color: white;
        font-weight: bold;
    }
    .stDownloadButton>button {
        background: linear-gradient(45deg, #00c853 0%, #00e676 100%);
        color: white;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)