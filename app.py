import streamlit as st
from google import genai
from google.genai import types
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Preformatted
)
from xml.sax.saxutils import escape
from io import BytesIO
from datetime import datetime
import re

# ==================================================
# ELECTROMIND AI - VERSION 1.2
# ==================================================

st.set_page_config(
    page_title="ElectroMind AI",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

MODEL_NAME = "gemini-3.5-flash-lite"

# ---------------- SESSION STATE ----------------

if "messages" not in st.session_state:
    st.session_state.messages = []

if "api_error" not in st.session_state:
    st.session_state.api_error = ""

# ---------------- AI INSTRUCTIONS ----------------

SYSTEM_INSTRUCTION = """
You are ElectroMind AI, an expert electronics engineering assistant.

DOMAIN:
Only handle electronics, electrical hardware, embedded systems,
microcontrollers, sensors, actuators, circuits and PCB components.

CONVERSATION:
1. Understand the user's project.
2. Ask ONE relevant question at a time.
3. Never repeat answered questions.
4. Adapt questions according to previous answers.
5. Ask about budget, controller, power, sensors, performance,
   connectivity and existing components when relevant.
6. Once requirements are sufficient, summarize them and request
   confirmation before final recommendations.

RECOMMENDATIONS:
For each recommended component provide:
- Component name and category.
- Why it was selected.
- Important specifications.
- Operating voltage and current, if verified.
- Interface and pin information.
- Alternative components.
- Estimated price in INR when reliable pricing is available.
- Datasheet reference when a genuine reference is known.

WIRING:
Provide clear connection tables when enough information is known.
Distinguish logic voltage from supply voltage.
Mention current requirements and common ground where applicable.
Never invent pin numbers or electrical specifications.

BUDGET:
Prioritize components that meet requirements within the user's budget.
Explain compromises when recommending cheaper alternatives.
Do not invent live market prices.

COMPARISON:
Compare components using voltage, current, performance,
interfaces, advantages, limitations and approximate price.

BOM:
Provide component name, quantity, purpose and estimated price.

SAFETY:
Never recommend connecting motors directly to GPIO pins.
Mention driver circuits and suitable power supplies.
Clearly warn about mains voltage, high voltage and battery hazards.
Do not present unverified wiring as safe.
Recommend qualified supervision for hazardous circuits.

IMPORTANT:
- Never invent datasheet values or availability.
- Clearly label assumptions and unverified information.
- Do not claim compatibility without sufficient specifications.
- If information is missing, ask the user.
- Keep answers beginner-friendly and organized.
- Avoid unnecessarily long responses.

For unrelated questions, politely explain that you specialize
in electronics projects.
"""

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
    min-height: 42px;
}

