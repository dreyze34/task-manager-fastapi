class JobNotFoundError(Exception):
    def __init__(self, job_id: str):
        self.job_id = job_id
        super().__init__(f"Job {job_id} not found")

class InvalidJobStatusError(Exception):
    def __init__(self, job_id: str):
        self.job_id = job_id
        super().__init__(f"Invalid transition status for job {job_id}.")