import re
from io import BytesIO
from datetime import datetime
from xml.sax.saxutils import escape

import streamlit as st
from google import genai
from google.genai import types

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
    KeepTogether,
)


# =========================================================
# ELECTROMIND AI VERSION 1.5
# =========================================================

st.set_page_config(
    page_title="ElectroMind AI",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

MODEL_NAME = "gemini-3.5-flash-lite"


# =========================================================
# SESSION STATE
# =========================================================

defaults = {
    "messages": [],
    "api_error": "",
    "report_content": "",
    "project_started": False
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# =========================================================
# GEMINI SYSTEM INSTRUCTION
# =========================================================

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
8. When sufficient information is collected,
   summarize requirements and ask for confirmation.

FINAL COMPONENT RECOMMENDATIONS:

After the user confirms requirements, use these exact headings:

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

Use a Markdown table:

| Component Name | Quantity | Purpose | Estimated Price (INR) |

Include total estimated project cost.

## WIRING AND SAFETY PLAN

Explain connections using a simple table.

Include:
- Component
- Component pin
- Controller/power pin
- Notes

Clearly distinguish signal and power connections.

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
- Mention when datasheet verification is required.

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

Politely explain that ElectroMind AI specializes
in electronic hardware projects.
"""


# =========================================================
# CUSTOM CSS
# =========================================================

st.markdown("""
<style>

.stApp {
    background: #0b1120;
    color: #f1f5f9;
}

.block-container {
    max-width: 1150px;
    padding-top: 1.4rem;
    padding-bottom: 5.5rem;
}

.main-title {
    color: #38bdf8;
    font-size: 34px;
    font-weight: 800;
    letter-spacing: -1px;
    margin-bottom: 0;
}

.subtitle {
    color: #94a3b8;
    font-size: 14px;
    margin-top: 4px;
}

div[data-testid="stChatMessage"] {
    background: #111c30;
    border: 1px solid #263449;
    border-radius: 14px;
    padding: 12px 15px;
    margin-bottom: 12px;
}

div[data-testid="stChatInput"] {
    border: 1px solid #334155;
    border-radius: 14px;
}

.stButton button,
div[data-testid="stDownloadButton"] button {
    border-radius: 10px;
    min-height: 42px;
    font-weight: 600;
}

div[data-testid="stDownloadButton"] button {
    background: #0284c7;
    color: white;
    border: none;
    min-height: 46px;
}

section[data-testid="stSidebar"] {
    background: #101a2c;
    border-right: 1px solid #263449;
}

div[data-testid="stExpander"] {
    border: 1px solid #263449;
    border-radius: 12px;
}

@media (max-width: 640px) {

    .block-container {
        padding-left: 0.8rem;
        padding-right: 0.8rem;
        padding-top: 0.9rem;
    }

    .main-title {
        font-size: 27px;
    }

    .subtitle {
        font-size: 12px;
    }

    div[data-testid="stChatMessage"] {
        padding: 9px;
    }

    .stButton button {
        font-size: 12px;
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

    except Exception as exc:

        raise ValueError(
            "Gemini API key is missing. "
            "Add GEMINI_API_KEY to Streamlit Secrets."
        ) from exc

    if not api_key or not str(api_key).strip():
        raise ValueError("GEMINI_API_KEY is empty.")

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

    return response.text.strip()


# =========================================================
# PROCESS CHAT MESSAGE
# =========================================================

def process_message(user_input):

    user_input = user_input.strip()

    if not user_input:
        return False

    previous_history = list(
        st.session_state.messages
    )

    st.session_state.messages.append({
        "role": "user",
        "content": user_input
    })

    st.session_state.project_started = True
    st.session_state.api_error = ""

    try:

        with st.spinner(
            "⚡ ElectroMind AI is analysing your project..."
        ):

            response = generate_ai_response(
                previous_history,
                user_input
            )

        st.session_state.messages.append({
            "role": "assistant",
            "content": response
        })

        lower_response = response.lower()

        if (
            "component recommendations" in lower_response
            and "bill of materials" in lower_response
        ):

            st.session_state.report_content = response

        return True

    except Exception as error:

        error_message = str(error)

        if (
            "429" in error_message
            or "RESOURCE_EXHAUSTED" in error_message
        ):

            st.session_state.api_error = (
                "Gemini API quota/rate limit reached. "
                "Check your API usage and try again later."
            )

        elif (
            "403" in error_message
            or "PERMISSION_DENIED" in error_message
        ):

            st.session_state.api_error = (
                "API access denied. Check your API key "
                "and whether the selected model is available."
            )

        else:

            st.session_state.api_error = (
                "Unable to generate a response: "
                + error_message[:500]
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
        r"__(.*?)__",
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


def normalize_heading(line):

    return re.sub(
        r"[^A-Z]",
        "",
        line.upper()
    )


# =========================================================
# EXTRACT PDF SECTIONS
# =========================================================

def extract_pdf_sections(content):

    lines = content.splitlines()

    component_start = None
    bom_start = None
    wiring_start = None

    for index, line in enumerate(lines):

        normalized = normalize_heading(line)

        if (
            component_start is None
            and "COMPONENTRECOMMENDATIONS" in normalized
        ):

            component_start = index

        elif (
            bom_start is None
            and "BILLOFMATERIALS" in normalized
        ):

            bom_start = index

        elif (
            wiring_start is None
            and (
                "WIRINGANDSAFETYPLAN" in normalized
                or normalized.startswith("WIRING")
            )
        ):

            wiring_start = index

    component_text = ""
    bom_text = ""

    if component_start is not None:

        possible_ends = [
            pos
            for pos in (
                bom_start,
                wiring_start,
                len(lines)
            )
            if pos is not None and pos > component_start
        ]

        end = min(possible_ends)

        component_text = "\n".join(
            lines[component_start + 1:end]
        ).strip()

    if bom_start is not None:

        possible_ends = [
            pos
            for pos in (
                wiring_start,
                len(lines)
            )
            if pos is not None and pos > bom_start
        ]

        end = min(possible_ends)

        bom_text = "\n".join(
            lines[bom_start + 1:end]
        ).strip()

    return component_text, bom_text


# =========================================================
# PARSE MARKDOWN TABLE
# =========================================================

def parse_markdown_table(section_text):

    rows = []
    extra_lines = []

    for raw_line in section_text.splitlines():

        line = raw_line.strip()

        if not line:
            continue

        if line.startswith("|") and line.endswith("|"):

            cells = [
                cell.strip()
                for cell in line.strip("|").split("|")
            ]

            if cells and all(
                re.fullmatch(
                    r"\s*:?-{2,}:?\s*",
                    cell
                )
                for cell in cells
            ):
                continue

            if cells:
                rows.append(cells)

        else:

            extra_lines.append(line)

    return rows, extra_lines


# =========================================================
# PROFESSIONAL PDF GENERATOR
# =========================================================

def generate_pdf(content):

    if not content:

        raise ValueError(
            "No component recommendations are available yet."
        )

    component_text, bom_text = extract_pdf_sections(
        content
    )

    if not component_text and not bom_text:

        raise ValueError(
            "Could not find the Component Recommendations "
            "and BOM sections. Generate final recommendations first."
        )

    buffer = BytesIO()

    page_width, _ = A4

    left_margin = 17 * mm
    right_margin = 17 * mm

    usable_width = (
        page_width - left_margin - right_margin
    )

    document = SimpleDocTemplate(

        buffer,

        pagesize=A4,

        rightMargin=right_margin,

        leftMargin=left_margin,

        topMargin=15 * mm,

        bottomMargin=16 * mm,

        title="ElectroMind AI Component Report",

        author="ElectroMind AI"
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "EMTitle",
        parent=styles["Title"],
        fontSize=21,
        leading=25,
        textColor=colors.HexColor("#0369A1"),
        alignment=0,
        spaceAfter=4
    )

    subtitle_style = ParagraphStyle(
        "EMSubtitle",
        parent=styles["Normal"],
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#64748B"),
        spaceAfter=3
    )

    heading_style = ParagraphStyle(
        "EMHeading",
        parent=styles["Heading2"],
        fontSize=13,
        leading=17,
        textColor=colors.HexColor("#0369A1"),
        spaceBefore=12,
        spaceAfter=7,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        "EMBody",
        parent=styles["BodyText"],
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#334155"),
        spaceAfter=3
    )

    component_style = ParagraphStyle(
        "EMComponent",
        parent=body_style,
        fontSize=9.2,
        leading=12.5,
        textColor=colors.HexColor("#0F172A"),
        spaceBefore=6,
        spaceAfter=3,
        keepWithNext=True
    )

    small_style = ParagraphStyle(
        "EMSmall",
        parent=styles["BodyText"],
        fontSize=7.6,
        leading=10,
        textColor=colors.HexColor("#334155")
    )

    header_style = ParagraphStyle(
        "EMTableHeader",
        parent=small_style,
        fontSize=7.7,
        leading=9.5,
        textColor=colors.white
    )

    story = [

        Paragraph(
            "ELECTROMIND AI",
            title_style
        ),

        Paragraph(
            "Electronic Component Recommendation Report",
            subtitle_style
        ),

        Paragraph(
            "Generated: "
            + datetime.now().strftime("%d %B %Y"),
            small_style
        ),

        Spacer(1, 9)

    ]

    # -----------------------------------------------------
    # COMPONENT RECOMMENDATIONS
    # -----------------------------------------------------

    if component_text:

        story.append(
            Paragraph(
                "1. Component Recommendations",
                heading_style
            )
        )

        for raw_line in component_text.splitlines():

            line = raw_line.strip()

            if not line or line.startswith("|"):
                continue

            if re.fullmatch(r"[-:\s|]+", line):
                continue

            line = clean_pdf_text(line)

            if not line:
                continue

            if re.match(r"^\d+[.)]\s*", line):

                story.append(
                    KeepTogether([

                        Paragraph(
                            "<b>" + escape(line) + "</b>",
                            component_style
                        )

                    ])
                )

            else:

                line = re.sub(
                    r"^[-*•]\s*",
                    "",
                    line
                )

                story.append(
                    Paragraph(
                        "&#8226; " + escape(line),
                        body_style
                    )
                )

    # -----------------------------------------------------
    # BILL OF MATERIALS
    # -----------------------------------------------------

    if bom_text:

        story.append(
            Paragraph(
                "2. Bill of Materials (BOM)",
                heading_style
            )
        )

        table_rows, extra_bom_lines = parse_markdown_table(
            bom_text
        )

        if table_rows:

            column_count = max(
                len(row)
                for row in table_rows
            )

            normalized_rows = [

                row + [""] * (
                    column_count - len(row)
                )

                for row in table_rows

            ]

            if column_count == 4:

                proportions = [
                    0.30,
                    0.11,
                    0.36,
                    0.23
                ]

            else:

                proportions = [
                    1 / column_count
                ] * column_count

            widths = [
                usable_width * part
                for part in proportions
            ]

            formatted_rows = []

            for row_index, row in enumerate(
                normalized_rows
            ):

                style = (
                    header_style
                    if row_index == 0
                    else small_style
                )

                formatted_rows.append([

                    Paragraph(
                        escape(clean_pdf_text(cell)),
                        style
                    )

                    for cell in row

                ])

            bom_table = Table(

                formatted_rows,

                colWidths=widths,

                repeatRows=1,

                hAlign="LEFT",

                splitByRow=1

            )

            # CORRECTED TABLE STYLE SYNTAX

            bom_table.setStyle(
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
                        5
                    ),

                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        5
                    ),

                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        6
                    ),

                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        6
                    )

                ])
            )

            story.append(bom_table)

        for line in extra_bom_lines:

            cleaned = clean_pdf_text(line)

            if cleaned:

                story.append(
                    Paragraph(
                        escape(cleaned),
                        body_style
                    )
                )

    # -----------------------------------------------------
    # FOOTER
    # -----------------------------------------------------

    story.extend([

        Spacer(1, 15),

        Paragraph(
            "<b>Technical Disclaimer:</b> Verify component "
            "specifications, electrical compatibility, current "
            "requirements and manufacturer datasheets before "
            "implementation.",
            small_style
        ),

        Spacer(1, 7),

        Paragraph(
            "Generated by ElectroMind AI",
            small_style
        )

    ])

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

    st.caption(f"Model: {MODEL_NAME}")

    st.divider()

    if st.button(
        "🗑️ New Conversation",
        use_container_width=True
    ):

        st.session_state.messages = []
        st.session_state.report_content = ""
        st.session_state.project_started = False
        st.session_state.api_error = ""

        st.rerun()

    st.caption("ElectroMind AI | Version 1.5")


