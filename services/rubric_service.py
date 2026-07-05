from repositories.rubric_repository import RubricRepository


class RubricService:
    def __init__(self, repository=None):
        self.repository=repository or RubricRepository();self.default_version_id=self.repository.ensure_default()
    def list_rubrics(self, include_archived=False):return self.repository.list(include_archived)
    def get_version(self, version_id):return self.repository.get_version(version_id)
    def create(self,name,description,categories):
        if not str(name).strip():raise ValueError("Rubric name is required.")
        if not categories:raise ValueError("Add at least one rubric category.")
        return self.repository.create(name.strip(),str(description).strip(),categories)
    def duplicate(self,version_id,name=None):
        source=self.get_version(version_id)
        if not source:raise LookupError("Rubric not found.")
        categories=[{"code":c["code"],"name":c["name"],"criteria":[{"key":x["criterion_key"],"name":x["name"],"max_score":float(x["max_score"])} for x in c["criteria"]]} for c in source["categories"]]
        return self.repository.create(name or f"{source['name']} Copy",source["description"],categories,version_id)
    def update(self,rubric_id,name,description,categories):return self.repository.new_version(rubric_id,name,description,categories)
    def archive(self,rubric_id,value=True):return self.repository.archive(rubric_id,value)
    def delete(self,rubric_id):return self.repository.delete(rubric_id)
