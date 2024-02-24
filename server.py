from fastapi import FastAPI, File, UploadFile
import uvicorn
import pandas as pd
from io import BytesIO


app = FastAPI()

@app.get("/")
def read_root() -> dict:
    return {"status": "App running in port 8000"}


@app.post("/uploadfile/")
async def upload_file(file: UploadFile = File(...)):
    contents = await file.read()
    df = pd.read_csv(BytesIO(contents))
    return {"filename": file.filename, "columns": df.columns.tolist(), "shape": df.shape}


if __name__ == "__main__":
    uvicorn.run("server:app", port=8000, log_level="info")
