"""
Automated Quiz Grading System
Reads student answers from CSV, compares with answer key,
calculates marks, and generates detailed performance reports.
"""

import csv
import os
from datetime import datetime
from collections import defaultdict


# ─────────────────────────────────────────────
#  LOADING
# ─────────────────────────────────────────────

def load_answer_key(filepath: str) -> dict:
    """
    Load the answer key CSV.
    Expected format:
        question_number, correct_answer, marks
        1, A, 2
        2, C, 1
    Returns: {question_number (int): {"answer": str, "marks": int}}
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Answer key not found: {filepath}")

    key = {}
    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        # Normalize header names (strip whitespace, lowercase)
        reader.fieldnames = [h.strip().lower() for h in reader.fieldnames]

        required = {"question_number", "correct_answer", "marks"}
        if not required.issubset(set(reader.fieldnames)):
            missing = required - set(reader.fieldnames)
            raise ValueError(f"Answer key missing columns: {missing}")

        for row in reader:
            qnum = int(row["question_number"].strip())
            key[qnum] = {
                "answer": row["correct_answer"].strip().upper(),
                "marks": int(row["marks"].strip()),
            }
    return key


def load_student_answers(filepath: str) -> list[dict]:
    """
    Load student answers CSV.
    Expected format:
        student_id, name, q1, q2, q3, ...
        S001, Ali Hassan, A, B, C, ...
    Returns: list of dicts per student.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Student answers file not found: {filepath}")

    students = []
    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        reader.fieldnames = [h.strip().lower() for h in reader.fieldnames]

        if "student_id" not in reader.fieldnames or "name" not in reader.fieldnames:
            raise ValueError("Student file must have 'student_id' and 'name' columns.")

        for row in reader:
            student = {
                "student_id": row["student_id"].strip(),
                "name": row["name"].strip(),
                "answers": {},
            }
            for key, val in row.items():
                if key.startswith("q"):
                    try:
                        qnum = int(key[1:])
                        student["answers"][qnum] = val.strip().upper() if val.strip() else ""
                    except ValueError:
                        pass
            students.append(student)
    return students


# ─────────────────────────────────────────────
#  GRADING
# ─────────────────────────────────────────────

def grade_student(student: dict, answer_key: dict) -> dict:
    """
    Compare a student's answers against the key.
    Returns a result dict with per-question breakdown + totals.
    """
    total_marks = sum(q["marks"] for q in answer_key.values())
    obtained = 0
    breakdown = {}

    for qnum, key_info in answer_key.items():
        student_ans = student["answers"].get(qnum, "")
        correct_ans = key_info["answer"]
        q_marks = key_info["marks"]

        is_correct = student_ans == correct_ans
        earned = q_marks if is_correct else 0
        obtained += earned

        breakdown[qnum] = {
            "student_answer": student_ans if student_ans else "—",
            "correct_answer": correct_ans,
            "is_correct": is_correct,
            "marks_earned": earned,
            "marks_possible": q_marks,
        }

    percentage = round((obtained / total_marks) * 100, 2) if total_marks > 0 else 0.0

    return {
        "student_id": student["student_id"],
        "name": student["name"],
        "obtained": obtained,
        "total": total_marks,
        "percentage": percentage,
        "grade": assign_grade(percentage),
        "breakdown": breakdown,
    }


def assign_grade(percentage: float) -> str:
    if percentage >= 90:
        return "A+"
    elif percentage >= 80:
        return "A"
    elif percentage >= 70:
        return "B"
    elif percentage >= 60:
        return "C"
    elif percentage >= 50:
        return "D"
    else:
        return "F"


def grade_all(students: list[dict], answer_key: dict) -> list[dict]:
    return [grade_student(s, answer_key) for s in students]


# ─────────────────────────────────────────────
#  ANALYTICS
# ─────────────────────────────────────────────