# =========================================================
# MAIN HEADER
# =========================================================

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


# =========================================================
# WELCOME SCREEN
# =========================================================

if not st.session_state.messages:

    st.markdown("## Welcome, Engineer! 👋")

    st.write(
        "Tell me about your electronics project. "
        "I'll understand your requirements, ask technical "
        "questions and help you select suitable components."
    )

    st.markdown("### What can I help you with?")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.info("🔧 Component Selection")

    with col2:
        st.info("⚡ Circuit & Wiring")

    with col3:
        st.info("💰 Budget Optimization")

    st.caption(
        "Start by describing your project in the chat box below."
    )


# =========================================================
# CHAT HISTORY
# =========================================================

st.markdown("### 💬 Project Conversation")

for message in st.session_state.messages:

    avatar = (
        "🧑‍💻"
        if message["role"] == "user"
        else "⚡"
    )

    with st.chat_message(
        message["role"],
        avatar=avatar
    ):

        st.markdown(
            message["content"]
        )


# =========================================================
# ERROR DISPLAY
# =========================================================

if st.session_state.api_error:

    st.error(
        st.session_state.api_error
    )


# =========================================================
# PROJECT TOOLS
# =========================================================

st.divider()

st.markdown("### 🛠️ Project Tools")

tool_prompts = {

    "🔌 Wiring Guide": """
Based on our project discussion, generate a wiring guide.

Use a clear connection table with:
Component, Component Pin, Controller/Power Pin and Notes.

Explain signal and power connections separately.
Mention voltage compatibility and current requirements.
Mark connections that need datasheet verification.
Do not invent pin assignments.
""",

    "⚖️ Compare Components": """
Compare the recommended components with their alternatives.

Use a table with:
Component, Voltage, Performance, Interface,
Advantages, Limitations and Estimated Price.

Clearly identify unverified specifications.
""",

    "💰 Optimize Budget": """
Optimize our component selection for the user's stated budget.

Suggest cost-effective alternatives while preserving
essential performance and electrical compatibility.

Show estimated prices in INR and approximate total cost.
Explain compromises.
Do not invent live market prices.
""",

    "📋 Generate BOM": """
Generate a complete Bill of Materials using our project requirements.

Use the heading:

## BILL OF MATERIALS (BOM)

Use a Markdown table with:
Component Name, Quantity, Purpose and Estimated Price (INR).

Include the estimated total project cost.
Do not invent unavailable information.
"""

}

