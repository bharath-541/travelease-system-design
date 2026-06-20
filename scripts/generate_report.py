import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "PROJECT_DOCUMENTATION.md"
OUTPUT = ROOT / "output" / "pdf" / "TravelEase_Project_Documentation.pdf"

IMAGE_PATTERN = re.compile(r"^<IMAGE:(.+?)\|(.+)>$")


def page_footer(canvas, document):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#d4cdbf"))
    canvas.line(48, 38, A4[0] - 48, 38)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#65706b"))
    canvas.drawString(48, 24, "TravelEase System Design Project")
    canvas.drawRightString(A4[0] - 48, 24, f"Page {document.page}")
    canvas.restoreState()


def build_styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            "CoverTitle",
            parent=styles["Title"],
            fontName="Times-Bold",
            fontSize=30,
            leading=35,
            textColor=colors.HexColor("#063f3b"),
            alignment=TA_CENTER,
            spaceAfter=18,
        )
    )
    styles.add(
        ParagraphStyle(
            "CoverSub",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=12,
            leading=18,
            textColor=colors.HexColor("#65706b"),
            alignment=TA_CENTER,
        )
    )
    styles.add(
        ParagraphStyle(
            "H1Custom",
            parent=styles["Heading1"],
            fontName="Times-Bold",
            fontSize=20,
            leading=24,
            textColor=colors.HexColor("#063f3b"),
            spaceBefore=14,
            spaceAfter=10,
        )
    )
    styles.add(
        ParagraphStyle(
            "H2Custom",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=17,
            textColor=colors.HexColor("#b33d32"),
            spaceBefore=10,
            spaceAfter=7,
        )
    )
    styles.add(
        ParagraphStyle(
            "BodyCustom",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.4,
            leading=14.2,
            textColor=colors.HexColor("#17201e"),
            spaceAfter=7,
        )
    )
    styles.add(
        ParagraphStyle(
            "BulletCustom",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.2,
            leading=13.5,
            leftIndent=16,
            firstLineIndent=-8,
            bulletIndent=4,
            textColor=colors.HexColor("#17201e"),
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            "CaptionCustom",
            parent=styles["BodyText"],
            fontName="Helvetica-Oblique",
            fontSize=8,
            leading=11,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#65706b"),
            spaceBefore=5,
            spaceAfter=12,
        )
    )
    return styles


def add_image(story, relative_path, caption, styles):
    path = ROOT / relative_path
    if not path.exists():
        story.append(
            Paragraph(
                f"<i>{caption} will be added after browser verification.</i>",
                styles["CaptionCustom"],
            )
        )
        return
    max_width = 7.15 * inch
    max_height = 8.2 * inch
    image = Image(str(path))
    scale = min(max_width / image.imageWidth, max_height / image.imageHeight, 1)
    image.drawWidth = image.imageWidth * scale
    image.drawHeight = image.imageHeight * scale
    story.append(
        KeepTogether(
            [
                image,
                Paragraph(caption, styles["CaptionCustom"]),
            ]
        )
    )


def parse_markdown(styles):
    lines = SOURCE.read_text(encoding="utf-8").splitlines()
    story = []
    in_code = False
    code_lines = []
    paragraph_lines = []

    def flush_paragraph():
        if paragraph_lines:
            text = " ".join(line.strip() for line in paragraph_lines)
            story.append(Paragraph(text, styles["BodyCustom"]))
            paragraph_lines.clear()

    for line in lines[1:]:
        stripped = line.strip()
        if stripped.startswith("```"):
            flush_paragraph()
            if in_code:
                story.append(
                    Preformatted(
                        "\n".join(code_lines),
                        ParagraphStyle(
                            "CodeCustom",
                            fontName="Courier",
                            fontSize=7.4,
                            leading=10,
                            leftIndent=10,
                            rightIndent=10,
                            borderColor=colors.HexColor("#d4cdbf"),
                            borderWidth=0.6,
                            borderPadding=8,
                            backColor=colors.HexColor("#f4f0e6"),
                            spaceAfter=10,
                        ),
                    )
                )
                code_lines.clear()
            in_code = not in_code
            continue
        if in_code:
            code_lines.append(line)
            continue
        if not stripped:
            flush_paragraph()
            continue
        image_match = IMAGE_PATTERN.match(stripped)
        if image_match:
            flush_paragraph()
            add_image(story, image_match.group(1), image_match.group(2), styles)
            continue
        if stripped.startswith("## "):
            flush_paragraph()
            story.append(Spacer(1, 4))
            story.append(Paragraph(stripped[3:], styles["H1Custom"]))
            continue
        if stripped.startswith("### "):
            flush_paragraph()
            story.append(Paragraph(stripped[4:], styles["H2Custom"]))
            continue
        if stripped.startswith("- "):
            flush_paragraph()
            story.append(
                Paragraph(
                    stripped[2:],
                    styles["BulletCustom"],
                    bulletText="•",
                )
            )
            continue
        if re.match(r"^\d+\.\s", stripped):
            flush_paragraph()
            number, text = stripped.split(".", 1)
            story.append(
                Paragraph(
                    text.strip(),
                    styles["BulletCustom"],
                    bulletText=f"{number}.",
                )
            )
            continue
        paragraph_lines.append(stripped)

    flush_paragraph()
    return story


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    styles = build_styles()
    document = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        rightMargin=48,
        leftMargin=48,
        topMargin=52,
        bottomMargin=50,
        title="TravelEase Project Documentation",
        author="Perni Bharath Raghavendra",
    )
    story = [
        Spacer(1, 1.35 * inch),
        Paragraph("TravelEase", styles["CoverTitle"]),
        Paragraph(
            "Designing a Scalable Travel Booking Platform",
            styles["CoverSub"],
        ),
        Spacer(1, 0.4 * inch),
        Paragraph(
            "System Design Final Examination Project",
            styles["CoverSub"],
        ),
        Spacer(1, 0.55 * inch),
        Paragraph(
            "Student Name: Perni Bharath Raghavendra",
            styles["CoverSub"],
        ),
        Paragraph("Roll Number: 150096724139", styles["CoverSub"]),
        Paragraph("Programme: B.Tech CSE, Semester 4", styles["CoverSub"]),
        Paragraph("Cohort: Mark Zuckerberg Cohort", styles["CoverSub"]),
        Paragraph("University: ITM Skills University", styles["CoverSub"]),
        Paragraph("Course: System Design", styles["CoverSub"]),
        Paragraph(
            "GitHub Repository: github.com/bharath-541/travelease-system-design",
            styles["CoverSub"],
        ),
        Spacer(1, 0.75 * inch),
        Paragraph(
            "Flask implementation, architecture, database design, algorithms, scalability, and fault tolerance",
            styles["CoverSub"],
        ),
        PageBreak(),
    ]
    story.extend(parse_markdown(styles))
    document.build(story, onFirstPage=page_footer, onLaterPages=page_footer)
    print(f"Generated {OUTPUT}")


if __name__ == "__main__":
    main()
