from fastapi import Request

def get_repository(request: Request):
    return request.app.state.repository

def get_queue(request: Request):
    return request.app.state.queue