def compute_analytics(results: list[dict], answer_key: dict) -> dict:
    """Compute class-wide statistics and per-question analysis."""
    percentages = [r["percentage"] for r in results]
    obtained_list = [r["obtained"] for r in results]

    # Per-question difficulty: how many students got it right
    question_stats = defaultdict(lambda: {"correct": 0, "total": 0})
    for r in results:
        for qnum, detail in r["breakdown"].items():
            question_stats[qnum]["total"] += 1
            if detail["is_correct"]:
                question_stats[qnum]["correct"] += 1

    question_difficulty = {}
    for qnum, stats in question_stats.items():
        pct = round((stats["correct"] / stats["total"]) * 100, 1) if stats["total"] > 0 else 0
        question_difficulty[qnum] = {
            "correct_count": stats["correct"],
            "total_students": stats["total"],
            "success_rate": pct,
            "difficulty": "Easy" if pct >= 70 else ("Medium" if pct >= 40 else "Hard"),
        }

    grade_distribution = defaultdict(int)
    for r in results:
        grade_distribution[r["grade"]] += 1

    return {
        "class_size": len(results),
        "max_marks": results[0]["total"] if results else 0,
        "highest": max(obtained_list) if obtained_list else 0,
        "lowest": min(obtained_list) if obtained_list else 0,
        "average": round(sum(percentages) / len(percentages), 2) if percentages else 0,
        "pass_count": sum(1 for p in percentages if p >= 50),
        "fail_count": sum(1 for p in percentages if p < 50),
        "grade_distribution": dict(grade_distribution),
        "question_difficulty": question_difficulty,
    }


# ─────────────────────────────────────────────
#  REPORT GENERATION
# ─────────────────────────────────────────────

def generate_summary_csv(results: list[dict], analytics: dict, output_path: str):
    """Write a summary CSV with one row per student."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Rank", "Student ID", "Name",
            "Marks Obtained", "Total Marks", "Percentage (%)", "Grade"
        ])
        sorted_results = sorted(results, key=lambda x: x["obtained"], reverse=True)
        for rank, r in enumerate(sorted_results, 1):
            writer.writerow([
                rank,
                r["student_id"],
                r["name"],
                r["obtained"],
                r["total"],
                r["percentage"],
                r["grade"],
            ])
    print(f"  ✔  Summary CSV saved → {output_path}")


def generate_detailed_csv(results: list[dict], answer_key: dict, output_path: str):
    """Write a detailed CSV with per-question breakdown for every student."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    question_nums = sorted(answer_key.keys())

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        # Header row
        header = ["Student ID", "Name"]
        for qnum in question_nums:
            header += [f"Q{qnum} Answer", f"Q{qnum} Correct?", f"Q{qnum} Marks"]
        header += ["Total Obtained", "Total Possible", "Percentage", "Grade"]
        writer.writerow(header)

        for r in sorted(results, key=lambda x: x["student_id"]):
            row = [r["student_id"], r["name"]]
            for qnum in question_nums:
                bd = r["breakdown"].get(qnum, {})
                row += [
                    bd.get("student_answer", "—"),
                    "✓" if bd.get("is_correct") else "✗",
                    bd.get("marks_earned", 0),
                ]
            row += [r["obtained"], r["total"], r["percentage"], r["grade"]]
            writer.writerow(row)
    print(f"  ✔  Detailed CSV saved → {output_path}")


