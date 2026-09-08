"""Create fictional workshop PDFs for Demo Institute of Technology."""
import argparse
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen.canvas import Canvas

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "data" / "documents"

DOCUMENTS = {
    "demo_attendance_policy.pdf": ("Attendance Policy", [
        "This is a fictional workshop policy for Demo Institute of Technology.",
        "Students must maintain at least 75 percent attendance in each course to be eligible for the end-semester examination.",
        "Medical absence requests require a medical certificate submitted to the department within five working days of return.",
    ]),
    "demo_examination_guidelines.pdf": ("Examination Guidelines", [
        "This is a fictional workshop policy for Demo Institute of Technology.",
        "Examination eligibility requires 75 percent course attendance and payment of all examination fees before the published deadline.",
        "Students must carry their institute identity card and hall ticket to every examination.",
    ]),
    "demo_placement_guidelines.pdf": ("Placement Guidelines", [
        "This is a fictional workshop policy for Demo Institute of Technology.",
        "Placement registration requires a current resume, student identity card, semester mark sheets, and a signed placement declaration.",
        "Students with no active disciplinary case and a cumulative GPA of 6.5 or higher may register for campus placements.",
    ]),
    "demo_internship_policy.pdf": ("Internship Policy", [
        "This is a fictional workshop policy for Demo Institute of Technology.",
        "Students must obtain department approval before beginning a credited internship.",
        "An internship report and supervisor evaluation must be submitted within ten working days after completion.",
    ]),
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--document",
        choices=("all", "attendance", "examination", "placement", "internship"),
        default="all",
        help="Generate all demo PDFs or one selected policy.",
    )
    args = parser.parse_args()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for filename, (title, lines) in DOCUMENTS.items():
        if args.document != "all" and args.document not in filename:
            continue
        path = OUTPUT / filename
        canvas = Canvas(str(path), pagesize=A4)
        canvas.setTitle(f"{title} — Fictional Workshop Document")
        text = canvas.beginText(72, 770)
        text.setFont("Helvetica-Bold", 17); text.textLine(title); text.textLine("")
        text.setFont("Helvetica", 11)
        for line in lines:
            for offset in range(0, len(line), 90):
                text.textLine(line[offset:offset + 90])
            text.textLine("")
        canvas.drawText(text); canvas.save()
        print(f"Created {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
