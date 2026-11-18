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
# ELECTROMIND AI VERSION 1.4
# Gemini Powered Electronics Component Recommender
# =========================================================


# ---------------- PAGE CONFIGURATION ----------------

st.set_page_config(
    page_title="ElectroMind AI",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
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

Explain connections using a simple table.

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

/* Main background */

.stApp {
    background: #0b1120;
    color: #f1f5f9;
}

/* Main content width */

.block-container {
    max-width: 1150px;
    padding-top: 1.5rem;
    padding-bottom: 5rem;
}

/* Main title */

.main-title {
    font-size: 34px;
    font-weight: 800;
    color: #38bdf8;
    letter-spacing: -1px;
}

.subtitle {
    color: #94a3b8;
    font-size: 14px;
    margin-top: 4px;
}

/* Chat messages */

div[data-testid="stChatMessage"] {
    background: #111c30;
    border: 1px solid #263449;
    border-radius: 14px;
    padding: 15px;
    margin-bottom: 12px;
}

/* Chat input */

div[data-testid="stChatInput"] {
    border: 1px solid #334155;
    border-radius: 14px;
}

/* Buttons */

.stButton button {
    border-radius: 10px;
    min-height: 42px;
    font-weight: 600;
}

/* Download button */

div[data-testid="stDownloadButton"] button {
    border-radius: 10px;
    min-height: 45px;
    background: #0284c7;
    color: white;
    border: none;
}

/* Sidebar */

section[data-testid="stSidebar"] {
    background: #101a2c;
    border-right: 1px solid #263449;
}

/* Expander */

div[data-testid="stExpander"] {
    border: 1px solid #263449;
    border-radius: 12px;
}

/* Info cards */

div[data-testid="stAlert"] {
    border-radius: 10px;
}

/* Mobile adjustments */

@media (max-width: 640px) {

    .block-container {
        padding-left: 0.8rem;
        padding-right: 0.8rem;
        padding-top: 1rem;
    }

    .main-title {
        font-size: 27px;
    }

    .subtitle {
        font-size: 12px;
    }

    div[data-testid="stChatMessage"] {
        padding: 10px;
    }

    .stButton button {
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
            "Configure GEMINI_API_KEY in Streamlit Secrets."
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

            max_output_tokens=2500
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

        # Save the final recommendation for PDF generation.

        lower_response = response.lower()

        if (
            "component recommendations" in lower_response
            and "bill of materials" in lower_response
        ):

            st.session_state.report_content = response

        st.session_state.api_error = ""

        return True

    except Exception as error:

        # Remove the failed user message so it is not
        # accidentally sent again as conversation history.

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
                + error_message[:400]
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

    text = text.replace("₹", "INR ")

    return text.strip()


# =========================================================
# EXTRACT COMPONENT AND BOM SECTIONS
# =========================================================

def extract_pdf_sections(content):

    lines = content.splitlines()

    component_start = None
    bom_start = None
    wiring_start = None

    for index, line in enumerate(lines):

        normalized = re.sub(
            r"[*#_\s]",
            "",
            line
        ).upper()

        if (
            "COMPONENTRECOMMENDATIONS" in normalized
            and component_start is None
        ):

            component_start = index

        elif (
            "BILLOFMATERIALS" in normalized
            and bom_start is None
        ):

            bom_start = index

        elif (
            "WIRINGANDSAFETYPLAN" in normalized
            and wiring_start is None
        ):

            wiring_start = index

    component_text = ""
    bom_text = ""

    if component_start is not None:

        end = (
            bom_start
            if bom_start is not None
            else wiring_start
            if wiring_start is not None
            else len(lines)
        )

        component_text = "\n".join(
            lines[component_start + 1:end]
        ).strip()

    if bom_start is not None:

        end = (
            wiring_start
            if wiring_start is not None
            else len(lines)
        )

        bom_text = "\n".join(
            lines[bom_start + 1:end]
        ).strip()

    return component_text, bom_text


# =========================================================
# PDF GENERATOR
# =========================================================

def generate_pdf(content):

    if not content:
        raise ValueError(
            "No component recommendations available."
        )

    component_text, bom_text = extract_pdf_sections(content)

    if not component_text and not bom_text:

        raise ValueError(
            "Could not find the component recommendation "
            "and BOM sections. Generate the final recommendations "
            "first."
        )

    buffer = BytesIO()

    page_width, page_height = A4

    left_margin = 17 * mm
    right_margin = 17 * mm

    usable_width = page_width - left_margin - right_margin

    document = SimpleDocTemplate(

        buffer,

        pagesize=A4,

        rightMargin=right_margin,

        leftMargin=left_margin,

        topMargin=16 * mm,

        bottomMargin=17 * mm
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(

        "ReportTitle",

        parent=styles["Title"],

        fontSize=22,

        leading=27,

        textColor=colors.HexColor("#0369A1"),

        alignment=0,

        spaceAfter=5
    )

    subtitle_style = ParagraphStyle(

        "ReportSubtitle",

        parent=styles["Normal"],

        fontSize=10,

        leading=14,

        textColor=colors.HexColor("#64748B"),

        spaceAfter=4
    )

    heading_style = ParagraphStyle(

        "SectionHeading",

        parent=styles["Heading2"],

        fontSize=14,

        leading=18,

        textColor=colors.HexColor("#0369A1"),

        spaceBefore=13,

        spaceAfter=8
    )

    body_style = ParagraphStyle(

        "ReportBody",

        parent=styles["BodyText"],

        fontSize=8.7,

        leading=12.5,

        textColor=colors.HexColor("#334155"),

        spaceAfter=3
    )

    component_style = ParagraphStyle(

        "ComponentTitle",

        parent=body_style,

        fontSize=9.5,

        leading=13,

        textColor=colors.HexColor("#0F172A"),

        spaceBefore=7,

        spaceAfter=3
    )

    small_style = ParagraphStyle(

        "SmallText",

        parent=styles["BodyText"],

        fontSize=7.8,

        leading=10.5,

        textColor=colors.HexColor("#334155")
    )

    header_style = ParagraphStyle(

        "TableHeader",

        parent=small_style,

        fontSize=8,

        leading=10,

        textColor=colors.white
    )

    story = []

    # ---------------- HEADER ----------------

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

    story.append(
        Spacer(1, 10)
    )

    # ---------------- COMPONENTS ----------------

    if component_text:

        story.append(
            Paragraph(
                "1. Component Recommendations",
                heading_style
            )
        )

        lines = component_text.splitlines()

        for line in lines:

            line = line.strip()

            if not line:
                continue

            line = clean_pdf_text(line)

            line = re.sub(
                r"^\s*[-*•]+\s*",
                "",
                line
            )

            if not line:
                continue

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

                        Spacer(1, 4),

                        Paragraph(
                            "<b>" + escape(line) + "</b>",
                            component_style
                        )

                    ])
                )

            else:

                story.append(
                    Paragraph(
                        "&#8226; " + escape(line),
                        body_style
                    )
                )

    # ---------------- BILL OF MATERIALS ----------------

    if bom_text:

        story.append(
            Paragraph(
                "2. Bill of Materials (BOM)",
                heading_style
            )
        )

        table_data = []
        extra_bom_lines = []

        for line in bom_text.splitlines():

            line = line.strip()

            if line.startswith("|"):

                cells = [
                    cell.strip()
                    for cell in line.strip("|").split("|")
                ]

                if all(
                    re.fullmatch(r"[-:\s]+", cell or "-")
                    for cell in cells
                ):
                    continue

                if cells:
                    table_data.append(cells)

            elif line:

                extra_bom_lines.append(line)

        if table_data:

            column_count = max(
                len(row)
                for row in table_data
            )

            # Four-column BOM table.

            if column_count == 4:

                proportions = [
                    0.30,
                    0.10,
                    0.38,
                    0.22
                ]

            else:

                proportions = [
                    1 / column_count
                ] * column_count

            widths = [
                usable_width * proportion
                for proportion in proportions
            ]

            formatted_data = []

            for row_index, row in enumerate(table_data):

                row = row + (
                    [""] * (column_count - len(row))
                )

                formatted_row = []

                for cell in row:

                    cell_text = escape(
                        clean_pdf_text(cell)
                    )

                    style = (
                        header_style
                        if row_index == 0
                        else small_style
                    )

                    formatted_row.append(
                        Paragraph(
                            cell_text,
                            style
                        )
                    )

                formatted_data.append(formatted_row)

            table = Table(

                formatted_data,

                colWidths=widths,

                repeatRows=1,

                hAlign="LEFT",

                splitByRow=1
            )

            table.setStyle(

                TableStyle([]

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
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.45,
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

                    () 
