"""
app.py

Description: Initializes the Flask application and sets up the database connection.

Author: Mohammed Hamza
Date: 2025-06-09
"""
import pandas as pd
from sqlalchemy import create_engine, text
import requests

# Initialize chat history
chat_history = []

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
        "prompt": f"You are an assistant that converts natural language into SQL queries and nothing else . {natural_language_query}  Use the following table: `students` Columns are: Name, CGPA, Location, Email, Phone_Number, Preferred_Work_Location, Specialization_of_degree.",
        "stream": False
    }
    response = requests.post(url, json=payload)
    sql = response.json().get("response", "")
    return sql.strip()

#filer the llm response to get only sql query
def extract_sql_only(response_text):
    response_text = response_text.strip()

    # Find the first occurrence of SELECT (or other SQL keywords)
    keywords = ["select", "insert", "update", "delete"]
    start = -1
    for keyword in keywords:
        idx = response_text.lower().find(keyword)
        if idx != -1:
            start = idx
            break

    # index of the first semicolon
    end = response_text.find(";", start)
    if start != -1 and end != -1:
        return response_text[start:end+1].strip()

    # redundancy: return nothing or raw string
    return response_text.strip()

# Fetching from sql
def fetch_sql(engine, sql):
    try:
        x=""
        with engine.connect() as connection:
            result = connection.execute(text(sql))
            rows = result.fetchall()
            for row in rows:
                print(row)
                x+= str(row) + ";"
        return x.strip() if x else "No results found."
    except Exception as e:
        print("Error running SQL:", e)

# Chat interface loop
def chat_loop(engine):
    print("Type your query (or 'exit' to quit):")
    while True:
        with engine.connect() as connection:
            result = connection.execute(text("PRAGMA table_info(students);"))
            columns = [row[1] for row in result.fetchall()]
        # print("Columns in the table:", columns)
        user_input = input("How can I help you: ")
        
        if user_input.lower() in ["exit", "quit"]:
            break
        # user_input = user_input.strip()
        # prompt = f"""You are an assistant that converts natural language into SQL queries.Use the following table: `students`Columns are: Name, CGPA, Location, Email, Phone Number, Preferred Work Location, Specialization in degree Natural Language Query: \"{user_input}\"Respond with just the SQL query, nothing else."""
        prompt =  user_input
        sql = query_llm(prompt) 
        # print("LLM GEN",sql);
        sql = extract_sql_only(sql)
        # print("SQL Generated:", sql)
        results= fetch_sql(engine, sql)
        # print (results);
        chat_history.append({"query": user_input, "sql": sql, "results": results})
    print("\nChat session history:")
    for i, entry in enumerate(chat_history):
        print(f"{i+1}. Q: {entry['query']}\n   SQL: {entry['sql']}\n   Results: {entry['results']}\n")
        with open("history.txt", "a") as history_file:
            history_file.write(f"Query: {entry['query']} ")
            history_file.write(f"SQL: {entry['sql']} ")
            history_file.write(f"Results: {entry['results']} ")
            history_file.write("\n")

if __name__ == "__main__":
    engine = load_data_to_db()
    chat_loop(engine)   