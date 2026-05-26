# Rubric-Based Evaluation System - Implementation Reference

## Overview
This document maps the PDF rubric to the implementation in `main.py` and `pdf_gen.py`.

**Total Marks:** 80 (10 questions × 8 marks each)
**Normalized Score:** Out of 20 (final_score / 80 × 20)

---

## Question-wise Rubric Mapping

### Q1A - Program Compilation and Execution (8 Marks)
**Course Outcome:** CO1 (Basic C programming constructs, Program execution)

| Component | Max Marks | JSON Field | Implementation |
|-----------|-----------|-----------|-----------------|
| Successful compilation and execution | 2 | `successful_compilation_and_execution` | Checked in evaluate_code() |
| Demonstration of menu operations | 2 | `demonstration_of_menu_operations` | Checked in evaluate_code() |
| Explanation of control structures | 2 | `explanation_of_control_structures` | Checked in evaluate_code() |
| Sample testing and output | 2 | `sample_testing_and_output` | Checked in evaluate_code() |
| **TOTAL** | **8** | `Q1A.total` | Sum of components |

---

### Q1B - Program Analysis and Debugging (8 Marks)
**Course Outcome:** CO1 (Program execution and debugging)

| Component | Max Marks | JSON Field | Implementation |
|-----------|-----------|-----------|-----------------|
| Testing effort | 2 | `testing_effort` | Checked in evaluate_code() |
| Identification of issues | 3 | `identification_of_issues` | Checked in evaluate_code() |
| Corrected logic and explanation | 3 | `corrected_logic_and_explanation` | Checked in evaluate_code() |
| **TOTAL** | **8** | `Q1B.total` | Sum of components |

---

### Q2A - Searching using Arrays and Strings (8 Marks)
**Course Outcome:** CO2 (Arrays and strings, Searching)

| Component | Max Marks | JSON Field | Implementation |
|-----------|-----------|-----------|-----------------|
| Proper use of arrays/strings | 3 | `proper_use_of_arrays_strings` | Checked in evaluate_code() |
| Searching implementation | 3 | `searching_implementation` | Checked in evaluate_code() |
| Output correctness | 2 | `output_correctness` | Checked in evaluate_code() |
| **TOTAL** | **8** | `Q2A.total` | Sum of components |

---

### Q2B - Sorting Account Records (8 Marks)
**Course Outcome:** CO2 (Sorting)

| Component | Max Marks | JSON Field | Implementation |
|-----------|-----------|-----------|-----------------|
| Sorting logic | 3 | `sorting_logic` | Checked in evaluate_code() |
| Correct implementation | 3 | `correct_implementation` | Checked in evaluate_code() |
| Display and testing | 2 | `display_and_testing` | Checked in evaluate_code() |
| **TOTAL** | **8** | `Q2B.total` | Sum of components |

---

### Q3A - Functional Decomposition (8 Marks)
**Course Outcome:** CO3 (Functional decomposition)

| Component | Max Marks | JSON Field | Implementation |
|-----------|-----------|-----------|-----------------|
| Function decomposition | 4 | `function_decomposition` | Checked in evaluate_code() |
| Modular design and readability | 4 | `modular_design_and_readability` | Checked in evaluate_code() |
| **TOTAL** | **8** | `Q3A.total` | Sum of components |

---

### Q3B - Pointer-Based Operations (8 Marks)
**Course Outcome:** CO3 (Pointer-based programming)

| Component | Max Marks | JSON Field | Implementation |
|-----------|-----------|-----------|-----------------|
| Proper pointer implementation | 4 | `proper_pointer_implementation` | Checked in evaluate_code() |
| Explanation and correctness | 4 | `explanation_and_correctness` | Checked in evaluate_code() |
| **TOTAL** | **8** | `Q3B.total` | Sum of components |

---

### Q4A - Structure Enhancement (8 Marks)
**Course Outcome:** CO4 (Structures and unions)

| Component | Max Marks | JSON Field | Implementation |
|-----------|-----------|-----------|-----------------|
| Structure modification | 4 | `structure_modification` | Checked in evaluate_code() |
| Proper implementation and testing | 4 | `proper_implementation_and_testing` | Checked in evaluate_code() |
| **TOTAL** | **8** | `Q4A.total` | Sum of components |

---

### Q4B - New Banking Feature Implementation (8 Marks)
**Course Outcome:** CO4 (Banking feature implementation)

| Component | Max Marks | JSON Field | Implementation |
|-----------|-----------|-----------|-----------------|
| Feature implementation | 4 | `feature_implementation` | Checked in evaluate_code() |
| Functionality and innovation | 4 | `functionality_and_innovation` | Checked in evaluate_code() |
| **TOTAL** | **8** | `Q4B.total` | Sum of components |

---

### Q5A - File Generation and Verification (8 Marks)
**Course Outcome:** CO5 (File handling concepts)

| Component | Max Marks | JSON Field | Implementation |
|-----------|-----------|-----------|-----------------|
| File generation | 2 | `file_generation` | Checked in evaluate_code() |
| File update verification | 3 | `file_update_verification` | Checked in evaluate_code() |
| Correction of file issues | 3 | `correction_of_file_issues` | Checked in evaluate_code() |
| **TOTAL** | **8** | `Q5A.total` | Sum of components |

---

### Q5B - Optimization and Error Handling (8 Marks)
**Course Outcome:** CO5 (Optimization and error handling)

