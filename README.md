# Quiz Grader 🎯

I built this because manually grading CSV answer sheets is tedious and error-prone.
You drop in an answer key and a sheet of student responses, run one command, and
get back three reports: a leaderboard, a per-question breakdown, and a full
class performance summary — all timestamped so nothing gets overwritten.

No external libraries. No database. Just Python and CSV files.

---

## What it does

- Reads student answers from a CSV file
- Compares them against your answer key (supports different marks per question)
- Calculates each student's score and assigns a letter grade
- Flags which questions the class struggled with (difficulty analysis)
- Outputs three report files automatically every time you run it

---

## Getting started

Clone the repo and set up a virtual environment:

```bash
git clone https://github.com/YOUR_USERNAME/quiz-grader.git
cd quiz-grader

python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # Mac / Linux

pip install -r requirements.txt
```

Then just run:

```bash
python grader.py
```

Reports land in the `reports/` folder.

---

## Setting up your data

Two CSV files live in the `data/` folder. Edit them before running.

**answer_key.csv** — one row per question:question_number, correct_answer, marks
1, A, 2
2, C, 1
**student_answers.csv** — one row per student, columns q1/q2/q3… match the question numbers:
student_id, name, q1, q2, q3
S001, Ali Hassan, A, C, B
S002, Sara Nawaz, B, A, B
Left a cell blank? It counts as a wrong answer.

---

## Running the tests

```bash
python -m pytest tests/test_grader.py -v
```

21 tests covering grading logic, grade boundaries, edge cases (missing answers,
zero scores, perfect scores), and the analytics engine.

---

## Output files

Every run creates three timestamped files in `reports/`:

| File | What's in it |
|------|-------------|
| `summary_*.csv` | Ranked leaderboard — ID, name, score, grade |
| `detailed_*.csv` | Every student × every question — what they answered, right or wrong |
| `report_*.txt` | Full human-readable report with class stats, grade distribution, and question difficulty |

---

## Customising

Want to change the passing mark from 50%? Open `grader.py` and find `compute_analytics()`.
Want different grade thresholds? Find `assign_grade()`. Both are short functions, easy to tweak.

---

## Tech

Python 3.11+ · csv · os · datetime · collections · pytest

No pip installs needed to run the grader itself — only pytest is required for tests.
