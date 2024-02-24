from fastapi import FastAPI, File, UploadFile
import uvicorn
import pandas as pd
from io import BytesIO
from typing import List
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
import datetime


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*']
    )

@app.get("/")
def read_root() -> dict:
    return {"status": "App running in port 8000"}


@app.post("/uploadfile/")
async def upload_file(files: List[UploadFile] = File(...)) -> list:
    parsed: list = []
    for file in files:
        contents = await file.read()
        isValid = True
        df = pd.read_csv(BytesIO(contents))
        dict_converted = df.to_dict(orient="records")
        null_rows = df[df.isnull().any(axis=1)]
        invalid_emails = validate_email(dict_converted)

        df_users = pd.read_csv("users.csv")
        df_projects = pd.read_csv("projects.csv")
        df_tasks = pd.read_csv("tasks.csv")

        today_date = datetime.now().date()

        missing_project_ids = df_tasks[~df_tasks['projectId'].isin(df_projects['id'])]

        missing_assigned_to = df_tasks[~df_tasks['assignedTo'].isin(df_users['id'])]
        
        invalid_deadlines = df_tasks[~pd.to_datetime(df_tasks['deadline'], errors='coerce').dt.date.isnull() & (pd.to_datetime(df_tasks['deadline']) < today_date)]

        duplicate_emails = df_users[df_users['email'].duplicated(keep=False)]
        duplicate_user_ids = df_users[df_users['id'].duplicated(keep=False)]

        duplicate_project_ids = df_projects[df_projects['id'].duplicated(keep=False)]


        if len(null_rows) > 0 or len(invalid_emails) > 0 or len(missing_project_ids) > 0 or len(invalid_deadlines) > 0 or len(duplicate_emails) > 0 or len(duplicate_user_ids) > 0 or len(duplicate_project_ids) > 0:
            isValid = False
            dict_converted = []
        parsed.append({
            "fileName": file.filename,
            "isValid": isValid,
            "nullValues": null_rows,
            "inValidEmails": invalid_emails,
            "missing_project_ids": missing_project_ids,
            "missing_assigned_to": missing_assigned_to,
            "invalid_deadlines": invalid_deadlines,
            "duplicate_emails": duplicate_emails,
            "duplicate_user_ids": duplicate_user_ids,
            "duplicate_project_ids": duplicate_project_ids
        })
    
    return jsonable_encoder(parsed)



def validate_email(objects) -> dict:
    invalid_emails = []
    valid = True
    for obj in objects:
        for key, value in obj.items():
            if key == 'email':
                if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', value):
                    invalid_emails.append(value)
    return invalid_emails


if __name__ == "__main__":
    uvicorn.run("server:app", port=8000, log_level="info", reload=True)
