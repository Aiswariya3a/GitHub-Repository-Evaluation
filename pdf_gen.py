from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
import pandas as pd
import json
import os
from PyPDF2 import PdfMerger


def safe_read_csv(path, expected_columns=None):
    if expected_columns is None:
        expected_columns = []
    try:
        df = pd.read_csv(path, dtype=str)
    except Exception:
        df = pd.DataFrame(columns=expected_columns)
    for col in expected_columns:
        if col not in df.columns:
            df[col] = ""
    return df.fillna("")


def normalize_roll(value):
    return str(value).strip().upper()


def parse_json(value):
    if not isinstance(value, str) or not value.strip():
        return {}
    try:
        data = json.loads(value)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def normalize_to_20(evaluation):
    if not isinstance(evaluation, dict):
        return None
    final = evaluation.get("final", {})
    if not isinstance(final, dict):
        return None

    for key in ("normalized_to_20", "score_out_of_20"):
        if key in final:
            try:
                return round(float(final[key]), 2)
            except Exception:
                pass

    if "normalized_to_10" in final:
        try:
            return round(float(final["normalized_to_10"]) * 2, 2)
        except Exception:
            pass

    if "total_out_of_100" in final:
        try:
            return round(float(final["total_out_of_100"]) / 5, 2)
        except Exception:
            pass

    return None


def as_yes_no(value):
    text = str(value).strip().lower()
    if text in {"true", "1", "yes"}:
        return "Yes"
    if text in {"false", "0", "no"}:
        return "No"
    return "N/A"


repo_df = safe_read_csv("repo_report.csv", ["roll_number", "repo", "public", "readme_exists", "commit_count"])
eval_df = safe_read_csv("evaluation_report.csv", ["roll_number", "repo", "evaluation"])
plag_df = safe_read_csv("plagiarism_report.csv", ["roll1", "roll2", "similarity"])

repo_df["roll_number"] = repo_df["roll_number"].apply(normalize_roll)
eval_df["roll_number"] = eval_df["roll_number"].apply(normalize_roll)
plag_df["roll1"] = plag_df["roll1"].apply(normalize_roll)
plag_df["roll2"] = plag_df["roll2"].apply(normalize_roll)
plag_df["similarity"] = pd.to_numeric(plag_df["similarity"], errors="coerce").fillna(0.0)

eval_df["evaluation_obj"] = eval_df["evaluation"].apply(parse_json)

repo_map = repo_df.drop_duplicates("roll_number", keep="last").set_index("roll_number")
eval_map = eval_df.drop_duplicates("roll_number", keep="last").set_index("roll_number")

all_rolls = sorted(set(repo_df["roll_number"]) | set(eval_df["roll_number"]))

os.makedirs("student_reports", exist_ok=True)

styles = getSampleStyleSheet()
title_style = ParagraphStyle(name="title", parent=styles["Title"], alignment=1, textColor=colors.HexColor("#173A63"))
subtitle_style = ParagraphStyle(name="subtitle", parent=styles["Heading2"], textColor=colors.HexColor("#173A63"), spaceAfter=8)
section_style = ParagraphStyle(name="section", parent=styles["Heading3"], textColor=colors.HexColor("#1F5D8B"), spaceAfter=6)
body_style = ParagraphStyle(name="body", parent=styles["BodyText"], fontSize=9, leading=12)


def get_plagiarism(roll):
    if plag_df.empty:
        return plag_df
    return plag_df[(plag_df["roll1"] == roll) | (plag_df["roll2"] == roll)]


def build_score_table(section_data):
    table_data = [[Paragraph("<b>Criteria</b>", body_style), Paragraph("<b>Score</b>", body_style), Paragraph("<b>Remarks</b>", body_style)]]

    for criterion, value in section_data.items():
        if isinstance(value, dict):
            score = value.get("score", "N/A")
            remarks = value.get("remarks", "N/A")
            table_data.append([
                Paragraph(str(criterion).replace("_", " ").title(), body_style),
                Paragraph(str(score), body_style),
                Paragraph(str(remarks), body_style),
            ])

    table = Table(table_data, colWidths=[145, 55, 310], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DDEAF7")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#173A63")),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#9EB9D4")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F6FAFF")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