def generate_text_report(results: list[dict], analytics: dict, output_path: str):
    """Generate a human-readable .txt performance report."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sorted_results = sorted(results, key=lambda x: x["obtained"], reverse=True)

    lines = []
    lines.append("=" * 65)
    lines.append("        AUTOMATED QUIZ GRADING SYSTEM — PERFORMANCE REPORT")
    lines.append("=" * 65)
    lines.append(f"  Generated : {timestamp}")
    lines.append(f"  Class Size: {analytics['class_size']} students")
    lines.append(f"  Max Marks : {analytics['max_marks']}")
    lines.append("")

    # ── Class Statistics ──
    lines.append("─" * 65)
    lines.append("  CLASS STATISTICS")
    lines.append("─" * 65)
    lines.append(f"  Average Score  : {analytics['average']}%")
    lines.append(f"  Highest Score  : {analytics['highest']} marks")
    lines.append(f"  Lowest Score   : {analytics['lowest']} marks")
    lines.append(f"  Students Passed: {analytics['pass_count']}")
    lines.append(f"  Students Failed: {analytics['fail_count']}")
    lines.append("")

    # ── Grade Distribution ──
    lines.append("─" * 65)
    lines.append("  GRADE DISTRIBUTION")
    lines.append("─" * 65)
    for grade in ["A+", "A", "B", "C", "D", "F"]:
        count = analytics["grade_distribution"].get(grade, 0)
        bar = "█" * count
        lines.append(f"  {grade:3}  {bar:20} {count} student(s)")
    lines.append("")

    # ── Question Difficulty ──
    lines.append("─" * 65)
    lines.append("  QUESTION DIFFICULTY ANALYSIS")
    lines.append("─" * 65)
    lines.append(f"  {'Q#':<6} {'Success Rate':>14}  {'Correct/Total':>14}  Difficulty")
    for qnum, stat in sorted(analytics["question_difficulty"].items()):
        lines.append(
            f"  Q{qnum:<5} {stat['success_rate']:>13}%  "
            f"{stat['correct_count']}/{stat['total_students']:>10}   {stat['difficulty']}"
        )
    lines.append("")

    # ── Individual Results ──
    lines.append("─" * 65)
    lines.append("  STUDENT RESULTS  (ranked by score)")
    lines.append("─" * 65)
    lines.append(f"  {'Rank':<6} {'ID':<10} {'Name':<22} {'Score':>7}  {'%':>7}  Grade")
    lines.append("  " + "-" * 60)
    for rank, r in enumerate(sorted_results, 1):
        lines.append(
            f"  {rank:<6} {r['student_id']:<10} {r['name']:<22} "
            f"{r['obtained']}/{r['total']:>3}  {r['percentage']:>6}%  {r['grade']}"
        )
    lines.append("")
    lines.append("=" * 65)
    lines.append("                        END OF REPORT")
    lines.append("=" * 65)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  ✔  Text report saved  → {output_path}")


# ─────────────────────────────────────────────
#  MAIN PIPELINE
# ─────────────────────────────────────────────

def run_grading_pipeline(
    answer_key_path: str,
    student_answers_path: str,
    reports_dir: str = "reports",
):
    print("\n" + "=" * 55)
    print("   AUTOMATED QUIZ GRADING SYSTEM")
    print("=" * 55)

    # 1. Load data
    print("\n[1/4] Loading data...")
    answer_key = load_answer_key(answer_key_path)
    students = load_student_answers(student_answers_path)
    print(f"      Questions loaded : {len(answer_key)}")
    print(f"      Students loaded  : {len(students)}")

    # 2. Grade
    print("\n[2/4] Grading...")
    results = grade_all(students, answer_key)
    print(f"      Graded {len(results)} student(s).")

    # 3. Analytics
    print("\n[3/4] Computing analytics...")
    analytics = compute_analytics(results, answer_key)
    print(f"      Class average : {analytics['average']}%")
    print(f"      Pass / Fail   : {analytics['pass_count']} / {analytics['fail_count']}")

    # 4. Reports
    print("\n[4/4] Generating reports...")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    generate_summary_csv(results, analytics, os.path.join(reports_dir, f"summary_{ts}.csv"))
    generate_detailed_csv(results, answer_key, os.path.join(reports_dir, f"detailed_{ts}.csv"))
    generate_text_report(results, analytics, os.path.join(reports_dir, f"report_{ts}.txt"))

    print("\n" + "=" * 55)
    print("   GRADING COMPLETE ✔")
    print("=" * 55 + "\n")

    return results, analytics


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    BASE = os.path.dirname(__file__)
    run_grading_pipeline(
        answer_key_path=os.path.join(BASE, "data", "answer_key.csv"),
        student_answers_path=os.path.join(BASE, "data", "student_answers.csv"),
        reports_dir=os.path.join(BASE, "reports"),
    )
