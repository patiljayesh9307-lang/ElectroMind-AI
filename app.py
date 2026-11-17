from modules.recommender import get_recommendation_summary

from modules.component_database import (
    get_all_components,
    search_components
)
import streamlit as st
from google import genai
from google.genai import types

# ==================================================
# ELECTROMIND AI - VERSION 1.1
# Gemini-powered Electronics Assistant
# ==================================================

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

if "api_error" not in st.session_state:
    st.session_state.api_error = ""

# ---------------- CONFIGURATION ----------------

MODEL_NAME = "gemini-3.5-flash-lite"

SYSTEM_INSTRUCTION = """
You are ElectroMind AI, an expert electronics engineering assistant.

YOUR DOMAIN:
You ONLY handle electronics and electrical hardware projects,
including embedded systems, microcontrollers, sensors, actuators,
power supplies, circuits, PCB components and communication modules.

YOUR MAIN TASK:
Understand the user's project requirements through an adaptive
conversation and eventually recommend suitable electronic components.

CONVERSATION RULES:

1. Start by understanding the user's project idea.
2. Ask ONE useful question at a time.
3. Never ask questions whose answers the user has already provided.
4. Adapt your next question based on previous answers.
5. Ask about relevant requirements such as:
   - Project purpose
   - Budget and currency
   - Existing components
   - Controller preference
   - Sensors and actuators
   - Power supply
   - Operating environment
   - Required accuracy and performance
   - Connectivity
   - Size constraints
   - User's experience level
6. Skip irrelevant questions.
7. Do not force a fixed number of questions.
8. Once sufficient information is collected, summarize the requirements
   and ask the user to confirm before proceeding to recommendations.

RECOMMENDATION RULES:

When enough information is available:
- Recommend suitable components.
- Explain why each component is selected.
- Suggest alternatives.
- Explain operating voltage and current requirements.
- Explain interfaces and pin connections.
- Estimate the project cost only when pricing information is available.
- Clearly identify assumptions and missing information.

IMPORTANT TECHNICAL SAFETY:

- Never invent datasheet specifications.
- Never claim electrical compatibility without checking it.
- Distinguish logic voltage from supply voltage.
- Mention current and power supply limitations.
- Never suggest connecting motors directly to microcontroller GPIO pins.
- Warn users about mains voltage, high voltage, batteries and
  other potentially dangerous circuits.
- Do not present unverified wiring instructions as safe.
- Recommend qualified supervision for hazardous circuits.

COMMUNICATION STYLE:

- Friendly and professional.
- Beginner-friendly explanations.
- Use clear headings and bullet points when useful.
- Avoid unnecessarily long answers.
- Ask only one main follow-up question per response.

If a user asks something unrelated to electronics, politely explain
that ElectroMind AI currently specializes in electronics projects.
"""

# ---------------- CUSTOM CSS ----------------

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

# ---------------- GEMINI CLIENT ----------------

def get_gemini_client():
    api_key = st.secrets.get("GEMINI_API_KEY", "")

    if not api_key:
        raise ValueError(
            "Gemini API key is missing. "
            "Please configure GEMINI_API_KEY in Streamlit Secrets."
        )

    return genai.Client(api_key=api_key)


def generate_ai_response(history, user_input):
    client = get_gemini_client()

    # Build conversation context from previous messages.
    conversation = []

    for message in history:
        role = "User" if message["role"] == "user" else "ElectroMind AI"
        conversation.append(
            f"{role}: {message['content']}"
        )

    conversation.append(f"User: {user_input}")

    prompt = "\n\n".join(conversation)

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.5,
            max_output_tokens=800
        )
    )

    if not response.text:
        raise ValueError("Gemini returned an empty response.")

    return response.text


# ---------------- SIDEBAR ----------------

