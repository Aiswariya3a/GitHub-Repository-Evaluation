from uuid import UUID

from database import connect

DEFAULT_RUBRIC_ID = UUID("00000000-0000-4000-8000-000000000001")
DEFAULT_VERSION_ID = UUID("00000000-0000-4000-8000-000000000002")

DEFAULT_CATEGORIES = [
    ("Q1A", "Program Compilation and Execution", [("successful_compilation_and_execution",2),("demonstration_of_menu_operations",2),("explanation_of_control_structures",2),("sample_testing_and_output",2)]),
    ("Q1B", "Program Analysis and Debugging", [("testing_effort",2),("identification_of_issues",3),("corrected_logic_and_explanation",3)]),
    ("Q2A", "Searching using Arrays and Strings", [("proper_use_of_arrays_strings",3),("searching_implementation",3),("output_correctness",2)]),
    ("Q2B", "Sorting Account Records", [("sorting_logic",3),("correct_implementation",3),("display_and_testing",2)]),
    ("Q3A", "Functional Decomposition", [("function_decomposition",4),("modular_design_and_readability",4)]),
    ("Q3B", "Pointer-Based Operations", [("proper_pointer_implementation",4),("explanation_and_correctness",4)]),
    ("Q4A", "Structure Enhancement", [("structure_modification",4),("proper_implementation_and_testing",4)]),
    ("Q4B", "New Banking Feature Implementation", [("feature_implementation",4),("functionality_and_innovation",4)]),
    ("Q5A", "File Generation and Verification", [("file_generation",2),("file_update_verification",3),("correction_of_file_issues",3)]),
    ("Q5B", "Optimization and Error Handling", [("optimization_techniques",4),("error_handling_implementation",4)]),
]


