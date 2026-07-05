from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
import pandas as pd
import json
import os
from PyPDF2 import PdfMerger
import argparse

from services.repository_service import RepositoryService
from repositories.session_repository import SessionRepository
from services.rubric_service import RubricService


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


def get_normalized_score_out_of_20(evaluation):
    """Extract normalized score out of 20 from evaluation."""
    if not isinstance(evaluation, dict):
        return None
    final = evaluation.get("final", {})
    if not isinstance(final, dict):
        return None

    try:
        if "normalized_to_20" in final:
            return round(float(final["normalized_to_20"]), 2)
        
        if "total_out_of_80" in final:
            return round((float(final["total_out_of_80"]) / 80) * 20, 2)
    except (ValueError, TypeError):
        pass

    return None


def as_yes_no(value):
    text = str(value).strip().lower()
    if text in {"true", "1", "yes"}:
        return "Yes"
    if text in {"false", "0", "no"}:
        return "No"
    return "N/A"


parser = argparse.ArgumentParser()
parser.add_argument("--session-id", required=True)
args = parser.parse_args()
store = RepositoryService()
session_record = SessionRepository().get(args.session_id)
saved_repositories = [repo for repo in store.list_repositories(args.session_id) if repo["status"] == "Completed"]


def resolve_rubric_snapshot(repo_row=None):
    version_id = None
    if isinstance(repo_row, dict):
        version_id = repo_row.get("evaluation_rubric_version_id") or repo_row.get("rubric_version_id")
    if not version_id:
        version_id = session_record.get("rubric_version_id")
    rubric_config = RubricService().get_version(version_id) if version_id else None
    if rubric_config:
        return {
            "name": rubric_config.get("name") or session_record.get("rubric_name") or "C Programming - Banking Transaction Assignment",
            "version": rubric_config.get("version") or session_record.get("rubric_version") or 1,
            "type": rubric_config.get("rubric_type") or session_record.get("rubric_type") or "System",
            "config": rubric_config,
            "max_score": float(rubric_config.get("total_score", 80) or 80),
            "category_max_scores": {item["code"]: float(item["max_score"]) for item in rubric_config.get("categories", [])},
            "question_titles": {item["code"]: item["name"] for item in rubric_config.get("categories", [])},
        }
    return {
        "name": session_record.get("rubric_name") or "C Programming - Banking Transaction Assignment",
        "version": session_record.get("rubric_version") or 1,
        "type": session_record.get("rubric_type") or "System",
        "config": None,
        "max_score": 80,
        "category_max_scores": {},
        "question_titles": {},
    }


report_rubric = resolve_rubric_snapshot(saved_repositories[0] if saved_repositories else None)
rubric_name = report_rubric["name"]
rubric_version = report_rubric["version"]
rubric_type = report_rubric["type"]
rubric_max_score = report_rubric["max_score"]
category_max_scores = report_rubric["category_max_scores"]
repo_df = pd.DataFrame([repo["repo_data"] for repo in saved_repositories], columns=["roll_number", "repo", "public", "readme_exists", "commit_count"])
eval_df = pd.DataFrame([
    {**repo["evaluation_data"], "evaluation": json.dumps(repo["evaluation_data"]["evaluation"])}
    for repo in saved_repositories
], columns=["roll_number", "repo", "evaluation"])
plag_df = pd.DataFrame(store.plagiarism(args.session_id), columns=["roll1", "roll2", "similarity"])

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

# Question metadata for display
question_info = {}


def get_plagiarism(roll):
    if plag_df.empty:
        return plag_df
    return plag_df[(plag_df["roll1"] == roll) | (plag_df["roll2"] == roll)]


def format_criterion_name(name):
    """Convert criterion name to readable format."""
    return name.replace("_", " ").title()


def build_question_table(question_data):
    """Build evaluation table for a single question."""
    table_data = [[
        Paragraph("<b>Criterion</b>", body_style),
        Paragraph("<b>Score</b>", body_style),
        Paragraph("<b>Remarks</b>", body_style)
    ]]

    for criterion, value in question_data.items():
        if criterion == "total":
            continue
        
        if isinstance(value, dict):
            score = value.get("score", 0)
            remarks = value.get("remarks", "")
            table_data.append([
                Paragraph(format_criterion_name(criterion), body_style),
                Paragraph(str(score), body_style),
                Paragraph(str(remarks), body_style),  # Allow full remarks text with wrapping
            ])

    # Increased criterion width (200) to accommodate full criterion names, reduced remarks slightly (260)
    table = Table(table_data, colWidths=[200, 50, 260], repeatRows=1)
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