with st.sidebar:

    st.markdown("# ⚡ ElectroMind AI")
    st.caption("Your Electronic Engineering Assistant")

    st.divider()

    st.markdown("### Navigation")
    st.info("💬 Component Recommender")

    st.markdown("### Capabilities")

    st.write("• AI Project Analysis")
    st.write("• Smart Component Selection")
    st.write("• Alternative Components")
    st.write("• Wiring Assistance")
    st.write("• Budget Optimization")
    st.write("• Technical Specifications")

    st.divider()

    st.markdown("### AI Engine")
    st.success("Gemini AI Connected")

    st.caption(f"Model: {MODEL_NAME}")

    st.divider()

    if st.button("🗑️ New Conversation", use_container_width=True):

        st.session_state.messages = []
        st.session_state.project_started = False
        st.session_state.api_error = ""

        st.rerun()

    st.caption("ElectroMind AI | Version 1.1")


# ---------------- MAIN HEADER ----------------

st.markdown(
    '<div class="main-title">⚡ ElectroMind AI</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'AI-Powered Electronic Component Recommender'
    '</div>',
    unsafe_allow_html=True
)

st.divider()


# ---------------- WELCOME SCREEN ----------------

if not st.session_state.messages:

    st.markdown("## Welcome, Engineer! 👋")

    st.write(
        "Tell me about your electronics project. "
        "I'll understand your requirements, ask technical "
        "questions and help you choose suitable components."
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


# ---------------- DISPLAY CHAT HISTORY ----------------

for message in st.session_state.messages:

    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# ---------------- CHAT INPUT ----------------

user_input = st.chat_input(
    "Describe your electronics project..."
)

if user_input:

    # Display and save user message.

    st.session_state.messages.append({
        "role": "user",
        "content": user_input
    })

    st.session_state.project_started = True

    with st.chat_message("user"):
        st.markdown(user_input)

    # Generate Gemini response.

    with st.chat_message("assistant"):

        with st.spinner("ElectroMind AI is analysing your requirements..."):

            try:

                response = generate_ai_response(
                    st.session_state.messages[:-1],
                    user_input
                )

                st.markdown(response)

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response
                })

                st.session_state.api_error = ""

            except Exception as error:

                error_message = str(error)

                st.error(
                    "Sorry! I couldn't generate a response. "
                    "Please check the details below."
                )

                if "API key is missing" in error_message:
                    st.warning(
                        "Please configure GEMINI_API_KEY "
                        "in Streamlit Secrets."
                    )

                elif "429" in error_message or "RESOURCE_EXHAUSTED" in error_message:
                    st.warning(
                        "Gemini API usage limit reached. "
                        "Please check your API quota and try again later."
                    )

                elif "403" in error_message or "PERMISSION_DENIED" in error_message:
                    st.warning(
                        "API access was denied. Check your API key "
                        "and model access in Google AI Studio."
                    )

                else:
                    st.caption(
                        "Technical error: " + error_message[:500]
                    )

                # Remove failed user message so it can be retried.
                st.session_state.messages.pop()

                st.session_state.api_error = error_message

# Component Database Test
st.sidebar.divider()
st.sidebar.subheader("Database Test")

components = get_all_components()
st.sidebar.write(f"Total components: {len(components)}")

search_query = st.sidebar.text_input("Search components")

if search_query:
    results = search_components(search_query)

    for component in results:
        st.sidebar.write(component["name"])


# Recommendation Matching Test

st.sidebar.divider()
st.sidebar.subheader("Recommendation Test")

test_names = [
    "ESP32 Development Board",
    "DHT22 Sensor",
    "Arduino Uno",
    "Unknown Component"
]

if st.sidebar.button("Test Recommendation Matching"):
    result = get_recommendation_summary(test_names)

    st.sidebar.write(
        f"Verified: {result['total_verified']}"
    )

    st.sidebar.write(
        f"Unverified: {result['total_unverified']}"
    )

    st.sidebar.write("Verified components:")

    for component in result["details"]["verified_components"]:
        st.sidebar.write("✅ " + component["name"])

    st.sidebar.write("Unverified components:")

    for name in result["details"]["unverified_components"]:
        st.sidebar.write("⚠️ " + name)
