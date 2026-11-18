import os
import re
from io import BytesIO
from datetime import datetime
from xml.sax.saxutils import escape

import streamlit as st
from google import genai
from google.genai import types

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER
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
    PageBreak,
)


# =========================================================
# ELECTROMIND AI v1.5
# Gemini-powered electronics component recommender
# =========================================================

st.set_page_config(
    page_title="ElectroMind AI",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

MODEL_NAME = st.secrets.get("GEMINI_MODEL", "gemini-2.5-flash-lite")


# ---------------- SESSION STATE ----------------

DEFAULTS = {
    "messages": [],
    "api_error": "",
    "report_content": "",
    "project_started": False,
}

for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ---------------- AI SYSTEM INSTRUCTIONS ----------------

SYSTEM_INSTRUCTION = """
You are ElectroMind AI, a friendly, careful electronics engineering assistant.
You specialize in low-voltage electronics, embedded systems, sensors,
microcontrollers, actuators, power supplies, circuit planning and BOMs.

CONVERSATION:
- First understand the user's project.
- Ask only ONE useful question at a time.
- Do not repeat information the user has already provided.
- Ask about purpose, budget/currency, existing parts, controller,
  sensors/actuators, power source, environment and connectivity only
  when relevant.
- When enough information is available, summarize the requirements and
  ask the user to confirm before producing final recommendations.
- Keep normal chat answers clear and reasonably concise.

FINAL RECOMMENDATION:
When the user confirms the requirements, produce these exact headings:

## COMPONENT RECOMMENDATIONS

Use one numbered subsection per component, for example:
### 1. ESP32 Development Board

For each component, include concise bullets for:
- Category
- Why selected
- Important specifications
- Operating voltage/current (distinguish logic and supply voltage)
- Interface
- Alternative
- Estimated price in INR, clearly marked as an estimate
- Datasheet/source reference, if known

## BILL OF MATERIALS (BOM)

Use exactly this table structure:
| Component Name | Quantity | Purpose | Estimated Price (INR) |

Include a total estimated cost after the table. Clearly state assumptions
and that prices are estimates, not live quotations.

## WIRING AND SAFETY PLAN

Give a concise low-voltage signal/power connection table where appropriate.
Do not invent pin assignments; label proposed pins as examples and explain
what must be verified against the exact board/module datasheets.

TECHNICAL ACCURACY:
- Never invent datasheet specifications, certifications, availability or live prices.
- State assumptions and uncertainty.
- Check logic-level compatibility and power/current requirements.
- Never power motors, servos, relay coils or other high-current loads directly
  from microcontroller GPIO pins.
- Recommend suitable drivers and correctly rated supplies where needed.
- Do not claim components are compatible unless the relevant specifications
  support that conclusion.

ELECTRICAL SAFETY:
- Treat mains AC (for example 120/230 V) and exposed high voltage as hazardous.
- Do NOT provide step-by-step mains wiring, terminal-by-terminal mains
  connections, or instructions for switching household appliances.
- Do not recommend exposed AC-DC converter modules as a beginner wiring project.
- Prefer a certified, enclosed, appropriately rated, isolated power supply
  and low-voltage-only prototyping.
- For any mains-connected equipment, state that design, installation and
  testing must be handled by a qualified electrician/competent professional.
- Clearly separate low-voltage prototype advice from mains-side work.

REPORT STYLE:
- Use compact, readable sections.
- Avoid repeating the same information.
- Do not include the full conversation in the report.
- The component recommendations and BOM must be independently understandable.

SCOPE:
If asked for unrelated topics, politely explain that ElectroMind AI focuses
on electronic hardware projects.
"""


# ---------------- CSS ----------------

st.markdown(
    """
    <style>
    .stApp {
        background: #0b1120;
        color: #f1f5f9;
    }
    .block-container {
        max-width: 1150px;
        padding-top: 1.35rem;
        padding-bottom: 6rem;
    }
    .em-title {
        color: #38bdf8;
        font-size: clamp(1.7rem, 4vw, 2.25rem);
        font-weight: 800;
        letter-spacing: -0.7px;
        margin-bottom: 0;
    }
    .em-subtitle {
        color: #94a3b8;
        font-size: 0.92rem;
        margin-top: 0.15rem;
    }
    div[data-testid="stChatMessage"] {
        background: #111c30;
        border: 1px solid #263449;
        border-radius: 14px;
        padding: 0.8rem 1rem;
        margin-bottom: 0.75rem;
    }
    div[data-testid="stChatInput"] {
        border: 1px solid #334155;
        border-radius: 14px;
    }
    .stButton button, div[data-testid="stDownloadButton"] button {
        border-radius: 10px;
        min-height: 42px;
        font-weight: 600;
    }
    div[data-testid="stDownloadButton"] button {
        background: #0284c7;
        color: white;
        border: 0;
    }
    section[data-testid="stSidebar"] {
        background: #101a2c;
        border-right: 1px solid #263449;
    }
    @media (max-width: 640px) {
        .block-container {
            padding-left: 0.75rem;
            padding-right: 0.75rem;
            padding-top: 0.9rem;
        }
        div[data-testid="stChatMessage"] {
            padding: 0.65rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------- GEMINI CLIENT ----------------

def get_gemini_client():
    api_key = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY", ""))
    if not api_key:
        raise ValueError(
            "Gemini API key not found. Add GEMINI_API_KEY to "
            "Streamlit Secrets or the GEMINI_API_KEY environment variable."
        )
    return genai.Client(api_key=api_key)


def build_conversation_prompt(history, user_input):
    """Build a readable transcript while retaining the complete chat context."""
    transcript = []
    for item in history:
        speaker = "User" if item["role"] == "user" else "ElectroMind AI"
        transcript.append(f"{speaker}:\n{item['content']}")
    transcript.append(f"User:\n{user_input}")
    return "\n\n".join(transcript)


def generate_ai_response(history, user_input):
    client = get_gemini_client()
    prompt = build_conversation_prompt(history, user_input)

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.35,
            max_output_tokens=3000,
        ),
    )

    answer = getattr(response, "text", None)
    if not answer or not answer.strip():
        raise ValueError("Gemini returned an empty response.")
    return answer.strip()


# ---------------- CHAT PROCESSING ----------------

def process_message(user_input):
    user_input = user_input.strip()
    if not user_input:
        return

    st.session_state.messages.append(
        {"role": "user", "content": user_input}
    )
    st.session_state.project_started = True

    try:
        history = st.session_state.messages[:-1]
        with st.spinner("⚡ ElectroMind AI is analysing your project..."):
            answer = generate_ai_response(history, user_input)

        st.session_state.messages.append(
            {"role": "assistant", "content": answer}
        )

        # Save only a response that contains both report sections.
        lower = answer.lower()
        if (
            "component recommendations" in lower
            and "bill of materials" in lower
        ):
            st.session_state.report_content = answer

        st.session_state.api_error = ""

    except Exception as exc:
        # Keep the user's message visible so they can retry or edit it.
        error = str(exc)
        if "429" in error or "RESOURCE_EXHAUSTED" in error:
            friendly = (
                "Gemini API quota/rate limit reached. Check your Google AI "
                "Studio project quota and try again later."
            )
        elif "403" in error or "PERMISSION_DENIED" in error:
            friendly = (
                "Gemini access was denied. Check the API key, project and "
                "model access."
            )
        else:
            friendly = f"Could not get an AI response: {error[:500]}"

        st.session_state.api_error = friendly


# ---------------- REPORT EXTRACTION ----------------

def normalize_heading(line):
    return re.sub(r"[*#_`\\s]", "", line).upper()


def extract_pdf_sections(content):
    """
    Extract only the component recommendation and BOM sections.
    The wiring section and all conversation text are intentionally excluded.
    """
    lines = content.splitlines()
    component_start = None
    bom_start = None
    wiring_start = None

    for i, line in enumerate(lines):
        normalized = normalize_heading(line)

        if component_start is None and "COMPONENTRECOMMENDATIONS" in normalized:
            component_start = i
        elif bom_start is None and "BILLOFMATERIALS" in normalized:
            bom_start = i
        elif wiring_start is None and (
            "WIRINGANDSAFETYPLAN" in normalized
            or "WIRINGSAFETYPLAN" in normalized
        ):
            wiring_start = i

    component_text = ""
    bom_text = ""

    if component_start is not None:
        end_candidates = [
            pos for pos in (bom_start, wiring_start, len(lines))
            if pos is not None and pos > component_start
        ]
        component_text = "\n".join(
            lines[component_start + 1:min(end_candidates)]
        ).strip()

    if bom_start is not None:
        end_candidates = [
            pos for pos in (wiring_start, len(lines))
            if pos is not None and pos > bom_start
        ]
        bom_text = "\n".join(
            lines[bom_start + 1:min(end_candidates)]
        ).strip()

    return component_text, bom_text


# ---------------- PDF HELPERS ----------------

def strip_markdown(text):
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"__(.*?)__", r"\1", text)
    text = re.sub(r"(?<!\*)\*(?!\*)(.*?)\*(?!\*)", r"\1", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = text.replace("₹", "INR ")
    return text.strip()


def make_paragraph(text, style):
    # Escape HTML after removing Markdown so symbols cannot break ReportLab XML.
    return Paragraph(escape(strip_markdown(text)), style)


def parse_bom_table(bom_text):
    rows = []
    for line in bom_text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue

        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if not cells:
            continue

        # Ignore Markdown separator rows such as |---|---|.
        if all(re.fullmatch(r"[-:\s]+", cell or "-") for cell in cells):
            continue

        rows.append(cells)

    return rows


def group_component_lines(component_text):
    """
    Split component text into groups. Supports the recommended format
    (### component heading) and the older 'Component Name:' bullet format.
    """
    groups = []
    current = []

    for raw_line in component_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("|"):
            continue
        if re.fullmatch(r"[-:\s|]+", line):
            continue

        is_new_component = bool(
            re.match(r"^#{2,4}\s+", line)
            or re.match(
                r"^(?:[-*]\s*)?(?:\d+[.)]\s*)?(?:\*\*)?Component\s+Name\s*:",
                line,
                flags=re.I,
            )
            or re.match(r"^\d+[.)]\s+\S", line)
        )

        if is_new_component and current:
            groups.append(current)
            current = []

        current.append(line)

    if current:
        groups.append(current)

    return groups


# ---------------- PDF GENERATOR ----------------

def generate_pdf(content):
    if not content or not content.strip():
        raise ValueError("No final component recommendation is available.")

    component_text, bom_text = extract_pdf_sections(content)
    if not component_text and not bom_text:
        raise ValueError(
            "Could not find the required COMPONENT RECOMMENDATIONS and "
            "BILL OF MATERIALS headings. Ask the AI to regenerate the "
            "final recommendations using the required headings."
        )

    buffer = BytesIO()
    page_width, _ = A4
    margin = 16 * mm
    usable_width = page_width - (2 * margin)

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=margin,
        leftMargin=margin,
        topMargin=15 * mm,
        bottomMargin=18 * mm,
        title="ElectroMind AI - Component Recommendation Report",
        author="ElectroMind AI",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "EMTitle", parent=styles["Title"], fontName="Helvetica-Bold",
        fontSize=21, leading=25, alignment=TA_CENTER,
        textColor=colors.HexColor("#075985"), spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "EMSubtitle", parent=styles["Normal"], fontSize=9,
        leading=12, alignment=TA_CENTER,
        textColor=colors.HexColor("#64748B"), spaceAfter=3,
    )
    section_style = ParagraphStyle(
        "EMSection", parent=styles["Heading2"], fontName="Helvetica-Bold",
        fontSize=13, leading=16, textColor=colors.HexColor("#075985"),
        spaceBefore=12, spaceAfter=7, keepWithNext=True,
    )
    component_heading_style = ParagraphStyle(
        "EMComponentHeading", parent=styles["Heading3"],
        fontName="Helvetica-Bold", fontSize=9.5, leading=12,
        textColor=colors.HexColor("#0F172A"), spaceAfter=4,
        keepWithNext=True,
    )
    body_style = ParagraphStyle(
        "EMBody", parent=styles["BodyText"], fontName="Helvetica",
        fontSize=8.4, leading=11.3, textColor=colors.HexColor("#334155"),
        leftIndent=7, firstLineIndent=-5, spaceAfter=2.5,
    )
    table_style_text = ParagraphStyle(
        "EMTable", parent=styles["BodyText"], fontSize=7.5,
        leading=9.5, textColor=colors.HexColor("#1E293B"),
    )
    table_header_style = ParagraphStyle(
        "EMTableHeader", parent=table_style_text,
        fontName="Helvetica-Bold", textColor=colors.white,
    )
    note_style = ParagraphStyle(
        "EMNote", parent=styles["BodyText"], fontSize=7.5,
        leading=10, textColor=colors.HexColor("#64748B"),
        spaceBefore=7,
    )

    story = [
        Paragraph("ELECTROMIND AI", title_style),
        Paragraph("COMPONENT RECOMMENDATION REPORT", subtitle_style),
        Paragraph(
            "Generated: " + datetime.now().strftime("%d %B %Y"),
            subtitle_style,
        ),
        Spacer(1, 8),
    ]

    # Component recommendations: each component's details are kept together
    # when they fit on a page. Long components can still flow naturally.
    if component_text:
        story.append(Paragraph("01. COMPONENT RECOMMENDATIONS", section_style))
        groups = group_component_lines(component_text)

        for group in groups:
            group_flowables = []
            for index, raw in enumerate(group):
                line = raw.strip()

                heading_match = re.match(r"^#{2,4}\s+(.*)$", line)
                if heading_match:
                    heading = heading_match.group(1)
                    group_flowables.append(
                        make_paragraph(heading, component_heading_style)
                    )
                    continue

                line = re.sub(r"^[-*•]\s*", "", line)
                line = re.sub(r"^\d+[.)]\s*", "", line)

                # Emphasize the field label without interpreting arbitrary HTML.
                label_match = re.match(
                    r"^([^:]{2,55}:)\s*(.*)$", strip_markdown(line)
                )
                if label_match:
                    label = escape(label_match.group(1))
                    value = escape(label_match.group(2))
                    para_text = f"<b>{label}</b> {value}"
                else:
                    para_text = escape(strip_markdown(line))

                group_flowables.append(
                    Paragraph("• " + para_text, body_style)
                )

            if group_flowables:
                story.append(KeepTogether(group_flowables))
                story.append(Spacer(1, 4))

    # Bill of materials table.
    if bom_text:
        story.append(Paragraph("02. BILL OF MATERIALS (BOM)", section_style))
        rows = parse_bom_table(bom_text)

        if rows:
            column_count = max(len(row) for row in rows)
            normalized_rows = [
                row + [""] * (column_count - len(row)) for row in rows
            ]

            if column_count == 4:
                proportions = [0.29, 0.10, 0.37, 0.24]
            else:
                proportions = [1 / column_count] * column_count

            widths = [usable_width * p for p in proportions]
            table_data = []

            for row_index, row in enumerate(normalized_rows):
                style = table_header_style if row_index == 0 else table_style_text
                table_data.append([
                    Paragraph(escape(strip_markdown(cell)), style)
                    for cell in row
                ])

            bom_table = Table(
                table_data,
                colWidths=widths,
                repeatRows=1,
                hAlign="LEFT",
                splitByRow=1,
            )
            bom_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#075985")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#CBD5E1")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1),
                 [colors.white, colors.HexColor("#F1F5F9")]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(bom_table)

        # Keep any total/assumption text after the Markdown table.
        extra_lines = [
            line.strip() for line in bom_text.splitlines()
            if line.strip() and not line.strip().startswith("|")
        ]
        for line in extra_lines:
            story.append(Spacer(1, 3))
            story.append(make_paragraph(line, note_style))

    story.append(Spacer(1, 12))
    story.append(Paragraph(
        "<b>Technical note:</b> Prices are estimates unless otherwise stated. "
        "Verify exact part numbers, manufacturer datasheets, voltage levels, "
        "current ratings and electrical compatibility before purchasing or use. "
        "Mains-voltage work must be handled by a qualified professional.",
        note_style,
    ))

    def add_page_number(canvas, document):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#CBD5E1"))
        canvas.setLineWidth(0.5)
        canvas.line(margin, 13 * mm, page_width - margin, 13 * mm)
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor("#64748B"))
        canvas.drawString(margin, 8.5 * mm, "ElectroMind AI")
        canvas.drawRightString(
            page_width - margin, 8.5 * mm, f"Page {document.page}"
        )
        canvas.restoreState()

    doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
    buffer.seek(0)
    return buffer.getvalue()


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:
    st.markdown("# ⚡ ElectroMind AI")
    st.caption("Your Electronic Engineering Assistant")
    st.divider()

    st.markdown("### Capabilities")
    for feature in [
        "AI project analysis",
        "Smart component selection",
        "Alternative components",
        "Wiring assistance",
        "Budget optimization",
        "Technical specifications",
        "BOM generation",
        "PDF project reports",
    ]:
        st.write(f"• {feature}")

    st.divider()
    st.markdown("### AI Engine")
    try:
        get_gemini_client()
        st.success("Gemini AI Connected")
    except Exception:
        st.error("Gemini AI Not Connected")

    st.caption(f"Model: {MODEL_NAME}")

    if st.button("🗑️ New Conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.report_content = ""
        st.session_state.project_started = False
        st.session_state.api_error = ""
        st.rerun()

    st.caption("ElectroMind AI | Version 1.5")


# =========================================================
# MAIN HEADER
# =========================================================

st.markdown('<div class="em-title">⚡ ElectroMind AI</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="em-subtitle">AI-Powered Electronic Component Recommender</div>',
    unsafe_allow_html=True,
)
st.divider()


# =========================================================
# WELCOME
# =========================================================

if not st.session_state.messages:
    st.markdown("## Welcome, Engineer!")
    st.write(
        "Describe your electronics project. ElectroMind AI will understand "
        "your requirements, ask relevant questions and help select suitable "
        "components."
    )
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info("🔧 Component Selection")
    with col2:
        st.info("⚡ Circuit Planning")
    with col3:
        st.info("💰 Budget Optimization")


# =========================================================
# CHAT HISTORY
# =========================================================

st.markdown("### 💬 Project Conversation")

for message in st.session_state.messages:
    role = message["role"]
    with st.chat_message("user" if role == "user" else "assistant"):
        if role == "assistant":
            st.markdown(message["content"])
        else:
            st.markdown(message["content"])


if st.session_state.api_error:
    st.error(st.session_state.api_error)


# =========================================================
# PROJECT TOOLS
# =========================================================

st.divider()
st.markdown("### 🛠️ Project Tools")

TOOL_PROMPTS = {
    "🔌 Wiring Guide": (
        "Based on our discussion, provide a low-voltage wiring guide. "
        "Use a table with component, signal/power pin, controller pin and notes. "
        "Do not provide step-by-step mains wiring or household AC switching "
        "instructions. Identify anything requiring qualified professional work."
    ),
    "⚖️ Compare Components": (
        "Compare the recommended components with alternatives in a concise "
        "table. Include relevant voltage, interface, advantages, limitations "
        "and estimated price. Mark unknown specifications clearly."
    ),
    "💰 Optimize Budget": (
        "Suggest a cost-conscious component selection within the user's stated "
        "budget. Preserve essential electrical compatibility and safety. "
        "Show estimated INR prices and total; do not invent live prices."
    ),
    "📋 Generate BOM": (
        "Generate the complete BOM using the exact heading "
        "'## BILL OF MATERIALS (BOM)' and table columns "
        "Component Name, Quantity, Purpose, Estimated Price (INR). "
        "Use the project details already discussed and include the estimated total."
    ),
}

tool_columns = st.columns(2)
tool_prompt_clicked = None

for index, (label, prompt) in enumerate(TOOL_PROMPTS.items()):
    with tool_columns[index % 2]:
        if st.button(label, use_container_width=True):
            tool_prompt_clicked = prompt


# =========================================================
# PDF REPORT DOWNLOAD
# =========================================================

st.divider()
st.markdown("### 📄 Component Recommendation Report")

if st.session_state.report_content:
    try:
        pdf_bytes = generate_pdf(st.session_state.report_content)
        st.download_button(
            label="⬇️ Download Component Report (PDF)",
            data=pdf_bytes,
            file_name="ElectroMind_Component_Report.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
        st.caption(
            "The PDF contains only component recommendations and the BOM. "
            "It excludes the chat conversation and wiring discussion."
        )
    except Exception as exc:
        st.warning(f"PDF generation issue: {exc}")
else:
    st.info(
        "The report download will appear after ElectroMind AI generates "
        "the final component recommendations and BOM."
    )


# =========================================================
# CHAT INPUT AND ACTIONS
# =========================================================

user_input = st.chat_input("Describe your electronics project or ask a question...")

if tool_prompt_clicked:
    if not st.session_state.messages:
        st.warning("Describe your project first, then use the project tools.")
    else:
        process_message(tool_prompt_clicked)
        st.rerun()

elif user_input:
    process_message(user_input)
    st.rerun()
