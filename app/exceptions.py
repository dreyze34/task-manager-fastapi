class JobNotFoundError(Exception):
    def __init__(self, job_id: str):
        self.job_id = job_id
        super().__init__(f"Job {job_id} not found")

class InvalidJobTypeError(Exception):
    super().__init__(f"Invalid job type requested.")

class InvalidJobStatusError(Exception):
    def __init__(self, job_id: str):
        self.job_id = job_id
        super().__init__(f"Invalid transition status for job {job_id}.")