tool_columns = st.columns(2)

selected_tool_prompt = None

for index, (label, prompt) in enumerate(
    tool_prompts.items()
):

    with tool_columns[index % 2]:

        if st.button(
            label,
            use_container_width=True,
            key=f"tool_{index}"
        ):

            selected_tool_prompt = prompt


if selected_tool_prompt:

    if not st.session_state.messages:

        st.warning(
            "Please describe your electronics project first."
        )

    else:

        process_message(selected_tool_prompt)

        st.rerun()


# =========================================================
# PDF REPORT DOWNLOAD
# =========================================================

st.divider()

st.markdown("### 📄 Component Recommendation Report")

if st.session_state.report_content:

    try:

        pdf_data = generate_pdf(
            st.session_state.report_content
        )

        st.download_button(

            label="⬇️ Download Component Report (PDF)",

            data=pdf_data,

            file_name="ElectroMind_Component_Report.pdf",

            mime="application/pdf",

            use_container_width=True

        )

        st.caption(
            "The PDF includes component recommendations and BOM only. "
            "Chat history and wiring discussion are excluded."
        )

    except Exception as error:

        st.warning(
            f"PDF generation issue: {error}"
        )

else:

    st.info(
        "Your report will appear here after ElectroMind AI "
        "generates the final component recommendations and BOM."
    )


# =========================================================
# CHAT INPUT
# KEEP THIS AT THE END OF THE SCRIPT
# =========================================================

user_input = st.chat_input(
    "Describe your electronics project or ask a question..."
)

if user_input:

    process_message(user_input)

    st.rerun()
