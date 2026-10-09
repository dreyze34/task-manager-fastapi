from fastapi import Request

def get_job_service(request: Request):
    return request.app.state.job_service