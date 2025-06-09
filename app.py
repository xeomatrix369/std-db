"""
app.py

Description: Initializes the Flask application and sets up the database connection.

Author: Mohammed Hamza
Date: 2025-06-09
"""
import pandas as pd
from sqlalchemy import create_engine, text
import requests

def load_data_to_db():
    df = pd.read_excel("students.xlsx")
    engine = create_engine("sqlite:///students.db")
    df.to_sql("students", con=engine, if_exists="replace", index=False)
    print("Data loaded into database.")
    return engine

# Query to LLM server to convert humaninput to SQL
def query_llm(natural_language_query):
    url = "http://172.25.60.20:11434/api/generate"
    model_name = "MFDoom/deepseek-r1-tool-calling:7b"  
    payload = {
        "model": model_name,
        "prompt": f"Convert the following natural language to SQL: {natural_language_query}\nUse table name 'students'",
        "stream": False
    }
    response = requests.post(url, json=payload)
    sql = response.json().get("response", "")
    return sql.strip()

# Fetching from sql
def fetch_sql(engine, sql):
    try:
        result = engine.execute(text(sql))
        rows = result.fetchall()
        for row in rows:
            print(row)
    except Exception as e:
        print("Error running SQL:", e)

# Chat interface loop
def chat_loop(engine):
    print("Type your query (or 'exit' to quit):")
    while True:
        user_input = input("You: ") + " the file being students.db just give me the sql query for it"
        if user_input.lower() in ["exit", "quit"]:
            break
        sql = query_llm(user_input) 
        print("SQL Generated:", sql)
        fetch_sql(engine, sql)

if __name__ == "__main__":
    engine = load_data_to_db()
    chat_loop(engine)