for roll in all_rolls:
    repo = repo_map.loc[roll].to_dict() if roll in repo_map.index else {}
    eval_row = eval_map.loc[roll].to_dict() if roll in eval_map.index else {}
    evaluation = eval_row.get("evaluation_obj", {})

    doc = SimpleDocTemplate(
        f"student_reports/{roll}.pdf",
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=28,
        bottomMargin=28,
    )
    content = []

    content.append(Paragraph("Student Evaluation Report", title_style))
    content.append(Spacer(1, 8))
    content.append(Paragraph(f"<b>Roll Number:</b> {roll}", body_style))
    content.append(Paragraph(f"<b>Repository:</b> {repo.get('repo') or eval_row.get('repo') or 'Not available'}", body_style))
    content.append(Spacer(1, 10))

    info_table = Table(
        [
            [Paragraph("<b>Metric</b>", body_style), Paragraph("<b>Value</b>", body_style)],
            [Paragraph("Commit Count", body_style), Paragraph(str(repo.get("commit_count", "N/A")), body_style)],
            [Paragraph("Public Repository", body_style), Paragraph(as_yes_no(repo.get("public", "")), body_style)],
            [Paragraph("README Present", body_style), Paragraph(as_yes_no(repo.get("readme_exists", "")), body_style)],
        ],
        colWidths=[180, 330],
        repeatRows=1,
    )
    info_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DDEAF7")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#173A63")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9EB9D4")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F6FAFF")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    content.append(info_table)
    content.append(Spacer(1, 12))

    score = normalize_to_20(evaluation)
    score_text = f"{score} / 20" if score is not None else "Not available"
    final = evaluation.get("final", {}) if isinstance(evaluation, dict) else {}
    remarks = final.get("overall_remarks", "Evaluation not available for this student.")

    content.append(Paragraph(f"Final Score: {score_text}", subtitle_style))
    content.append(Paragraph(f"<b>Overall Remarks:</b> {remarks}", body_style))
    content.append(Spacer(1, 12))

    scores = evaluation.get("scores", {}) if isinstance(evaluation, dict) else {}
    if scores:
        for section, section_data in scores.items():
            if not isinstance(section_data, dict):
                continue
            content.append(Paragraph(str(section).replace("_", " ").upper(), section_style))
            content.append(build_score_table(section_data))
            content.append(Spacer(1, 10))
    else:
        content.append(Paragraph("Section-wise evaluation details are not available.", body_style))
        content.append(Spacer(1, 8))

    content.append(Paragraph("PLAGIARISM CHECK", section_style))
    plag_matches = get_plagiarism(roll)
    if plag_matches.empty:
        content.append(Paragraph("No high-similarity plagiarism matches found.", body_style))
    else:
        rows = [[Paragraph("<b>Other Roll</b>", body_style), Paragraph("<b>Similarity</b>", body_style)]]
        for _, row in plag_matches.sort_values("similarity", ascending=False).iterrows():
            other = row["roll2"] if row["roll1"] == roll else row["roll1"]
            rows.append([Paragraph(str(other), body_style), Paragraph(f"{float(row['similarity']):.2f}", body_style)])
        plag_table = Table(rows, colWidths=[255, 255], repeatRows=1)
        plag_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#FCE4E4")),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D7A7A7")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FFF7F7")]),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        content.append(plag_table)

    doc.build(content)

print("Individual PDFs generated.")


def generate_preamble():
    doc = SimpleDocTemplate("preamble.pdf", pagesize=A4, rightMargin=30, leftMargin=30, topMargin=28, bottomMargin=28)
    content = []

    scored_rows = []
    for roll in all_rolls:
        evaluation = eval_map.loc[roll]["evaluation_obj"] if roll in eval_map.index else {}
        score = normalize_to_20(evaluation)
        if score is not None:
            scored_rows.append(score)

    total_students = len(all_rolls)
    evaluated_students = len(scored_rows)
    avg_score = round(sum(scored_rows) / evaluated_students, 2) if scored_rows else 0
    max_score = max(scored_rows) if scored_rows else 0
    min_score = min(scored_rows) if scored_rows else 0
    high_plag = plag_df[plag_df["similarity"] >= 0.8]

    content.append(Paragraph("Consolidated Evaluation Report", title_style))
    content.append(Spacer(1, 14))

    summary_table = Table(
        [
            [Paragraph("<b>Total Students</b>", body_style), Paragraph(str(total_students), body_style)],
            [Paragraph("<b>Evaluated Students</b>", body_style), Paragraph(str(evaluated_students), body_style)],
            [Paragraph("<b>Average Score</b>", body_style), Paragraph(f"{avg_score} / 20", body_style)],
            [Paragraph("<b>Highest Score</b>", body_style), Paragraph(str(max_score), body_style)],
            [Paragraph("<b>Lowest Score</b>", body_style), Paragraph(str(min_score), body_style)],
            [Paragraph("<b>Plagiarism Cases (>= 0.80)</b>", body_style), Paragraph(str(len(high_plag)), body_style)],
        ],
        colWidths=[250, 260],
    )
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7FBFF")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9EB9D4")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    content.append(summary_table)
    content.append(Spacer(1, 12))

    content.append(Paragraph("Student Coverage Overview", subtitle_style))
    overview_rows = [[
        Paragraph("<b>Roll Number</b>", body_style),
        Paragraph("<b>Score (/20)</b>", body_style),
        Paragraph("<b>Commits</b>", body_style),
        Paragraph("<b>Public</b>", body_style),
        Paragraph("<b>README</b>", body_style),
    ]]
    for roll in all_rolls:
        repo = repo_map.loc[roll].to_dict() if roll in repo_map.index else {}
        evaluation = eval_map.loc[roll]["evaluation_obj"] if roll in eval_map.index else {}
        score = normalize_to_20(evaluation)
        overview_rows.append([
            Paragraph(roll, body_style),
            Paragraph(str(score) if score is not None else "N/A", body_style),
            Paragraph(str(repo.get("commit_count", "N/A")), body_style),
            Paragraph(as_yes_no(repo.get("public", "")), body_style),
            Paragraph(as_yes_no(repo.get("readme_exists", "")), body_style),
        ])

    overview_table = Table(overview_rows, colWidths=[150, 85, 80, 95, 100], repeatRows=1)
    overview_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DDEAF7")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#173A63")),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#9EB9D4")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F6FAFF")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    content.append(overview_table)
    doc.build(content)


generate_preamble()
print("Preamble generated.")


def merge_pdfs():
    merger = PdfMerger()
    merger.append("preamble.pdf")

    for pdf in sorted(os.listdir("student_reports")):
        if pdf.lower().endswith(".pdf"):
            merger.append(os.path.join("student_reports", pdf))

    merger.write("Final_Consolidated_Report.pdf")
    merger.close()


merge_pdfs()
print("Final consolidated PDF created.")
