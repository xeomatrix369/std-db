"""
app.py

Description: Initializes the Flask application and sets up the database connection.

Author: Mohammed Hamza
Date: 2025-06-09
"""
import pandas as pd
from sqlalchemy import create_engine, text
import requests

model_var= "qwen2.5:latest"  # Model variable for LLM

def load_data_to_db():
    df = pd.read_excel("students.xlsx")
    engine = create_engine("sqlite:///students.db")
    df.to_sql("students", con=engine, if_exists="replace", index=False)
    print("Data loaded into database.")
    return engine

# Query to LLM server to convert humaninput to SQL
def query_llm(natural_language_query):
    url = "http://172.25.60.20:11434/api/generate"
    model_name = model_var
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
        with engine.connect() as connection:
            result = connection.execute(text(sql))
            rows = result.fetchall()
            for row in rows:
                print(row)
    except Exception as e:
        print("Error running SQL:", e)

# Chat interface loop
def chat_loop(engine):
    print("Type your query (or 'exit' to quit):")
    while True:
        user_input = input("How can I Help you: ")
        if user_input.lower() in ["exit", "quit"]:
            break
        # user_input = user_input.strip()
        prompt = f"""You are an assistant that converts natural language into SQL queries.Use the following table: `students`Columns are: Name, CGPA, Location, Email, Phone Number, Preferred Work Location, Specialization in degree Natural Language Query: \"{user_input}\"Respond with just the SQL query, nothing else."""
        sql = query_llm(prompt) 
        print("SQL Generated:", sql)
        fetch_sql(engine, user_input)

if __name__ == "__main__":
    engine = load_data_to_db()
    chat_loop(engine)