class RubricRepository:
    def ensure_default(self):
        with connect() as db:
            db.execute("""INSERT INTO rubrics(id,name,description,rubric_type,is_default,is_read_only)
                VALUES (%s,'C Programming - Banking Transaction Assignment',
                'Official C-trans-Assignment rubric for the banking transaction mini project.','System',TRUE,TRUE)
                ON CONFLICT(id) DO NOTHING""", (DEFAULT_RUBRIC_ID,))
            db.execute("INSERT INTO rubric_versions(id,rubric_id,version) VALUES (%s,%s,1) ON CONFLICT(id) DO NOTHING", (DEFAULT_VERSION_ID,DEFAULT_RUBRIC_ID))
            for order,(code,name,criteria) in enumerate(DEFAULT_CATEGORIES):
                category = db.execute("""INSERT INTO rubric_categories(rubric_version_id,code,name,max_score,sort_order)
                    VALUES (%s,%s,%s,%s,%s) ON CONFLICT(rubric_version_id,code) DO UPDATE SET name=EXCLUDED.name
                    RETURNING id""", (DEFAULT_VERSION_ID,code,name,sum(score for _,score in criteria),order)).fetchone()
                for criterion_order,(key,score) in enumerate(criteria):
                    db.execute("""INSERT INTO rubric_criteria(category_id,criterion_key,name,max_score,sort_order)
                        VALUES (%s,%s,%s,%s,%s) ON CONFLICT(category_id,criterion_key) DO NOTHING""",
                        (category["id"],key,key.replace("_"," ").title(),score,criterion_order))
            db.execute("UPDATE evaluation_sessions SET rubric_version_id=%s WHERE rubric_version_id IS NULL", (DEFAULT_VERSION_ID,))
            db.execute("""UPDATE evaluations e SET rubric_version_id=s.rubric_version_id FROM repositories r
                JOIN evaluation_sessions s ON s.id=r.session_id WHERE e.repository_id=r.id AND e.rubric_version_id IS NULL""")
            db.execute("ALTER TABLE evaluation_sessions ALTER COLUMN rubric_version_id SET NOT NULL")
            db.execute("ALTER TABLE evaluations ALTER COLUMN rubric_version_id SET NOT NULL")
        return DEFAULT_VERSION_ID

    def list(self, include_archived=False):
        with connect() as db:
            return db.execute("""SELECT r.*,v.id version_id,v.version,
                COUNT(DISTINCT c.id) category_count,COUNT(k.id) criterion_count
                FROM rubrics r JOIN LATERAL (SELECT * FROM rubric_versions WHERE rubric_id=r.id ORDER BY version DESC LIMIT 1) v ON TRUE
                LEFT JOIN rubric_categories c ON c.rubric_version_id=v.id LEFT JOIN rubric_criteria k ON k.category_id=c.id
                WHERE (%s OR NOT r.is_archived) GROUP BY r.id,v.id,v.version ORDER BY r.is_default DESC,r.updated_at DESC""", (include_archived,)).fetchall()

    def get_version(self, version_id):
        with connect() as db:
            header = db.execute("""SELECT r.*,v.id version_id,v.version FROM rubric_versions v
                JOIN rubrics r ON r.id=v.rubric_id WHERE v.id=%s""", (version_id,)).fetchone()
            if not header: return None
            categories = db.execute("SELECT * FROM rubric_categories WHERE rubric_version_id=%s ORDER BY sort_order,code", (version_id,)).fetchall()
            for category in categories:
                category["criteria"] = db.execute("SELECT * FROM rubric_criteria WHERE category_id=%s ORDER BY sort_order,criterion_key", (category["id"],)).fetchall()
            header["categories"] = categories
            header["total_score"] = float(sum(category["max_score"] for category in categories))
            return header

    def create(self, name, description, categories, source_version_id=None):
        with connect() as db:
            rubric = db.execute("""INSERT INTO rubrics(name,description,rubric_type,is_default,is_read_only)
                VALUES (%s,%s,'Custom',FALSE,FALSE) RETURNING *""", (name,description)).fetchone()
            version = db.execute("INSERT INTO rubric_versions(rubric_id,version) VALUES (%s,1) RETURNING *", (rubric["id"],)).fetchone()
            self._insert_categories(db, version["id"], categories)
        return self.get_version(version["id"])

    def new_version(self, rubric_id, name, description, categories):
        with connect() as db:
            rubric = db.execute("SELECT * FROM rubrics WHERE id=%s FOR UPDATE", (rubric_id,)).fetchone()
            if not rubric: raise LookupError("Rubric not found.")
            if rubric["is_read_only"]: raise PermissionError("System rubrics cannot be edited. Duplicate it first.")
            db.execute("UPDATE rubrics SET name=%s,description=%s,updated_at=now() WHERE id=%s", (name,description,rubric_id))
            number = db.execute("SELECT COALESCE(MAX(version),0)+1 number FROM rubric_versions WHERE rubric_id=%s", (rubric_id,)).fetchone()["number"]
            version = db.execute("INSERT INTO rubric_versions(rubric_id,version) VALUES (%s,%s) RETURNING *", (rubric_id,number)).fetchone()
            self._insert_categories(db, version["id"], categories)
        return self.get_version(version["id"])

    @staticmethod
    def _insert_categories(db, version_id, categories):
        for order,category in enumerate(categories):
            criteria = category.get("criteria", [])
            maximum = sum(float(item.get("max_score",0)) for item in criteria)
            row = db.execute("""INSERT INTO rubric_categories(rubric_version_id,code,name,max_score,sort_order)
                VALUES (%s,%s,%s,%s,%s) RETURNING id""", (version_id,category["code"],category.get("name",category["code"]),maximum,order)).fetchone()
            for criterion_order,item in enumerate(criteria):
                db.execute("""INSERT INTO rubric_criteria(category_id,criterion_key,name,max_score,sort_order)
                    VALUES (%s,%s,%s,%s,%s)""", (row["id"],item["key"],item.get("name",item["key"]),item["max_score"],criterion_order))

    def archive(self, rubric_id, archived=True):
        with connect() as db:
            row=db.execute("SELECT is_read_only FROM rubrics WHERE id=%s",(rubric_id,)).fetchone()
            if not row:return False
            if row["is_read_only"]:raise PermissionError("System rubrics cannot be archived.")
            db.execute("UPDATE rubrics SET is_archived=%s,updated_at=now() WHERE id=%s",(archived,rubric_id));return True

    def delete(self, rubric_id):
        with connect() as db:
            row=db.execute("SELECT is_read_only FROM rubrics WHERE id=%s",(rubric_id,)).fetchone()
            if not row:return False
            if row["is_read_only"]:raise PermissionError("System rubrics cannot be deleted.")
            usage=db.execute("""SELECT EXISTS(SELECT 1 FROM evaluation_sessions s JOIN rubric_versions v ON v.id=s.rubric_version_id WHERE v.rubric_id=%s)
                OR EXISTS(SELECT 1 FROM evaluations e JOIN rubric_versions v ON v.id=e.rubric_version_id WHERE v.rubric_id=%s) used""",(rubric_id,rubric_id)).fetchone()
            if usage["used"]:raise ValueError("Rubrics used by sessions or historical evaluations cannot be deleted; archive it instead.")
            return bool(db.execute("DELETE FROM rubrics WHERE id=%s",(rubric_id,)).rowcount)