| Component | Max Marks | JSON Field | Implementation |
|-----------|-----------|-----------|-----------------|
| Optimization techniques | 4 | `optimization_techniques` | Checked in evaluate_code() |
| Error handling implementation | 4 | `error_handling_implementation` | Checked in evaluate_code() |
| **TOTAL** | **8** | `Q5B.total` | Sum of components |

---

## JSON Response Structure

```json
{
  "roll_number": "24UCS271001",
  "questions": {
    "Q1A": {
      "successful_compilation_and_execution": {
        "score": 2,
        "remarks": "Program compiles without errors and executes successfully"
      },
      "demonstration_of_menu_operations": {
        "score": 2,
        "remarks": "All menu operations demonstrated with sample inputs"
      },
      "explanation_of_control_structures": {
        "score": 2,
        "remarks": "Variables, loops, and conditionals explained clearly"
      },
      "sample_testing_and_output": {
        "score": 2,
        "remarks": "Sample test cases provided with expected output"
      },
      "total": 8
    },
    "Q1B": {
      "testing_effort": {
        "score": 2,
        "remarks": "Thorough testing with various test cases"
      },
      "identification_of_issues": {
        "score": 3,
        "remarks": "Identified two logical issues in the code"
      },
      "corrected_logic_and_explanation": {
        "score": 3,
        "remarks": "Issues corrected with clear explanation"
      },
      "total": 8
    },
    "Q2A": { ... },
    "Q2B": { ... },
    "Q3A": { ... },
    "Q3B": { ... },
    "Q4A": { ... },
    "Q4B": { ... },
    "Q5A": { ... },
    "Q5B": { ... }
  },
  "final": {
    "total_out_of_80": 73,
    "normalized_to_20": 18.25,
    "overall_remarks": "Good implementation with strong fundamentals..."
  }
}
```

---

## Scoring Rules in Implementation

### Score Clamping (main.py, evaluate_code function)
```python
# For each component:
max_score = rubric_max_scores[question_id][component]
clamped_score = max(0, min(original_score, max_score))
```

### Total Calculation
```python
question_total = sum(clamped_scores for all components in question)
final_total_out_of_80 = sum(all question_totals)
normalized_to_20 = (final_total_out_of_80 / 80) * 20
```

### Score Validation
- Each component score is clamped to its maximum
- No score can exceed the rubric maximum
- Totals are recalculated programmatically
- **LLM output is NEVER trusted for totals**

---

## PDF Report Structure

### Individual Student Report (pdf_gen.py)
1. **Header Section**
   - Title: "Student Evaluation Report"
   - Roll Number
   - Repository URL

2. **Repository Information**
   - Commit Count
   - Public Repository (Yes/No)
   - README Present (Yes/No)

3. **Final Score Summary**
   - Total Out of 80
   - Normalized to 20
   - Overall Remarks

4. **Question-wise Evaluation**
   - For each Q1A through Q5B:
     - Question title and description
     - Total score for question (e.g., "6/8")
     - Table with:
       - Criterion name
       - Score obtained
       - Remarks

5. **Plagiarism Check**
   - List of similar submissions (if any)
   - Similarity percentage

### Consolidated Report (preamble.pdf)
1. **Summary Statistics**
   - Total Students
   - Evaluated Students
   - Average Score (out of 80 and 20)
   - Highest/Lowest Scores
   - Plagiarism Cases

2. **Student Coverage Overview**
   - Table with all students
   - Columns: Roll No, Score Out of 80, Score Out of 20, Commits, Public Repo, README

---

## Preserved Workflows

✅ **Repository Analysis** - Unchanged
- Repository cloning
- Base code extraction
- Commit counting
- Public/README detection

✅ **Plagiarism Detection** - Unchanged
- TF-IDF vectorization
- Cosine similarity (threshold: 0.80)
- Code corpus from student additions

✅ **CSV Output** - Unchanged
- repo_report.csv
- evaluation_report.csv
- plagiarism_report.csv

✅ **PDF Merging** - Unchanged
- Individual PDFs merged into Final_Consolidated_Report.pdf

---

## Testing Checklist

- [ ] main.py runs without syntax errors
- [ ] evaluate_code() returns correct JSON structure
- [ ] Score clamping works (test with LLM output exceeding max)
- [ ] Totals calculated correctly programmatically
- [ ] pdf_gen.py reads new JSON format
- [ ] Individual PDFs generated correctly
- [ ] Consolidated PDF generated with updated statistics
- [ ] Question titles display correctly
- [ ] Plagiarism detection works
- [ ] CSV files generated correctly

---

## Backward Compatibility

⚠️ **Breaking Change:** Old evaluation format is no longer supported
- Old JSON structure (general, comprehension, modification, innovation) removed
- Code that depends on old structure will fail
- Regenerate evaluation_report.csv by re-running main.py

✅ **Non-breaking:** Everything else
- Repository data format unchanged
- Plagiarism data format unchanged
- CSV workflow unchanged
- File handling unchanged

---

## Notes for Deployment

1. **Run main.py first** to generate new evaluation_report.csv
2. **Then run pdf_gen.py** to generate PDF reports
3. **Delete old student_reports folder** if regenerating
4. **Expected output files:**
   - evaluation_report.csv (updated)
   - plagiarism_report.csv (updated)
   - repo_report.csv (unchanged)
   - preamble.pdf (regenerated)
   - student_reports/*.pdf (all regenerated)
   - Final_Consolidated_Report.pdf (regenerated)
