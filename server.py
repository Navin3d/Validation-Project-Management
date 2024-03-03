from fastapi import FastAPI, File, UploadFile
import uvicorn, re, pathlib, os, shutil
import pandas as pd
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
from datetime import datetime


base = pd.to_datetime("2022-10-10")
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*']
    )

FILE_BASEPATH: str = os.path.join(pathlib.Path().resolve(), "files/prod/")


@app.get("/")
def read_root() -> dict:
    return {"status": "App running in port 8000"}


@app.post("/uploadfile/{bactchId}/")
async def upload_file(bactchId: str, files: UploadFile = File(...)):
    batch_path = FILE_BASEPATH + bactchId
    if(not os.path.isdir(batch_path)):
       os.mkdir(batch_path)
    path = os.path.join(batch_path, files.filename)
    try:
        contents = await files.read()
        with open(path, 'wb') as f:
            f.write(contents)
    except Exception as e:
        print(e)
        return False
    finally:
        files.close()
    return True

@app.get("/clearbatch/{bactchId}/")
async def upload_file(bactchId: str):
    batch_path = FILE_BASEPATH + bactchId
    if os.path.isdir(batch_path):
       shutil.rmtree(batch_path)
    return True

def return_list_ifempty(df):
    try:
        if df.empty:
            return []
        return df.to_dict(orient="records")
    except Exception:
        return []

@app.get("/process-batch/{bactchId}/")
async def proces_batch(bactchId: str) -> dict:
    batch_path = FILE_BASEPATH + bactchId

    parsed: list = []
    developer_file = filter_file(batch_path, "developer")
    project_file = filter_file(batch_path, "project")
    task_file = filter_file(batch_path, "task")

    project_df = []
    developer_df = []
    task_df = []
    if ".xlsx" in project_file:
        project_df = await excel_to_df(project_file)
    else:
        project_df = await csv_to_df(project_file)

    if ".xlsx" in developer_file:
        developer_df = await excel_to_df(developer_file)
    else:
        developer_df = await csv_to_df(developer_file)

    if ".xlsx" in task_file:
        task_df = await excel_to_df(task_file)
    else:
        task_df = await csv_to_df(task_file)

    parsed.append(handle_developer(developer_df))
    parsed.append(handle_project(project_df, developer_df))
    parsed.append(handle_task(task_df, project_df, developer_df))

    returnValue = {
        "isValid": True,
        "errors": parsed
    }

    if parsed[0]['isDeveloperValid'] == False or parsed[1]['isProjectValid'] == False or parsed[2]['isTaskValid'] == False:
        returnValue["isValid"] = False

    if returnValue["isValid"] == True:
        returnValue["data"] = {
            "developer": return_list_ifempty(developer_df),
            "project": return_list_ifempty(project_df),
            "task": return_list_ifempty(task_df),
        }
        returnValue.pop("errors")
    
    print(returnValue)
    return jsonable_encoder(returnValue)


def filter_file(folder_path, file_name):
    for file in os.listdir(folder_path):
        print(file)
        if file_name in file:
            return os.path.join(folder_path, file)
    return None

async def csv_to_df(csv_file):
    return pd.read_csv(csv_file)

async def excel_to_df(excel_file):
    return pd.read_excel(excel_file)

async def handle_csv(csv_file):
    file_name = csv_file.filename
    dataframe = await csv_to_df(csv_file)
    if "developer" in file_name:
        return handle_developer(dataframe)
    elif "project" in file_name:
        return handle_project(dataframe)
    elif "task" in file_name:
        return handle_task(dataframe)


async def handle_excel(exce_file):
    file_name = exce_file.filename
    dataframe = await excel_to_df(exce_file)
    if "developer" in file_name:
        return handle_developer(dataframe)
    elif "project" in file_name:
        return handle_project(dataframe)
    elif "task" in file_name:
        return handle_task(dataframe)


