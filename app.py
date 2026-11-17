
import streamlit as st

# ---------------- PAGE CONFIGURATION ----------------
st.set_page_config(
    page_title="ElectroMind AI",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------- SESSION STATE ----------------
if "messages" not in st.session_state:
    st.session_state.messages = []

if "project_started" not in st.session_state:
    st.session_state.project_started = False

# ---------------- CUSTOM DESIGN ----------------
st.markdown("""
<style>
.stApp {
    background-color: #0b1120;
    color: #ffffff;
}

.main-title {
    font-size: 38px;
    font-weight: 800;
    color: #38bdf8;
}

.subtitle {
    color: #94a3b8;
    font-size: 16px;
}

div[data-testid="stChatMessage"] {
    border: 1px solid #263449;
    border-radius: 12px;
    padding: 12px;
}

.stButton button {
    border-radius: 10px;
}
</style>
""", unsafe_allow_html=True)

# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.markdown("# ⚡ ElectroMind AI")
    st.caption("Your Electronic Engineering Assistant")

    st.divider()

    st.markdown("### Navigation")
    st.info("💬 Component Recommender")

    st.markdown("### Capabilities")
    st.write("• AI Project Analysis")
    st.write("• Component Recommendations")
    st.write("• Alternative Components")
    st.write("• Wiring Assistance")
    st.write("• Budget Optimization")
    st.write("• Technical Specifications")

    st.divider()

    if st.button("🗑️ New Conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.project_started = False
        st.rerun()

    st.caption("ElectroMind AI | Version 1.0")

# ---------------- MAIN HEADER ----------------
st.markdown(
    '<div class="main-title">⚡ ElectroMind AI</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">AI-Powered Electronic Component Recommender</div>',
    unsafe_allow_html=True
)

st.divider()

# ---------------- WELCOME SCREEN ----------------
if not st.session_state.messages:
    st.markdown("## Welcome, Engineer!")

    st.write(
        "Describe your electronics project. "
        "I'll understand your requirements, ask relevant questions "
        "and help you select the most suitable components."
    )

    st.markdown("### What can I help you with?")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.info("🔧 Component Selection")

    with col2:
        st.info("⚡ Circuit & Wiring")

    with col3:
        st.info("💰 Budget Optimization")

    st.markdown("### Start with your project idea")

# ---------------- CHAT HISTORY ----------------
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ---------------- CHAT INPUT ----------------
user_input = st.chat_input(
    "Describe your electronics project..."
)

if user_input:
    st.session_state.messages.append({
        "role": "user",
        "content": user_input
    })

    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        response = (
            "Interesting project! I'm ready to understand your requirements.\n\n"
            "In the next development stage, we'll connect the AI engine "
            "to ask adaptive technical questions and generate component recommendations."
        )
        st.markdown(response)

    st.session_state.messages.append({
        "role": "assistant",
        "content": response
    })
