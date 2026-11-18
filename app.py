import streamlit as st
import os
import re
from io import BytesIO
from datetime import datetime
from xml.sax.saxutils import escape

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
    PageBreak
)


# =========================================================
# ELECTROMIND AI VERSION 1.5
# Gemini Powered Electronics Component Recommender
# =========================================================


# ---------------- PAGE CONFIGURATION ----------------

st.set_page_config(
    page_title="ElectroMind AI",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

MODEL_NAME = "gemini-3.8-flash"


# ---------------- SESSION STATE ----------------

DEFAULTS = {
    "messages": [],
    "api_error": "",
    "report_content": "",
    "project_started": False
}

for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value


# =========================================================
# GEMINI SYSTEM INSTRUCTIONS
# =========================================================

SYSTEM_INSTRUCTION = """
You are ElectroMind AI, an expert electronics engineering assistant.

YOUR DOMAIN:
Only handle electronics and electrical hardware projects.

Topics include:
- Microcontrollers
- Sensors
- Actuators
- Embedded systems
- Low-voltage power supplies
- Electronic circuits
- PCB components
- Communication modules
- IoT projects
- Robotics electronics

CONVERSATION RULES:

1. First understand the user's project idea.
2. Ask ONE useful question at a time.
3. Never repeat questions already answered.
4. Remember previous project requirements.
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
8. When enough information is collected, summarize
   requirements and ask the user to confirm.
9. Do not generate final recommendations before
   sufficient requirements are available.

FINAL RECOMMENDATIONS:

After the user confirms requirements, generate
a complete recommendation using EXACTLY these headings:

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

Use this Markdown table:

| Component Name | Quantity | Purpose | Estimated Price (INR) |

Include the total estimated project cost.

## WIRING AND SAFETY PLAN

Use a Markdown connection table:

| Component | Component Pin | Controller/Power Pin | Notes |

Clearly distinguish signal connections and power connections.

TECHNICAL ACCURACY:

- Never invent datasheet specifications.
- Never invent product availability or live prices.
- Clearly label estimates and assumptions.
- Distinguish logic voltage from supply voltage.
- Check current and power requirements.
- Never connect motors directly to GPIO pins.
- Mention suitable drivers when appropriate.
- Check sensor output compatibility.
- Never claim compatibility without sufficient information.
- Mention when a datasheet must be checked.

SAFETY:

- Focus on low-voltage electronics.
- Do not provide step-by-step mains-voltage or
  high-voltage construction or wiring instructions.
- If a project involves household AC mains,
  explain that mains-side work must be handled by
  a qualified electrician under appropriate supervision.
- Do not suggest connecting mains directly to GPIO,
  breadboards or exposed low-voltage circuits.
- Explain safe low-voltage prototyping practices.
- Do not present unverified wiring as safe.

COMMUNICATION:

- Friendly and professional.
- Beginner-friendly.
- Use headings and tables.
- Avoid unnecessarily long answers.
- Ask only ONE main question per response.

UNRELATED QUESTIONS:

Politely explain that ElectroMind AI specializes
in electronics and hardware projects.
"""


# =========================================================
# CUSTOM CSS
# =========================================================

st.markdown("""
<style>

/* Main application */

.stApp {
    background-color: #0b1120;
    color: #f1f5f9;
}

/* Main content */

.block-container {
    max-width: 1150px;
    padding-top: 2rem !important;
    padding-bottom: 5rem !important;
    padding-left: 1.5rem;
    padding-right: 1.5rem;
    overflow: visible !important;
}

/* Header */

.main-title {
    display: block;
    width: 100%;
    font-size: 36px;
    font-weight: 800;
    line-height: 1.5;
    color: #38bdf8;
    letter-spacing: -0.5px;
    padding-top: 5px;
    padding-bottom: 2px;
    overflow: visible;
    white-space: normal;
}

.subtitle {
    color: #94a3b8;
    font-size: 14px;
    line-height: 1.6;
    margin-top: 3px;
}

/* Chat messages */

div[data-testid="stChatMessage"] {
    background: #111c30;
    border: 1px solid #263449;
    border-radius: 14px;
    padding: 14px;
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
    min-height: 44px;
    font-weight: 600;
}

/* Download button */

div[data-testid="stDownloadButton"] button {
    background: #0284c7;
    color: white;
    border: none;
    border-radius: 10px;
    min-height: 48px;
    font-weight: 700;
}

/* Sidebar */

section[data-testid="stSidebar"] {
    background: #101a2c;
    border-right: 1px solid #263449;
}

/* Expanders */

div[data-testid="stExpander"] {
    border: 1px solid #263449;
    border-radius: 12px;
}

/* Alert boxes */

div[data-testid="stAlert"] {
    border-radius: 10px;
}

/* Markdown tables */

div[data-testid="stMarkdownContainer"] table {
    width: 100%;
}

/* Mobile layout */

@media (max-width: 640px) {

    .block-container {
        padding-top: 1.5rem !important;
        padding-left: 0.8rem;
        padding-right: 0.8rem;
    }

    .main-title {
        font-size: 29px;
        line-height: 1.5;
        padding-top: 5px;
    }

    .subtitle {
        font-size: 12px;
    }

    div[data-testid="stChatMessage"] {
        padding: 10px;
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

    api_key = None

    # Streamlit Cloud Secrets

    try:
        api_key = st.secrets.get("GEMINI_API_KEY")

    except Exception:
        pass

    # Environment variable fallback

    if not api_key:
        api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise ValueError(
            "Gemini API key is missing. "
            "Add GEMINI_API_KEY to Streamlit Secrets."
        )

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

            max_output_tokens=6000

        )

    )

    if not response.text:
        raise ValueError(
            "Gemini returned an empty response."
        )

    return response.text.strip()


# =========================================================
# CHECK FINAL RECOMMENDATION
# =========================================================

def has_final_recommendations(content):

    if not content:
        return False

    normalized = re.sub(
        r"[*#_\s]",
        "",
        content
    ).upper()

    required_sections = [
        "COMPONENTRECOMMENDATIONS",
        "BILLOFMATERIALS",
        "WIRINGANDSAFETYPLAN"
    ]

    return all(
        section in normalized
        for section in required_sections
    )


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

        # Save only complete final recommendations.

        if has_final_recommendations(response):

            st.session_state.report_content = response

        st.session_state.api_error = ""

        return True

    except Exception as error:

        # Remove failed user message.

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
                "and model permissions."
            )

        elif (
            "404" in error_message
            or "NOT_FOUND" in error_message
        ):

            st.session_state.api_error = (
                "Gemini model was not found. Check the model "
                "name and API availability in Google AI Studio. "
                "Current configured model: " + MODEL_NAME
            )

        else:

            st.session_state.api_error = (
                "Unable to generate response: "
                + error_message[:400]
            )

        return False


# =========================================================
# PDF TEXT FORMATTING
# =========================================================

def format_pdf_text(text):

    text = str(text).strip()

    text = re.sub(
        r"`([^`]*)`",
        r"\1",
        text
    )

    text = re.sub(
        r"\*\*(.*?)\*\*",
        r"<b>\1</b>",
        escape(text)
    )

    text = re.sub(
        r"(?<!\*)\*([^*]+)\*(?!\*)",
        r"<i>\1</i>",
        text
    )

    text = text.replace("₹", "INR ")

    return text


# =========================================================
# EXTRACT PDF SECTIONS
# =========================================================

def extract_pdf_sections(content):

    lines = content.splitlines()

    headings = {}

    for index, line in enumerate(lines):

        normalized = re.sub(
            r"[*#_\s]",
            "",
            line
        ).upper()

        if (
            "COMPONENTRECOMMENDATIONS" in normalized
            and "components" not in headings
        ):

            headings["components"] = index

        elif (
            "BILLOFMATERIALS" in normalized
            and "bom" not in headings
        ):

            headings["bom"] = index

        elif (
            "WIRINGANDSAFETYPLAN" in normalized
            and "wiring" not in headings
        ):

            headings["wiring"] = index

    result = {}

    section_order = [
        "components",
        "bom",
        "wiring"
    ]

    for position, section in enumerate(section_order):

        if section not in headings:
            result[section] = ""
            continue

        start = headings[section] + 1

        end = len(lines)

        for next_section in section_order[position + 1:]:

            if next_section in headings:
                end = headings[next_section]
                break

        result[section] = "\n".join(
            lines[start:end]
        ).strip()

    return result


# =========================================================
# PDF STYLES
# =========================================================

def get_pdf_styles():

    styles = getSampleStyleSheet()

    styles.add(
        ParagraphStyle(
            name="EMTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=23,
            leading=29,
            textColor=colors.HexColor("#0369A1"),
            spaceAfter=5
        )
    )

    styles.add(
        ParagraphStyle(
            name="EMSubtitle",
            parent=styles["Normal"],
            fontSize=10,
            leading=15,
            textColor=colors.HexColor("#64748B"),
            spaceAfter=5
        )
    )

    styles.add(
        ParagraphStyle(
            name="EMHeading",
            parent=styles["Heading2"],
            fontSize=14,
            leading=19,
            textColor=colors.HexColor("#0369A1"),
            spaceBefore=13,
            spaceAfter=8,
            keepWithNext=True
        )
    )

    styles.add(
        ParagraphStyle(
            name="EMSubheading",
            parent=styles["Heading3"],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#0F172A"),
            spaceBefore=7,
            spaceAfter=4,
            keepWithNext=True
        )
    )

    styles.add(
        ParagraphStyle(
            name="EMBody",
            parent=styles["BodyText"],
            fontSize=8.5,
            leading=12.5,
            textColor=colors.HexColor("#334155"),
            spaceAfter=4
        )
    )

    styles.add(
        ParagraphStyle(
            name="EMBullet",
            parent=styles["BodyText"],
            fontSize=8.3,
            leading=12,
            leftIndent=12,
            firstLineIndent=-8,
            textColor=colors.HexColor("#334155"),
            spaceAfter=3
        )
    )

    styles.add(
        ParagraphStyle(
            name="EMSmall",
            parent=styles["BodyText"],
            fontSize=7.5,
            leading=10,
            textColor=colors.HexColor("#334155")
        )
    )

    styles.add(
        ParagraphStyle(
            name="EMTableHeader",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=7.4,
            leading=9.5,
            textColor=colors.white
        )
    )

    return styles


# =========================================================
# PDF TABLE GENERATOR
# =========================================================

def create_pdf_table(lines, available_width, styles, section):

    table_data = []

    for line in lines:

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

    if not table_data:
        return None

    column_count = max(
        len(row)
        for row in table_data
    )

    if column_count == 4:

        if section == "bom":

            proportions = [
                0.29,
                0.11,
                0.37,
                0.23
            ]

        else:

            proportions = [
                0.19,
                0.17,
                0.27,
                0.37
            ]

    else:

        proportions = [
            1 / column_count
        ] * column_count

    widths = [
        available_width * value
        for value in proportions
    ]

    formatted_data = []

    for row_index, row in enumerate(table_data):

        row = row + (
            [""] * (column_count - len(row))
        )

        formatted_row = []

        for cell in row:

            style = (
                styles["EMTableHeader"]
                if row_index == 0
                else styles["EMSmall"]
            )

            formatted_row.append(
                Paragraph(
                    format_pdf_text(cell),
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

        TableStyle([

            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.HexColor("#0369A1")
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

    return table


# =========================================================
# PDF SECTION CONTENT
# =========================================================

def add_pdf_section(story, section_text, section_name,
                    available_width, styles):

    if not section_text:
        return

    lines = section_text.splitlines()

    story.append(
        Paragraph(
            section_name,
            styles["EMHeading"]
        )
    )

    non_table_lines = []
    table_lines = []

    def flush_table():

        if table_lines:

            table = create_pdf_table(
                table_lines,
                available_width,
                styles,
                "bom" if "BOM" in section_name else "other"
            )

            if table:
                story.append(table)

            table_lines.clear()

    for line in lines:

        stripped = line.strip()

        if stripped.startswith("|"):

            if non_table_lines:

                for item in non_table_lines:
                    add_pdf_text_line(story, item, styles)

                non_table_lines.clear()

            table_lines.append(stripped)

        else:

            flush_table()

            if stripped:
                non_table_lines.append(stripped)

    flush_table()

    for item in non_table_lines:
        add_pdf_text_line(story, item, styles)


# =========================================================
# PDF LINE FORMATTER
# =========================================================

def add_pdf_text_line(story, line, styles):

    line = line.strip()

    if not line:
        return

    # Remove code blocks and Markdown formatting.

    if line.startswith("```"):
        return

    # Subheadings.

    if line.startswith("###"):

        heading = line.lstrip("#").strip()

        story.append(
            Paragraph(
                format_pdf_text(heading),
                styles["EMSubheading"]
            )
        )

        return

    # Bullet points.

    if re.match(r"^[-*•]\s*", line):

        line = re.sub(
            r"^[-*•]\s*",
            "",
            line
        )

        story.append(
            Paragraph(
                "&#8226; " + format_pdf_text(line),
                styles["EMBullet"]
            )
        )

        return

    # Numbered points.

    if re.match(r"^\d+[\.)]\s*", line):

        story.append(
            Paragraph(
                format_pdf_text(line),
                styles["EMBody"]
            )
        )

        return

    # Normal text.

    story.append(
        Paragraph(
            format_pdf_text(line),
            styles["EMBody"]
        )
    )


# =========================================================
# PDF PAGE FOOTER
# =========================================================

def add_pdf_footer(canvas, document):

    canvas.saveState()

    page_width, page_height = A4

    canvas.setStrokeColor(
        colors.HexColor("#CBD5E1")
    )

    canvas.line(
        17 * mm,
        13 * mm,
        page_width - 17 * mm,
        13 * mm
    )

    canvas.setFont(
        "Helvetica",
        7
    )

    canvas.setFillColor(
        colors.HexColor("#64748B")
    )

    canvas.drawString(
        17 * mm,
        8 * mm,
        "Generated by ElectroMind AI"
    )

    canvas.drawRightString(
        page_width - 17 * mm,
        8 * mm,
        f"Page {document.page}"
    )

    canvas.restoreState()


# =========================================================
# GENERATE COMPLETE PDF
# =========================================================

def generate_pdf(content):

    if not content:
        raise ValueError(
            "No recommendations available."
        )

    sections = extract_pdf_sections(content)

    if not all([
        sections["components"],
        sections["bom"],
        sections["wiring"]
    ]):

        raise ValueError(
            "The final recommendation must contain all three "
            "sections: COMPONENT RECOMMENDATIONS, "
            "BILL OF MATERIALS (BOM), and "
            "WIRING AND SAFETY PLAN. "
            "Please generate the final recommendations again."
        )

    buffer = BytesIO()

    document = SimpleDocTemplate(

        buffer,

        pagesize=A4,

        rightMargin=17 * mm,

        leftMargin=17 * mm,

        topMargin=19 * mm,

        bottomMargin=19 * mm

    )

    styles = get_pdf_styles()

    available_width = (
        A4[0] - 34 * mm
    )

    story = []

    # REPORT HEADER

    story.append(
        Paragraph(
            "ELECTROMIND AI",
            styles["EMTitle"]
        )
    )

    story.append(
        Paragraph(
            "Electronic Component Recommendation Report",
            styles["EMSubtitle"]
        )
    )

    story.append(
        Paragraph(
            "Generated: " +
            datetime.now().strftime("%d %B %Y"),
            styles["EMSmall"]
        )
    )

    story.append(
        Spacer(1, 12)
    )

    # SECTION 1

    add_pdf_section(
        story,
        sections["components"],
        "1. Component Recommendations",
        available_width,
        styles
    )

    # SECTION 2

    add_pdf_section(
        story,
        sections["bom"],
        "2. Bill of Materials (BOM)",
        available_width,
        styles
    )

    # SECTION 3

    add_pdf_section(
        story,
        sections["wiring"],
        "3. Wiring and Safety Plan",
        available_width,
        styles
    )

    # DISCLAIMER

    story.append(
        Spacer(1, 12)
    )

    story.append(
        Paragraph(
            "<b>Technical Disclaimer:</b> "
            "Verify all component specifications, electrical "
            "compatibility, current requirements and manufacturer "
            "datasheets before implementation. Mains-voltage work "
            "must be handled by a qualified electrician.",
            styles["EMSmall"]
        )
    )

    document.build(
        story,
        onFirstPage=add_pdf_footer,
        onLaterPages=add_pdf_footer
    )

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

    st.markdown("### Capabilities")

    st.write("🔧 AI Project Analysis")

    st.write("⚡ Component Selection")

    st.write("🔌 Wiring Assistance")

    st.write("💰 Budget Optimization")

    st.write("📋 BOM Generation")

    st.write("📄 PDF Project Reports")

    st.divider()

    st.markdown("### AI Engine")

    try:

        get_gemini_client()

        st.success("Gemini AI Connected")

    except Exception:

        st.error("Gemini AI Not Connected")

    st.caption(
        "Model: " + MODEL_NAME
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

        st.rerun()

    st.caption(
        "ElectroMind AI | Version 1.5"
    )


# =========================================================
# MAIN HEADER
# =========================================================

st.markdown(
    """
    <div class="main-title">
        ⚡ ElectroMind AI
    </div>
    <div class="subtitle">
        AI-Powered Electronic Component Recommender
    </div>
    """,
    unsafe_allow_html=True
)

st.divider()


# =========================================================
# WELCOME SCREEN
# =========================================================

if not st.session_state.messages:

    st.markdown("## Welcome, Engineer!")

    st.write(
        "Tell me about your electronics project. "
        "I will understand your requirements, ask technical "
        "questions and help you select suitable components."
    )

    st.markdown("### What can I help you with?")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.info("🔧 Component Selection")

    with col2:
        st.info("⚡ Circuit Assistance")

    with col3:
        st.info("💰 Budget Optimization")

    st.markdown(
        "### Start with your project idea"
    )


# =========================================================
# PROJECT CONVERSATION
# =========================================================

st.markdown("### 💬 Project Conversation")

for index, message in enumerate(
    st.session_state.messages
):

    if message["role"] == "user":

        with st.chat_message("user"):

            st.markdown(
                message["content"]
            )

    else:

        with st.chat_message("assistant"):

            with st.expander(
                "⚡ ElectroMind AI Response",
                expanded=(
                    index == len(st.session_state.messages) - 1
                )
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

TOOL_PROMPTS = {

    "🔌 Wiring Guide": """
Based on our project discussion, provide a wiring guide.

Use a clear table with:
Component, component pin, controller/power pin and notes.

Explain signal and low-voltage power connections separately.
Mention voltage compatibility and current requirements.
Clearly identify datasheet verification requirements.

Do not provide step-by-step mains or high-voltage wiring.
Do not invent pin assignments.
""",

    "⚖️ Compare Components": """
Compare the recommended components with their alternatives.

Use a comparison table containing:
Component, voltage, performance, interface,
advantages, limitations and estimated price.

Clearly identify unverified specifications.
""",

    "💰 Optimize Budget": """
Optimize our component selection for the user's stated budget.

Suggest suitable cost-effective alternatives.
Preserve essential performance and electrical compatibility.
Show estimated prices in INR and approximate total cost.
Explain any compromises.
Do not invent live market prices.
""",

    "📋 Generate BOM": """
Generate a complete Bill of Materials for our project.

Use this exact heading:

## BILL OF MATERIALS (BOM)

Use this table:

| Component Name | Quantity | Purpose | Estimated Price (INR) |

Include the estimated total project cost.

Use previous project requirements.
Do not invent unavailable information.
""",

    "⭐ Generate Final Recommendations": """
Generate the FINAL COMPONENT RECOMMENDATION REPORT.

Use our complete previous conversation and confirmed
project requirements.

Use EXACTLY these three section headings:

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

## BILL OF MATERIALS (BOM)

Create a Markdown table:

| Component Name | Quantity | Purpose | Estimated Price (INR) |

Include the total estimated project cost.

## WIRING AND SAFETY PLAN

Create a Markdown table:

| Component | Component Pin | Controller/Power Pin | Notes |

Clearly distinguish signal and low-voltage power connections.

Include safety warnings and datasheet verification notes.

Do not invent specifications, prices or pin assignments.

Do not provide step-by-step mains-voltage wiring instructions.

If essential requirements are still missing, ask one
clarifying question instead of generating an incomplete report.
"""
}


tool_columns = st.columns(2)

tool_clicked = None

for index, (label, prompt) in enumerate(
    TOOL_PROMPTS.items()
):

    with tool_columns[index % 2]:

        if st.button(
            label,
            use_container_width=True
        ):

            tool_clicked = prompt


# =========================================================
# PDF DOWNLOAD SECTION
# =========================================================

st.divider()

st.markdown(
    "### 📄 Component Recommendation Report"
)

if st.session_state.report_content:

    try:

        pdf_data = generate_pdf(
            st.session_state.report_content
        )

        st.success(
            "Your complete component report is ready!"
        )

        st.download_button(

            label="⬇️ Download Component Report (PDF)",

            data=pdf_data,

            file_name="ElectroMind_AI_Component_Report.pdf",

            mime="application/pdf",

            use_container_width=True,

            key="download_report"

        )

        st.caption(
            "Includes component recommendations, BOM, "
            "wiring and safety plan."
        )

    except Exception as error:

        st.warning(
            "PDF generation issue: " + str(error)
        )

else:

    st.info(
        "The PDF download will appear after ElectroMind AI "
        "generates the complete final recommendations "
        "using all three required headings."
    )

    st.caption(
        "Use the Generate Final Recommendations button "
        "after confirming your project requirements."
    )


# =========================================================
# CHAT INPUT
# =========================================================

user_input = st.chat_input(
    "Describe your electronics project or ask a question..."
)


# =========================================================
# HANDLE TOOL BUTTON
# =========================================================

if tool_clicked:

    if not st.session_state.messages:

        st.warning(
            "Please describe your electronics project first."
        )

    else:

        process_message(tool_clicked)

        st.rerun()


# =========================================================
# HANDLE CHAT INPUT
# =========================================================

elif user_input:

    process_message(user_input)

    st.rerun()