def handle_developer(developer_dataframe) -> dict:
    is_valid = True
    developer_dataframe_cleaned = developer_dataframe.where(pd.notnull(developer_dataframe), None)    
    # Get rows with null values
    null_rows = developer_dataframe_cleaned[developer_dataframe_cleaned.isnull().any(axis=1)]    
    # Exclude the first row
    null_rows = null_rows[null_rows.index != 1]
    dict_converted = developer_dataframe.where(pd.notnull(developer_dataframe), "null").to_dict(orient="records")

    invalid_emails = validate_email(dict_converted)
    duplicate_emails = developer_dataframe[developer_dataframe['email'].duplicated(keep=False)]
    duplicate_user_ids = developer_dataframe[developer_dataframe['id'].duplicated(keep=False)]
    if len(null_rows) > 0 or len(invalid_emails) > 0 or len(duplicate_emails) > 0 or len(duplicate_user_ids) > 0:
        is_valid = False
    return {
        "isDeveloperValid": is_valid,
        "invalidEmails": invalid_emails,
        "nullRows": return_list_ifempty(null_rows),
        "duplicateEmailEntry": return_list_ifempty(duplicate_emails),
        "duplicateIdEntry": return_list_ifempty(duplicate_user_ids)
    }

def handle_project(project_dataframe, developer_dataframe):
    is_valid = True
    null_rows = project_dataframe[project_dataframe.isnull().any(axis=1)]
    null_rows = null_rows[null_rows.index != 1]
    missing_developer_ids = project_dataframe[~project_dataframe['createdBy'].isin(developer_dataframe['id'])]
    duplicate_project_ids = project_dataframe[project_dataframe['id'].duplicated(keep=False)]
    if len(null_rows) > 0 or len(duplicate_project_ids) > 0:
        is_valid = False
    return {
        "isProjectValid": is_valid,
        "nullRows": return_list_ifempty(null_rows),
        "duplicateIdEntry": return_list_ifempty(duplicate_project_ids),
        "missingDevelopers": return_list_ifempty(missing_developer_ids),
    }

def handle_task(task_dataframe, project_dataframe, developer_dataframe):
    is_valid = True
    today_date = datetime.now().date()
    null_rows = project_dataframe[project_dataframe.isnull().any(axis=1)]
    null_rows = null_rows[null_rows.index != 1]
    missing_project_ids = task_dataframe[~task_dataframe['projectId'].isin(project_dataframe['id'])]
    missing_assigned_to = task_dataframe[~task_dataframe['assignedTo'].isin(developer_dataframe['id'])]        
    # invalid_deadlines = task_dataframe[~pd.to_datetime(task_dataframe['deadline'], errors='coerce').dt.date.isnull() & (pd.to_datetime(task_dataframe['deadline']) < today_date)]
    invalid_deadlines = []
    invalid_assigned_to = []
    
    for index, row in task_dataframe.iterrows():
        project_id = row['projectId']
        assigned_to = row['assignedTo']
        # Check if project_id exists in projects DataFrame
        if project_id in project_dataframe['id'].values:
            # Filter projects DataFrame for the specific project_id
            project_row = project_dataframe[project_dataframe['id'] == project_id]
            if not project_row.empty:
                # Extract the developers associated with the project
                project_developers = project_row['developers'].iloc[0]
                # Check if project_developers is not NaN (missing)
                if not pd.isna(project_developers):
                    # Convert to list if not already
                    if not isinstance(project_developers, list):
                        project_developers = [project_developers]
                    # Check if assigned_to is not in the list of project developers
                    if assigned_to not in project_developers:
                        invalid_assigned_to.append({ "projectId": project_id, "assignedId": assigned_to })

    try:
        task_dataframe['deadline'] = pd.to_datetime(task_dataframe['deadline'])
        invalid_deadlines = task_dataframe[task_dataframe['deadline'] < pd.Timestamp.today()]
    except ValueError as e:
        print("Invalid deadline format:", e)
    if len(null_rows) > 0 or len(missing_project_ids) > 0 or len(missing_assigned_to) > 0 or len(invalid_deadlines) > 0:
        is_valid = False
    return {
        "isTaskValid": is_valid,
        "nullRows": return_list_ifempty(null_rows),
        "missingProjects": return_list_ifempty(missing_project_ids),
        "missingDevelopers": return_list_ifempty(missing_assigned_to),
        "invalidDeadlines": return_list_ifempty(invalid_deadlines),
        "inValidAssignment": return_list_ifempty(invalid_assigned_to)
    }

def validate_email(objects):
    invalid_emails = []
    for obj in objects:
        for key, value in obj.items():
            if key == 'email':
                if value != value:
                    invalid_emails.append(value)
                else:
                    # print(value)
                    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', value):
                        invalid_emails.append({ "id": obj["id"], "email": value })
    return invalid_emails



if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, log_level="info", reload=True)
