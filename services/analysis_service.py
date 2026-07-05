class AnalysisService:
    def __init__(self, repository_service): self.repositories = repository_service

    @staticmethod
    def added_code(base_code, student_code):
        base_lines = {line.strip() for line in base_code.splitlines() if line.strip()}
        return "\n".join(line for line in student_code.splitlines() if line.strip() and line.strip() not in base_lines)

    def save_result(self, repository_id, repository_data, evaluation):
        self.repositories.save_repository_evaluation(repository_id, repository_data, evaluation)

    def save_plagiarism(self, session_id, rows): self.repositories.save_plagiarism(session_id, rows)
