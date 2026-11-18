import streamlit as st
from google import genai
from google.genai import types

from io import BytesIO
from datetime import datetime
from xml.sax.saxutils import escape
import re

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether
)


# =========================================================
# ELECTROMIND AI VERSION 1.3
# Gemini Powered Electronics Component Recommender
# =========================================================


# ---------------- PAGE CONFIGURATION ----------------

st.set_page_config(
    page_title="ElectroMind AI",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)


MODEL_NAME = "gemini-3.5-flash-lite"


# ---------------- SESSION STATE ----------------

defaults = {
    "messages": [],
    "api_error": "",
    "report_content": "",
    "project_started": False
}

for key, value in defaults.items():

    if key not in st.session_state:
        st.session_state[key] = value


# ---------------- GEMINI INSTRUCTIONS ----------------

SYSTEM_INSTRUCTION = """
You are ElectroMind AI, an expert electronics engineering assistant.

YOUR DOMAIN:
You ONLY handle electronics and electrical hardware projects.

This includes:
- Microcontrollers
- Sensors
- Actuators
- Embedded systems
- Power supplies
- Electronic circuits
- PCB components
- Communication modules

CONVERSATION RULES:

1. First understand the user's project idea.
2. Ask ONE useful question at a time.
3. Never repeat questions already answered.
4. Adapt questions to previous answers.
5. Ask relevant questions about:
   - Project purpose
   - Budget and currency
   - Existing components
   - Controller preference
   - Sensors and actuators
   - Power supply
   - Operating environment
   - Performance
   - Connectivity
   - Size requirements
6. Skip irrelevant questions.
7. Do not force a fixed number of questions.
8. When sufficient information is collected, summarize
   requirements and ask the user to confirm.

FINAL COMPONENT RECOMMENDATIONS:

After the user confirms their requirements, use these
exact section headings:

## COMPONENT RECOMMENDATIONS

For every component include:

- Component name
- Category
- Why it was selected
- Important specifications
- Operating voltage and current
- Interface
- Alternative component
- Estimated price in INR, if known
- Datasheet reference, if known

Keep descriptions concise.

## BILL OF MATERIALS (BOM)

Use a Markdown table with these columns:

| Component Name | Quantity | Purpose | Estimated Price (INR) |

Include a total estimated project cost.

## WIRING AND SAFETY PLAN

Explain the connections using a simple table.

Include:
- Component
- Component pin
- Controller/power pin
- Notes

Clearly distinguish signal connections and power connections.

TECHNICAL ACCURACY:

- Never invent datasheet specifications.
- Never invent product availability or live prices.
- Clearly label estimates and assumptions.
- Distinguish logic voltage from supply voltage.
- Check current and power requirements.
- Never connect motors directly to GPIO pins.
- Mention suitable motor drivers or power supplies.
- Check sensor output compatibility with controller logic.
- Do not claim compatibility without sufficient information.
- Mention when a datasheet must be checked.

SAFETY:

- Clearly identify electrical hazards.
- Do not present unverified wiring as safe.
- Avoid hazardous mains or high-voltage construction instructions.
- Recommend qualified supervision for hazardous circuits.
- Explain safe low-voltage prototyping practices.

COMMUNICATION:

- Friendly and professional.
- Beginner-friendly.
- Use headings and tables.
- Avoid unnecessarily long answers.
- Ask only ONE main question per response.

UNRELATED QUESTIONS:

Politely explain that ElectroMind AI currently specializes
in electronic hardware projects.
"""


# ---------------- CUSTOM CSS ----------------

st.markdown("""
<style>

.stApp {
    background-color: #0b1120;
    color: #ffffff;
}

.main-title {
    font-size: 36px;
    font-weight: 800;
    color: #38bdf8;
}

.subtitle {
    color: #94a3b8;
    font-size: 15px;
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
    min-height: 45px;
}

div[data-testid="stExpander"] {
    border: 1px solid #263449;
    border-radius: 10px;
}

@media (max-width: 640px) {

    .main-title {
        font-size: 27px;
    }

    .subtitle {
        font-size: 13px;
    }

}

</style>
""", unsafe_allow_html=True)


# =========================================================
# GEMINI CONNECTION
# =========================================================

def get_gemini_client():

    try:
        api_key = st.secrets["GEMINI_API_KEY"]

    except Exception:
        raise ValueError(
            "Gemini API key is missing. "
            "Please configure GEMINI_API_KEY in Streamlit Secrets."
        )

    if not api_key:
        raise ValueError("Gemini API key is empty.")

    return genai.Client(api_key=api_key)


# =========================================================
# GENERATE AI RESPONSE
# =========================================================

def generate_ai_response(history, user_input):

    client = get_gemini_client()

    conversation = []

    for message in history:

        role = (
            "User"
            if message["role"] == "user"
            else "ElectroMind AI"
        )

        conversation.append(
            f"{role}: {message['content']}"
        )

    conversation.append(
        f"User: {user_input}"
    )

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

        raise ValueError(
            "Gemini returned an empty response."
        )

    return response.text


