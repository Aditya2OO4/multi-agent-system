from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import os
from dotenv import load_dotenv
import uuid
import json
from datetime import datetime
from enum import Enum
import sqlite3
import google.generativeai as genai
from agents.classifier_agent import ClassifierAgent
from agents.email_agent import EmailAgent
from agents.json_agent import JSONAgent
from agents.pdf_agent import PDFAgent
from action_router import ActionRouter

# Load environment variables
load_dotenv()

# Initialize Gemini
genai.configure(api_key="AIzaSyDs9InimZpe2zOZmQBaWCocHKvh6hFCTWc")
gemini_model = genai.GenerativeModel('gemini-2.0-flash')


# Initialize SQLite Database
def init_db():
    conn = sqlite3.connect('memory_store.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS requests (
            request_id TEXT PRIMARY KEY,
            raw_input TEXT,
            input_type TEXT,
            timestamp TEXT,
            classification TEXT,
            agent_results TEXT,
            actions TEXT,
            action_results TEXT
        )
    ''')
    conn.commit()
    conn.close()


init_db()

app = FastAPI(title="Multi-Format Autonomous AI System")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# Initialize agents with SQLite connection
def get_db_conn():
    return sqlite3.connect('memory_store.db')


classifier_agent = ClassifierAgent(gemini_model, get_db_conn)
email_agent = EmailAgent(gemini_model, get_db_conn)
json_agent = JSONAgent(gemini_model, get_db_conn)
pdf_agent = PDFAgent(gemini_model, get_db_conn)
action_router = ActionRouter(get_db_conn)


class InputType(str, Enum):
    EMAIL = "email"
    JSON = "json"
    PDF = "pdf"


class ProcessRequest(BaseModel):
    input_type: InputType
    content: Optional[str] = None


@app.post("/process")
async def process_input(
        input_type: InputType,
        file: UploadFile = File(None),
        content: str = None
):
    conn = get_db_conn()
    cursor = conn.cursor()

    try:
        # Generate unique ID for this processing request
        request_id = str(uuid.uuid4())

        # Get content from either file or direct content
        if file:
            content = await file.read()
            if input_type == InputType.PDF:
                content = content.decode('latin-1')  # For PDF binary
        elif not content:
            raise HTTPException(status_code=400, detail="Either file or content must be provided")

        # Store raw input in database
        cursor.execute('''
            INSERT INTO requests (request_id, raw_input, input_type, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (request_id, content, input_type.value, datetime.now().isoformat()))
        conn.commit()

        # Classify input
        classification = classifier_agent.classify(content, input_type)
        cursor.execute('''
            UPDATE requests SET classification = ? WHERE request_id = ?
        ''', (json.dumps(classification), request_id))
        conn.commit()

        # Route to appropriate agent
        agent_results = {}
        if input_type == InputType.EMAIL:
            agent_results = email_agent.process(content, classification)
        elif input_type == InputType.JSON:
            agent_results = json_agent.process(content, classification)
        elif input_type == InputType.PDF:
            agent_results = pdf_agent.process(content, classification)

        # Store agent results
        cursor.execute('''
            UPDATE requests SET agent_results = ? WHERE request_id = ?
        ''', (json.dumps(agent_results), request_id))
        conn.commit()

        # Determine and execute actions
        actions = action_router.determine_actions(agent_results, classification)
        cursor.execute('''
            UPDATE requests SET actions = ? WHERE request_id = ?
        ''', (json.dumps(actions), request_id))
        conn.commit()

        # Execute actions
        action_results = action_router.execute_actions(actions)
        cursor.execute('''
            UPDATE requests SET action_results = ? WHERE request_id = ?
        ''', (json.dumps(action_results), request_id))
        conn.commit()

        return {
            "request_id": request_id,
            "classification": classification,
            "agent_results": agent_results,
            "actions": actions,
            "action_results": action_results
        }

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@app.get("/request/{request_id}")
async def get_request(request_id: str):
    conn = get_db_conn()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            SELECT * FROM requests WHERE request_id = ?
        ''', (request_id,))
        request_data = cursor.fetchone()

        if not request_data:
            raise HTTPException(status_code=404, detail="Request not found")

        # Convert tuple to dictionary
        columns = [column[0] for column in cursor.description]
        request_dict = dict(zip(columns, request_data))

        # Parse JSON fields
        for field in ['classification', 'agent_results', 'actions', 'action_results']:
            if request_dict.get(field):
                request_dict[field] = json.loads(request_dict[field])

        return request_dict

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@app.get("/requests")
async def list_requests():
    conn = get_db_conn()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            SELECT request_id, input_type, timestamp FROM requests ORDER BY timestamp DESC
        ''')
        requests = cursor.fetchall()

        columns = [column[0] for column in cursor.description]
        return [dict(zip(columns, row)) for row in requests]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)