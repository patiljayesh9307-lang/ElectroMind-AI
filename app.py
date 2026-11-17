import streamlit as st
from google import genai

from modules.component_database import get_all_components
from modules.recommender import match_recommendations
from modules.recommendation_ui import display_recommendations
from modules.bom_calculator import calculate_bom


# ---------------- PAGE SETTINGS ----------------

st.set_page_config(
    page_title="ElectroMind AI",
    page_icon="⚡",
    layout="wide"
)

st.title("⚡ ElectroMind AI")
st.caption("Your AI assistant for electronics and project component recommendations.")

st.markdown("""
<style>
.stApp {
    background-color: #101827;
    color: #f4f7fb;
}
[data-testid="stChatMessage"] {
    background-color: #1b293b;
    border-radius: 12px;
}
.stButton button {
    border-radius: 8px;
}
</style>
""", unsafe_allow_html=True)


# ---------------- API CONNECTION ----------------

try:
    api_key = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=api_key)
except Exception:
    client = None


GEMINI_MODEL = "gemini-3.8-flash"


# ---------------- SESSION STATE ----------------

if "messages" not in st.session_state:
    st.session_state.messages = []

if "recommendation_result" not in st.session_state:
    st.session_state.recommendation_result = None

if "project_started" not in st.session_state:
    st.session_state.project_started = False


# ---------------- COMPONENT DATABASE ----------------

all_components = get_all_components()


# ---------------- AI INSTRUCTIONS ----------------

SYSTEM_PROMPT = """
You are ElectroMind AI, an expert electronics project assistant.

Your job is to help users plan electronics projects and choose suitable
electronic components.

IMPORTANT RULES:

1. Only help with electronics, embedded systems, robotics, IoT,
   sensors, microcontrollers, circuits and related engineering projects.
2. If the user's project details are incomplete, ask ONE useful question
   at a time.
3. Ask about project purpose, budget, controller, sensors, outputs,
   power supply, connectivity, environment and user experience when relevant.
4. Do not ask questions that the user has already answered.
5. Once you have enough information, provide a clear project plan.
6. Recommend exact component names from this catalog whenever suitable:

ESP32 Development Board
Arduino Uno
NodeMCU ESP8266
DHT11 Sensor
DHT22 Sensor
HC-SR04 Ultrasonic Sensor
PIR HC-SR501
LDR Sensor
MQ-2 Gas Sensor
1-Channel Relay Module
4-Channel Relay Module
8-Channel Relay Module
SG90 Servo Motor
L298N Motor Driver
0.96-inch OLED SSD1306
16x2 LCD Display
Active Buzzer
NEO-6M GPS Module
HC-05 Bluetooth Module
INA219 Current Sensor

7. If a suitable component is not in the catalog, you may mention it,
   but clearly say it is not in the current ElectroMind database.
8. Never invent component prices, electrical ratings, pinouts or
   compatibility claims.
9. Explain why each recommended component is needed.
10. Include a practical safety warning when mains voltage, motors,
    batteries, high current or other hazards are involved.
11. Do not claim that a circuit is electrically safe just because
    two components have similar interfaces or voltage labels.
12. Keep answers clear and useful for students and makers.

When ready, format recommendations with component names exactly as
they appear in the catalog so ElectroMind can identify them.
"""


# ---------------- AI RESPONSE FUNCTION ----------------

def generate_ai_response(user_message):
    if client is None:
        return (
            "Gemini API connection is not configured. "
            "Please check that GEMINI_API_KEY is saved in Streamlit Secrets."
        )

    conversation = SYSTEM_PROMPT + "\n\n"

    for message in st.session_state.messages:
        role = message["role"].upper()
        conversation += f"{role}: {message['content']}\n\n"

    conversation += f"USER: {user_message}\n\nASSISTANT:"

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=conversation
        )
        return response.text or "I couldn't generate a response. Please try again."
    except Exception as error:
        return f"Gemini error: {error}"


# ---------------- RECOMMENDATION DETECTION ----------------

def find_database_mentions(ai_response):
    found_components = []

    response_lower = ai_response.lower()

    for component in all_components:
        component_name = component.get("name", "")

        if component_name and component_name.lower() in response_lower:
            found_components.append(component_name)

    return list(dict.fromkeys(found_components))


def process_recommendations(ai_response):
    mentioned_names = find_database_mentions(ai_response)

    if mentioned_names:
        st.session_state.recommendation_result = match_recommendations(
            mentioned_names
        )


# ---------------- CHAT HISTORY ----------------

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# ---------------- CHAT INPUT ----------------

user_message = st.chat_input(
    "Describe your electronics project or ask a question..."
)

if user_message:
    st.session_state.messages.append({
        "role": "user",
        "content": user_message
    })

    with st.chat_message("user"):
        st.markdown(user_message)

    with st.chat_message("assistant"):
        with st.spinner("ElectroMind AI is thinking..."):
            ai_response = generate_ai_response(user_message)

        st.markdown(ai_response)

    st.session_state.messages.append({
        "role": "assistant",
        "content": ai_response
    })

    process_recommendations(ai_response)


# ---------------- RECOMMENDATION SECTION ----------------

if st.session_state.recommendation_result:
    st.divider()
    st.header("🔧 Component Recommendations")

    display_recommendations(
        st.session_state.recommendation_result,
        all_components
    )


# ---------------- BILL OF MATERIALS ----------------

st.divider()
st.header("🧾 Smart Project Cost Estimator")

if st.session_state.recommendation_result:
    recommended_components = (
        st.session_state.recommendation_result.get(
            "verified_components", []
        )
    )
else:
    recommended_components = []

calculate_bom(
    all_components,
    recommended_components
)


# ---------------- FOOTER ----------------

st.divider()
st.caption(
    "ElectroMind AI | Component prices are illustrative estimates. "
    "Always verify datasheets, electrical ratings and wiring before building."
)