# =========================================================
# PROCESS CHAT MESSAGE
# =========================================================

def process_message(user_input):

    st.session_state.messages.append({

        "role": "user",

        "content": user_input

    })

    st.session_state.project_started = True

    try:

        history = st.session_state.messages[:-1]

        with st.spinner(
            "⚡ ElectroMind AI is analysing your project..."
        ):

            response = generate_ai_response(
                history,
                user_input
            )

        st.session_state.messages.append({

            "role": "assistant",

            "content": response

        })

        # Preserve the latest component recommendation
        # when the user subsequently uses other tools.

        lower_response = response.lower()

        has_recommendations = (
            "component recommendations" in lower_response
        )

        if has_recommendations:

            st.session_state.report_content = response

        st.session_state.api_error = ""

        return True

    except Exception as error:

        st.session_state.messages.pop()

        error_message = str(error)

        if (
            "429" in error_message
            or "RESOURCE_EXHAUSTED" in error_message
        ):

            st.session_state.api_error = (
                "Gemini API usage limit reached. "
                "Please check your API quota."
            )

        elif (
            "403" in error_message
            or "PERMISSION_DENIED" in error_message
        ):

            st.session_state.api_error = (
                "API access denied. Check your API key "
                "and model access."
            )

        else:

            st.session_state.api_error = (
                "Unable to generate response: "
                + error_message[:300]
            )

        return False


# =========================================================
# PDF TEXT HELPERS
# =========================================================

def clean_pdf_text(text):

    text = re.sub(
        r"```.*?```",
        "",
        text,
        flags=re.S
    )

    text = re.sub(
        r"\*\*(.*?)\*\*",
        r"\1",
        text
    )

    text = re.sub(
        r"\*(.*?)\*",
        r"\1",
        text
    )

    text = re.sub(
        r"`(.*?)`",
        r"\1",
        text
    )

    # Standard PDF fonts may not support the rupee symbol.
    text = text.replace("₹", "INR ")

    return text.strip()


def extract_pdf_sections(content):

    component_match = re.search(
        r"##\s*COMPONENT RECOMMENDATIONS\s*(.*?)"
        r"(?=##\s*BILL OF MATERIALS|##\s*WIRING|$)",
        content,
        re.I | re.S
    )

    bom_match = re.search(
        r"##\s*BILL OF MATERIALS\s*\(BOM\)\s*(.*?)"
        r"(?=##\s*WIRING|##\s*SAFETY|$)",
        content,
        re.I | re.S
    )

    # Fallback for older recommendation responses.
    if not component_match:

        component_match = re.search(
            r"Component Recommendations\s*(.*?)"
            r"(?=Bill of Materials|BOM|Wiring|Safety Plan|$)",
            content,
            re.I | re.S
        )

    if not bom_match:

        bom_match = re.search(
            r"Bill of Materials\s*\(BOM\)(.*?)"
            r"(?=Wiring|Safety Plan|Next Steps|$)",
            content,
            re.I | re.S
        )

    component_text = (
        component_match.group(1).strip()
        if component_match
        else ""
    )

    bom_text = (
        bom_match.group(1).strip()
        if bom_match
        else ""
    )

    return component_text, bom_text


# =========================================================
# PROFESSIONAL PDF GENERATOR
# =========================================================