# Generate individual student reports
for roll in all_rolls:
    repo = repo_map.loc[roll].to_dict() if roll in repo_map.index else {}
    eval_row = eval_map.loc[roll].to_dict() if roll in eval_map.index else {}
    evaluation = eval_row.get("evaluation_obj", {})
    rubric_snapshot = resolve_rubric_snapshot(repo)
    rubric_name = rubric_snapshot["name"]
    rubric_version = rubric_snapshot["version"]
    rubric_type = rubric_snapshot["type"]
    rubric_config = rubric_snapshot["config"]
    rubric_max_score = rubric_snapshot["max_score"]
    category_max_scores = rubric_snapshot["category_max_scores"]
    question_titles = rubric_snapshot["question_titles"]

    doc = SimpleDocTemplate(
        f"student_reports/{roll}.pdf",
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=28,
        bottomMargin=28,
    )
    content = []

    # Header
    content.append(Paragraph("Student Evaluation Report", title_style))
    content.append(Spacer(1, 8))
    content.append(Paragraph(f"<b>Roll Number:</b> {roll}", body_style))
    content.append(Paragraph(f"<b>Repository:</b> {repo.get('repo') or eval_row.get('repo') or 'Not available'}", body_style))
    content.append(Paragraph(f"<b>Rubric:</b> {rubric_name} · Version {rubric_version} · {rubric_type}", body_style))
    content.append(Spacer(1, 10))

    # Repository Information
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

    # Overall Score Summary
    final_data = evaluation.get("final", {}) if isinstance(evaluation, dict) else {}
    total_out_of_80 = final_data.get("total_out_of_80", "N/A")
    normalized_to_20 = final_data.get("normalized_to_20", "N/A")
    overall_remarks = final_data.get("overall_remarks", "Evaluation not available.")

    content.append(Paragraph("FINAL SCORE SUMMARY", subtitle_style))
    summary_table = Table(
        [
            [Paragraph(f"<b>Total Out of {rubric_max_score:g}</b>", body_style), Paragraph(str(total_out_of_80), body_style)],
            [Paragraph("<b>Normalized to 20</b>", body_style), Paragraph(str(normalized_to_20), body_style)],
        ],
        colWidths=[200, 310],
    )
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8F4F8")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#173A63")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9EB9D4")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FBFD")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    content.append(summary_table)
    content.append(Spacer(1, 8))
    content.append(Paragraph(f"<b>Overall Remarks:</b> {overall_remarks}", body_style))
    content.append(Spacer(1, 12))

    # Question-wise Evaluation
    content.append(Paragraph("QUESTION-WISE EVALUATION", section_style))
    questions = evaluation.get("questions", {}) if isinstance(evaluation, dict) else {}
    
    if questions:
        for question_id in sorted(questions.keys()):
            question_data = questions[question_id]
            if not isinstance(question_data, dict):
                continue
            
            # Question header
            question_title = question_titles.get(question_id, question_info.get(question_id, question_id)) or question_id
            question_total = question_data.get("total", 0)
            content.append(Paragraph(f"<b>{question_id}: {question_title}</b> (Total: {question_total}/{category_max_scores.get(question_id, 8):g})", section_style))
            
            # Question evaluation table
            content.append(build_question_table(question_data))
            content.append(Spacer(1, 8))
    else:
        content.append(Paragraph("Question-wise evaluation details are not available.", body_style))
        content.append(Spacer(1, 8))

    # Plagiarism Check
    content.append(PageBreak())
    content.append(Paragraph("PLAGIARISM CHECK", section_style))
    plag_matches = get_plagiarism(roll)
    if plag_matches.empty:
        content.append(Paragraph("No high-similarity plagiarism matches found (threshold: 0.80).", body_style))
    else:
        rows = [[Paragraph("<b>Other Roll</b>", body_style), Paragraph("<b>Similarity</b>", body_style)]]
        for _, row in plag_matches.sort_values("similarity", ascending=False).iterrows():
            other = row["roll2"] if row["roll1"] == roll else row["roll1"]
            sim_value = float(row["similarity"])
            rows.append([Paragraph(str(other), body_style), Paragraph(f"{sim_value:.2%}", body_style)])
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
    """Generate consolidated report with summary statistics and question-wise breakdown."""
    doc = SimpleDocTemplate("preamble.pdf", pagesize=A4, rightMargin=30, leftMargin=30, topMargin=28, bottomMargin=28)
    content = []

    # Collect scores from all evaluations
    all_scores = []  # List of tuples: (roll, total_out_of_80, normalized_to_20)
    
    for roll in all_rolls:
        evaluation = eval_map.loc[roll]["evaluation_obj"] if roll in eval_map.index else {}
        final = evaluation.get("final", {}) if isinstance(evaluation, dict) else {}
        try:
            total_out_of_80 = float(final.get("total_out_of_80", 0))
            normalized_to_20 = float(final.get("normalized_to_20", 0))
            all_scores.append((roll, total_out_of_80, normalized_to_20))
        except (ValueError, TypeError):
            pass

    # Calculate statistics
    total_students = len(all_rolls)
    evaluated_students = len(all_scores)
    scores_80 = [score[1] for score in all_scores]
    scores_20 = [score[2] for score in all_scores]
    
    avg_score_80 = round(sum(scores_80) / evaluated_students, 2) if evaluated_students > 0 else 0
    avg_score_20 = round(sum(scores_20) / evaluated_students, 2) if evaluated_students > 0 else 0
    max_score_80 = max(scores_80) if scores_80 else 0
    max_score_20 = max(scores_20) if scores_20 else 0
    min_score_80 = min(scores_80) if scores_80 else 0
    min_score_20 = min(scores_20) if scores_20 else 0
    high_plag = plag_df[plag_df["similarity"] >= 0.8]

    # Title
    content.append(Paragraph("Consolidated Evaluation Report", title_style))
    content.append(Spacer(1, 14))
    content.append(Paragraph(f"<b>Rubric:</b> {report_rubric['name']} · Version {report_rubric['version']} · {report_rubric['type']}", body_style))
    content.append(Spacer(1, 10))

    # Summary Statistics
    content.append(Paragraph("SUMMARY STATISTICS", section_style))
    summary_table = Table(
        [
            [Paragraph("<b>Total Students</b>", body_style), Paragraph(str(total_students), body_style)],
            [Paragraph("<b>Evaluated Students</b>", body_style), Paragraph(str(evaluated_students), body_style)],
            [Paragraph(f"<b>Average Score (out of {rubric_max_score:g})</b>", body_style), Paragraph(f"{avg_score_80}", body_style)],
            [Paragraph("<b>Average Score (out of 20)</b>", body_style), Paragraph(f"{avg_score_20}", body_style)],
            [Paragraph(f"<b>Highest Score (out of {rubric_max_score:g})</b>", body_style), Paragraph(str(max_score_80), body_style)],
            [Paragraph(f"<b>Lowest Score (out of {rubric_max_score:g})</b>", body_style), Paragraph(str(min_score_80), body_style)],
            [Paragraph("<b>Plagiarism Cases (≥ 0.80)</b>", body_style), Paragraph(str(len(high_plag)), body_style)],
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
    content.append(Spacer(1, 14))

    # Student Overview
    content.append(Paragraph("STUDENT COVERAGE OVERVIEW", subtitle_style))
    overview_rows = [[
        Paragraph("<b>Roll No</b>", body_style),
        Paragraph(f"<b>Out of {rubric_max_score:g}</b>", body_style),
        Paragraph("<b>Out of 20</b>", body_style),
        Paragraph("<b>Commits</b>", body_style),
        Paragraph("<b>Public</b>", body_style),
        Paragraph("<b>README</b>", body_style),
    ]]
    
    for roll, total_80, total_20 in all_scores:
        repo = repo_map.loc[roll].to_dict() if roll in repo_map.index else {}
        overview_rows.append([
            Paragraph(roll, body_style),
            Paragraph(str(total_80), body_style),
            Paragraph(str(total_20), body_style),
            Paragraph(str(repo.get("commit_count", "N/A")), body_style),
            Paragraph(as_yes_no(repo.get("public", "")), body_style),
            Paragraph(as_yes_no(repo.get("readme_exists", "")), body_style),
        ])

    overview_table = Table(overview_rows, colWidths=[100, 80, 80, 80, 80, 95], repeatRows=1)
    overview_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DDEAF7")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#173A63")),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#9EB9D4")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
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
