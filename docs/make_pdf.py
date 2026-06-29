"""Build the Agent Run Report as a PDF with ReportLab (no native deps).

Run:  python3 docs/make_pdf.py   ->  docs/Agent_Run_Report.pdf
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    ListFlowable,
    ListItem,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

HERE = Path(__file__).resolve().parent
IMAGES = HERE / "images"
OUT = HERE / "Agent_Run_Report.pdf"

MAX_W = 6.6 * inch
INK = colors.HexColor("#1f2937")
GREY = colors.HexColor("#6b7280")

styles = getSampleStyleSheet()
styles.add(ParagraphStyle("H1", parent=styles["Title"], fontSize=22, spaceAfter=10, textColor=INK))
styles.add(ParagraphStyle("H2", parent=styles["Heading2"], fontSize=15, spaceBefore=16,
                          spaceAfter=6, textColor=INK))
styles.add(ParagraphStyle("H3", parent=styles["Heading3"], fontSize=12.5, spaceBefore=10,
                          textColor=INK))
styles.add(ParagraphStyle("Body", parent=styles["BodyText"], fontSize=10.5, leading=15,
                          alignment=TA_LEFT, textColor=INK))
styles.add(ParagraphStyle("Caption", parent=styles["BodyText"], fontSize=9, textColor=GREY,
                          spaceBefore=2, spaceAfter=10))
styles.add(ParagraphStyle("CodeBlock", parent=styles["Code"], fontSize=8.2, leading=11.5,
                          textColor=colors.HexColor("#0f172a"), leftIndent=0))
styles.add(ParagraphStyle("Cell", parent=styles["BodyText"], fontSize=9, leading=12))


def img(name: str, caption: str | None = None) -> list:
    path = IMAGES / name
    w, h = PILImage.open(path).size
    scale = min(MAX_W / w, 1.0)
    flow: list = [Image(str(path), width=w * scale, height=h * scale)]
    if caption:
        flow.append(Paragraph(caption, styles["Caption"]))
    flow.append(Spacer(1, 6))
    return flow


def p(text: str) -> Paragraph:
    return Paragraph(text, styles["Body"])


def bullets(items: list[str]) -> ListFlowable:
    return ListFlowable(
        [ListItem(Paragraph(t, styles["Body"]), leftIndent=12) for t in items],
        bulletType="bullet", start="•", leftIndent=14,
    )


def code(text: str):
    """A code block as a bordered light-grey panel (always readable)."""
    panel = Table([[Preformatted(text, styles["CodeBlock"])]], colWidths=[MAX_W])
    panel.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f3f4f6")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return panel


def build() -> None:
    doc = SimpleDocTemplate(
        str(OUT), pagesize=letter,
        leftMargin=0.8 * inch, rightMargin=0.8 * inch,
        topMargin=0.8 * inch, bottomMargin=0.8 * inch,
        title="Agent Run Report — Healthcare Q&A Agent",
    )
    s: list = []

    s.append(Paragraph("Agent Run Report — Healthcare Q&amp;A Agent", styles["H1"]))
    s.append(p("A short walkthrough of what I built, how it thinks, and how it behaves when "
               "you actually run it. The goal was a small, honest agent that answers health "
               "questions by looking things up and summarizing what it finds — not a giant "
               "framework, and nothing that needs servers to run."))

    s.append(Paragraph("1. What it does, in one line", styles["H2"]))
    s.append(p("You ask a health question, the agent searches a medical knowledge base, reads "
               "the results, and writes back a short answer with the sources it used."))
    s.append(p("I picked the <b>healthcare Q&amp;A</b> domain because it shows the whole agent "
               "story clearly: it has to decide <i>what</i> to look up, actually call a tool, "
               "read the results, and then ground its answer in them."))

    s.append(Paragraph("2. Architecture", styles["H2"]))
    s += img("architecture.png")
    s.append(p("The flow is a classic <b>ReAct loop</b> (Reason → Act → Observe), which mirrors "
               "how a person researches something:"))
    s.append(bullets([
        "<b>Guard-rails</b> — sanity-check the question before spending any tokens.",
        "<b>Agent (the LLM)</b> — each turn returns one small JSON step: a <i>thought</i> plus "
        "an <i>action</i> (either \"search\" or \"final answer\").",
        "<b>Tool: medical search</b> — search_medical_database() uses DuckDuckGo (free, no key) "
        "as a stand-in for PubMed, steering queries toward medical sources.",
        "<b>Observation</b> — the top results (title, snippet, link) go back to the agent.",
        "The loop repeats until the agent is confident, then it writes a <b>grounded answer "
        "with cited sources</b>.",
    ]))
    s.append(p("Two supporting pieces make it robust: a <b>trace logger</b> that records every "
               "step to the console and a JSONL file, and a <b>fallback</b> that returns a safe "
               "answer if the LLM errors or the step budget runs out (and the search tool falls "
               "back to bundled fixtures if the web is unavailable)."))
    s.append(Paragraph("Why these choices", styles["H3"]))
    s.append(bullets([
        "<b>Free + zero infra:</b> Groq's free tier (Llama 3) for the LLM, DuckDuckGo for search.",
        "<b>Custom loop, not a framework:</b> the deliverable is the reasoning trace, so I kept "
        "the loop small (~40 lines) and readable instead of hiding it in LangChain.",
        "<b>Structured JSON every step:</b> validated with Pydantic for clean parsing.",
    ]))

    s.append(Paragraph("3. The app in action", styles["H2"]))
    s.append(p("A simple Streamlit UI wraps the same agent. These are real runs (Groq + live "
               "DuckDuckGo search)."))
    s.append(Paragraph("Example A — \"What is the treatment for the common cold?\"", styles["H3"]))
    s += img("cold_answer.png", "The agent answers and lists the sources it actually used.")
    s.append(p("The nice part is the trace below: the agent's first search returned weak results, "
               "so it noticed and searched again with a better query before answering — genuine "
               "reasoning, not a single canned lookup:"))
    s += img("cold_reasoning_trace.png")
    s.append(Paragraph("Example B — \"How to cure acne marks?\"", styles["H3"]))
    s += img("acne_answer.png", "A different topic, same clean behavior, with Mayo/NIH/NHS sources.")
    s += img("acne_reasoning_trace.png")

    s.append(Paragraph("4. A full reasoning trace (text)", styles["H2"]))
    s.append(p("The same common-cold run captured from the terminal — the exact reasoning chain, "
               "tool calls, and final output:"))
    s.append(code(
        "[QUERY] what is treatment for common cold?\n\n"
        "[THOUGHT]  I need to find evidence-based recommendations for treating the common cold.\n"
        "[ACTION]   search_medical_database('treatment for the common cold')\n"
        "[OBSERVE]  3 results - weak / non-authoritative sources\n\n"
        "[THOUGHT]  These results aren't from reputable sources. I should search again\n"
        "           with a more specific query.\n"
        "[ACTION]   search_medical_database('evidence-based treatment for the common cold')\n"
        "[OBSERVE]  3 results - CDC; review article; UpToDate\n\n"
        "[THOUGHT]  Reputable sources (CDC, UpToDate) point to symptom management and prevention.\n"
        "[ANSWER]   The common cold is typically managed by alleviating symptoms - OTC\n"
        "           pain/fever medicine, rest, and hydration. This is general information,\n"
        "           not a substitute for professional medical advice.\n"
        "[SOURCES]  cdc.gov/common-cold/treatment, jaci-global.org/..., uptodate.com/..."
    ))

    s.append(Paragraph("5. Evaluation", styles["H2"]))
    s.append(p("5 scenarios in tests/scenarios.json, run by evaluate.py, checking each answer "
               "against simple expectations. It runs fully offline (mock LLM + fixtures), so "
               "results are deterministic."))
    rows = [
        ["#", "Scenario", "What it checks", "Result"],
        ["1", "Type 2 diabetes treatment", "mentions metformin, cites sources", "PASS"],
        ["2", "First-line hypertension therapy", "mentions a first-line drug class", "PASS"],
        ["3", "Asthma long-term treatment", "mentions corticosteroid", "PASS"],
        ["4", "Empty query", "guard-rail rejects the input", "PASS"],
        ["5", "Unknown topic", "falls back to general trusted sources", "PASS"],
    ]
    data = [[Paragraph(c, styles["Cell"]) for c in row] for row in rows]
    table = Table(data, colWidths=[0.4 * inch, 1.9 * inch, 3.1 * inch, 0.7 * inch])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f4f6")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    s.append(table)
    s.append(Spacer(1, 6))
    s.append(p("<b>Score: 5/5.</b>"))

    s.append(Paragraph("6. Design decisions &amp; trade-offs", styles["H2"]))
    s.append(bullets([
        "<b>DuckDuckGo instead of PubMed.</b> Same engineering for free; trade-off is lower "
        "medical authority — acceptable given the assignment values engineering over accuracy.",
        "<b>Custom ReAct over LangChain.</b> Smaller, clearer, no dependency churn; trade-off "
        "is no built-in memory, which this scope doesn't need.",
        "<b>Mock LLM + offline fixtures.</b> The project and its evaluation run with no key and "
        "no network; switching to Groq is one env-var change.",
        "<b>Degrade gracefully.</b> LLM error → retry then fallback; search failure → fixtures; "
        "too many steps → safe answer. It never just crashes on the user.",
    ]))

    s.append(Paragraph("7. How to run it", styles["H2"]))
    s.append(code(
        "pip3 install -r requirements.txt\n"
        "cp .env.example .env          # add your free Groq key (console.groq.com/keys)\n\n"
        "# Ask a question (Groq + live web search):\n"
        "python3 -m src.agent --domain healthcare --query \"Treatment options for Type 2 diabetes?\"\n\n"
        "# Or launch the UI:\n"
        "python3 -m streamlit run app.py"
    ))
    s.append(Spacer(1, 8))
    s.append(Paragraph("Educational demo only — not a substitute for professional medical advice.",
                       styles["Caption"]))

    doc.build(s)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    build()