def generate_pdf(content):

    if not content:

        raise ValueError(
            "No component recommendations available."
        )

    component_text, bom_text = extract_pdf_sections(content)

    if not component_text and not bom_text:

        raise ValueError(
            "Recommendation sections were not detected. "
            "Generate the final component recommendations first."
        )

    buffer = BytesIO()

    document = SimpleDocTemplate(

        buffer,

        pagesize=A4,

        rightMargin=18 * mm,

        leftMargin=18 * mm,

        topMargin=16 * mm,

        bottomMargin=16 * mm
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(

        "ReportTitle",

        parent=styles["Title"],

        fontSize=21,

        leading=26,

        textColor=colors.HexColor("#0284C7"),

        spaceAfter=5
    )

    subtitle_style = ParagraphStyle(

        "ReportSubtitle",

        parent=styles["Normal"],

        fontSize=10,

        textColor=colors.HexColor("#64748B"),

        spaceAfter=5
    )

    heading_style = ParagraphStyle(

        "SectionHeading",

        parent=styles["Heading2"],

        fontSize=14,

        leading=18,

        textColor=colors.HexColor("#0369A1"),

        spaceBefore=14,

        spaceAfter=8
    )

    body_style = ParagraphStyle(

        "ReportBody",

        parent=styles["BodyText"],

        fontSize=9,

        leading=13,

        spaceAfter=4
    )

    component_style = ParagraphStyle(

        "ComponentTitle",

        parent=body_style,

        fontSize=10,

        leading=14,

        textColor=colors.HexColor("#0F172A"),

        spaceBefore=7,

        spaceAfter=4
    )

    small_style = ParagraphStyle(

        "SmallText",

        parent=styles["BodyText"],

        fontSize=8,

        leading=11
    )

    story = []

    # REPORT HEADER

    story.append(
        Paragraph(
            "ELECTROMIND AI",
            title_style
        )
    )

    story.append(
        Paragraph(
            "Electronic Component Recommendation Report",
            subtitle_style
        )
    )

    story.append(
        Paragraph(
            "Generated: "
            + datetime.now().strftime("%d %B %Y"),
            small_style
        )
    )

    story.append(Spacer(1, 12))

    # COMPONENT RECOMMENDATIONS

    if component_text:

        story.append(
            Paragraph(
                "1. Component Recommendations",
                heading_style
            )
        )

        lines = component_text.splitlines()

        for line in lines:

            line = clean_pdf_text(line)

            if not line:
                continue

            line = re.sub(
                r"^\s*[-*•]+\s*",
                "",
                line
            )

            if line.startswith("|"):
                continue

            if re.fullmatch(
                r"[-:\s|]+",
                line
            ):
                continue

            if re.match(
                r"^\d+[\.)]\s*",
                line
            ):

                story.append(
                    KeepTogether([

                        Spacer(1, 5),

                        Paragraph(
                            "<b>" + escape(line) + "</b>",
                            component_style
                        )

                    ])
                )

            else:

                story.append(
                    Paragraph(
                        "• " + escape(line),
                        body_style
                    )
                )

    # BILL OF MATERIALS

    if bom_text:

        story.append(
            Paragraph(
                "2. Bill of Materials (BOM)",
                heading_style
            )
        )

        table_data = []

        for line in bom_text.splitlines():

            line = line.strip()

            if not line.startswith("|"):
                continue

            cells = [

                cell.strip()

                for cell in line.strip("|").split("|")

            ]

            # Ignore Markdown separator rows.

            if all(
                re.fullmatch(r"[-:\s]+", cell or "-")
                for cell in cells
            ):
                continue

            if cells:
                table_data.append(cells)

        if table_data:

            column_count = max(
                len(row)
                for row in table_data
            )

            if column_count == 4:

                widths = [
                    125,
                    45,
                    180,
                    105
                ]

            elif column_count == 3:

                widths = [
                    180,
                    65,
                    210
                ]

            else:

                widths = [
                    515 / column_count
                ] * column_count

            formatted_data = []

            for row in table_data:

                row = row + (
                    [""] * (column_count - len(row))
                )

                formatted_row = []

                for cell in row:

                    formatted_row.append(

                        Paragraph(
                            escape(clean_pdf_text(cell)),
                            small_style
                        )

                    )

                formatted_data.append(formatted_row)

            table = Table(

                formatted_data,

                colWidths=widths,

                repeatRows=1,

                hAlign="LEFT"

            )

            table.setStyle(

                TableStyle([

                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.HexColor("#0369A1")
                    ),

                    (
                        "TEXTCOLOR",
                        (0, 0),
                        (-1, 0),
                        colors.white
                    ),

                    (
                        "FONTNAME",
                        (0, 0),
                        (-1, 0),
                        "Helvetica-Bold"
                    ),

                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.5,
                        colors.HexColor("#CBD5E1")
                    ),

                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [
                            colors.white,
                            colors.HexColor("#EFF6FA")
                        ]
                    ),

                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "TOP"
                    ),

                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        6
                    ),

                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        6
                    ),

                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        7
                    ),

                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        7
                    )

                ])

            )

            story.append(table)

        else:

            story.append(
                Paragraph(
                    escape(clean_pdf_text(bom_text)),
                    body_style
                )
            )

    # FOOTER

    story.append(Spacer(1, 18))

    story.append(
        Paragraph(
            "<b>Technical Disclaimer:</b> "
            "Verify component specifications, electrical "
            "compatibility, current requirements and manufacturer "
            "datasheets before implementation.",
            small_style
        )
    )

    story.append(Spacer(1, 8))

    story.append(
        Paragraph(
            "Generated by ElectroMind AI",
            small_style
        )
    )

    document.build(story)

    buffer.seek(0)

    return buffer.getvalue()


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.markdown("# ⚡ ElectroMind AI")

    st.caption(
        "Your Electronic Engineering Assistant"
    )

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

    st.write("• BOM Generation")

    st.write("• PDF Project Reports")

    st.divider()

    st.markdown("### AI Engine")

    try:

        get_gemini_client()

        st.success("Gemini AI Connected")

    except Exception:

        st.error("Gemini AI Not Connected")

    st.caption(
        f"Model: {MODEL_NAME}"
    )

    st.divider()

    if st.button(
        "🗑️ New Conversation",
        use_container_width=True
    ):

        st.session_state.messages = []

        st.session_state.report_content = ""

        st.session_state.project_started = False

        st.session_state.api_error = ""

        st.rerun(