div[data-testid="stDownloadButton"] button {
    border-radius: 10px;
}
</style>
""", unsafe_allow_html=True)


# ---------------- GEMINI CONNECTION ----------------

def get_gemini_client():

    api_key = st.secrets.get("GEMINI_API_KEY", "")

    if not api_key:
        raise ValueError(
            "Gemini API key is missing. Configure it in Streamlit Secrets."
        )

    return genai.Client(api_key=api_key)


def generate_ai_response(history, user_input):

    client = get_gemini_client()

    conversation = []

    for message in history:

        role = (
            "User" if message["role"] == "user"
            else "ElectroMind AI"
        )

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
            temperature=0.4,
            max_output_tokens=1800
        )
    )

    if not response.text:
        raise ValueError("Gemini returned an empty response.")

    return response.text


# ---------------- MESSAGE PROCESSING ----------------

def process_message(user_input):

    st.session_state.messages.append({
        "role": "user",
        "content": user_input
    })

    try:

        history = st.session_state.messages[:-1]

        with st.spinner("ElectroMind AI is analysing..."):

            response = generate_ai_response(
                history,
                user_input
            )

        st.session_state.messages.append({
            "role": "assistant",
            "content": response
        })

        st.session_state.api_error = ""

        return True

    except Exception as error:

        st.session_state.messages.pop()

        error_message = str(error)

        if "429" in error_message or "RESOURCE_EXHAUSTED" in error_message:
            st.session_state.api_error = (
                "Gemini usage limit reached. Check your API quota."
            )

        elif "403" in error_message or "PERMISSION_DENIED" in error_message:
            st.session_state.api_error = (
                "API access denied. Check your API key and model access."
            )

        else:
            st.session_state.api_error = (
                "Unable to generate a response: " + error_message[:300]
            )

        return False


# ---------------- PDF GENERATOR ----------------

def generate_pdf(messages):

    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm
    )

    styles = getSampleStyleSheet()

    story = []

    story.append(
        Paragraph("ElectroMind AI - Project Report", styles["Title"])
    )

    story.append(Spacer(1, 10))

    story.append(
        Paragraph(
            "Electronics Component Recommendation Report",
            styles["Heading2"]
        )
    )

    story.append(
        Paragraph(
            "Generated: " + datetime.now().strftime("%d-%m-%Y %H:%M"),
            styles["Normal"]
        )
    )

    story.append(Spacer(1, 15))

    for message in messages:

        if message["role"] == "user":
            heading = "USER REQUIREMENTS"
        else:
            heading = "ELECTROMIND AI RECOMMENDATION"

        story.append(
            Paragraph(heading, styles["Heading3"])
        )

        content = message["content"]

        # Remove basic Markdown formatting for a readable PDF.
        content = re.sub(r"```.*?```", "[Code block omitted]", content,
                         flags=re.S)
        content = re.sub(r"[*_`#]", "", content)
        content = escape(content)

        story.append(
            Preformatted(
                content,
                styles["Code"],
                maxLineLength=90
            )
        )

        story.append(Spacer(1, 12))

    story.append(Spacer(1, 10))

    story.append(
        Paragraph(
            "Note: Verify all electrical specifications and wiring "
            "against official manufacturer documentation before use.",
            styles["Italic"]
        )
    )

    document.build(story)

    buffer.seek(0)

    return buffer.getvalue()


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
    st.write("• PDF Project Reports")

    st.divider()

    st.markdown("### AI Engine")

    try:
        get_gemini_client()
        st.success("Gemini AI Connected")
    except Exception:
        st.error("Gemini AI Not Connected")

    st.caption(f"Model: {MODEL_NAME}")

    st.divider()

    if st.button("🗑️ New Conversation", use_container_width=True):

        st.session_state.messages = []
        st.session_state.api_error = ""

        st.rerun()

    st.caption("ElectroMind AI | Version 1.2")


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
        "I'll understand your requirements, ask technical questions "
        "and help you choose suitable components."
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


# ---------------- ERROR DISPLAY ----------------

if st.session_state.api_error:

    st.error(st.session_state.api_error)


# ---------------- QUICK ACTIONS ----------------

st.divider()

st.markdown("### 🛠️ Project Tools")

tool_prompts = {
    "🔌 Wiring Guide":
        "Based on our project discussion, provide a detailed wiring "
        "guide in a component-to-component connection table. "
        "Include pin numbers, logic levels and power requirements. "
        "Clearly identify anything that needs verification.",

    "⚖️ Compare Components":
        "Compare the recommended components with their alternatives. "
        "Show specifications, voltage, performance, advantages, "
        "limitations and estimated prices in a comparison table.",

    "💰 Optimize Budget":
        "Optimize our component selection for the discussed budget. "
        "Suggest cost-effective alternatives without sacrificing "
        "essential performance or electrical compatibility.",

    "📋 Generate BOM":
        "Generate a complete Bill of Materials for our project. "
        "Include component name, quantity, purpose, estimated "
        "individual price in INR and estimated total cost. "
        "Clearly label uncertain prices."
}

tool_columns = st.columns(4)

tool_clicked = None

for index, (label, prompt) in enumerate(tool_prompts.items()):

    with tool_columns[index]:

        if st.button(label, use_container_width=True):

            tool_clicked = prompt


# ---------------- PDF DOWNLOAD ----------------

if st.session_state.messages:

    st.markdown("### 📄 Project Report")

    try:

        pdf_data = generate_pdf(st.session_state.messages)

        st.download_button(
            label="⬇️ Download Project Report (PDF)",
            data=pdf_data,
            file_name="ElectroMind_Project_Report.pdf",
            mime="application/pdf",
            use_container_width=True
        )

    except Exception as error:
        st.warning("PDF generation failed: " + str(error))


# ---------------- CHAT INPUT ----------------

user_input = st.chat_input(
    "Describe your electronics project..."
)


# ---------------- HANDLE USER INPUT ----------------

if tool_clicked:

    if not st.session_state.messages:

        st.warning(
            "Please describe your project in the chatbot first."
        )

    else:

        process_message(tool_clicked)
        st.rerun()


elif user_input:

    process_message(user_input)
    st.rerun()
