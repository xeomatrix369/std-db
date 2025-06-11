"""
app.py

Description: Initializes the Flask application and sets up the database connection.

Author: Mohammed Hamza
Date: 2025-06-09
"""
import pandas as pd
from sqlalchemy import create_engine, text
import requests
import re
from chromadb import Client, Settings
from chromadb.utils import embedding_functions
from sentence_transformers import SentenceTransformer
from chromadb.utils.embedding_functions.ollama_embedding_function import (
    OllamaEmbeddingFunction,
)


model_var= "qwen2.5:latest"  # Model variable for LLM
vector_db = "sqlite:///vector_db.db"  # Path to the vector database\
embedding_model_var = "nomic-embed-text:latest"  # Embedding model
# df_embedding=pd.read_csv('nl_sql_dataset.csv')

chroma_client = Client(Settings(persist_directory=vector_db, is_persistent=True))
# Initialize Ollama embedding function
ollama_ef = OllamaEmbeddingFunction(
    url="http://172.25.60.20:11434/api/generate",
    model_name=embedding_model_var,
)

#############################################################################################
# Vectorisation of SQL queries under development

sql_collection = chroma_client.get_or_create_collection(
    name="sql_queries",
    embedding_function=ollama_ef
)

def initialize_vector_db():
    """Pre-populate vector DB with example queries if empty"""
    if sql_collection.count() == 0:
        # examples of assignment given
        examples = [
            ("List all students with a CGPA greater than 8.", "SELECT * FROM students WHERE CGPA > 8"),
            ("What are the email address of students from Bangalore", "SELECT Email FROM students WHERE Location LIKE '%Bangalore%'"),
            ("Show phone numbers of students preferring to work in Hyderabad with CGPA greater than 8", 
             "SELECT Phone_Number FROM students WHERE Preferred_Work_Location LIKE '%Hyderabad%' AND CGPA > 8")
        ]
        # examples form dataset
        try:
            # Load CSV dataset
            df = pd.read_csv('nl_sql_dataset.csv')
            print(df.columns)
            examples.extend(zip(df['nl_query'], df['sql']))
            print(f"Loaded {len(df)} examples from {'nl_sql_dataset.csv'}")

            embedding  = ollama_ef( ("List all students with a CGPA greater than 8.", "SELECT * FROM students WHERE CGPA > 8"))
            
            # # Prepare data for vector DB
            # ids = [f"id_{i}" for i in range(len(df))]
            # documents = df['sql'].tolist()
            # metadatas = [{"nl_query": nl} for nl in df['nl_query']]
            
            # # Add to collection
            # sql_collection.add(
            #     ids=ids,
            #     documents=documents,
            #     metadatas=metadatas
            # )
            # print(f"Vector DB initialized with {len(df)} examples from dataset")
        except Exception as e:
            print(f"Error loading CSV: {str(e)}")
            print("Initializing with default examples instead")
        
        print(f"Initialized vector DB with {len(examples)} examples")

def build_rag_prompt(user_query: str, similar_results: list) -> str:
    """RAG prompt to be constructed."""
    prompt = """You are a SQL expert. Convert questions to SQLite SQL for table 'students' with columns:
    Name, CGPA, Location, Email, Phone_Number, Preferred_Work_Location, Specialization_of_degree
    Rules:
    1. Always use SELECT statements
    2. Use LIKE for text matching (case-insensitive)
    Recent similar queries:\n"""
    # Add similar examples to prompt
    for i, item in enumerate(similar_results, 1):
        nl = item["metadatas"][0]["nl_query"]
        sql = item["documents"][0]
        prompt += f"{i}. Q: {nl}\n   SQL: {sql}\n"
    
    prompt += f"\nNew Query: {user_query}\nSQL:"
    return prompt

def query_llm(prompt: str) -> str:
    """Send prompt to LLM and return response"""
    payload = {
        "model": LLM_MODEL,
        "prompt": prompt,
        "stream": False
    }
    response = requests.post(LLM_URL, json=payload)
    return response.json().get("response", "").strip()

def extract_sql(response: str) -> str:
    """Extract SQL query from LLM response"""
    # Find first SQL keyword
    match = re.search(r"\b(SELECT|INSERT|UPDATE|DELETE)\b", response, re.IGNORECASE)
    if not match:
        return ""
    
    # Extract from keyword to semicolon
    start = match.start()
    end = response.find(";", start)
    return response[start:end+1] if end != -1 else response[start:]

def execute_sql(sql: str) -> str:
    """Execute SQL query and return results"""
    # Security validation
    if not re.match(r"^SELECT\s", sql, re.IGNORECASE):
        return "Error: Only SELECT queries allowed"
    
    conn = sqlite3.connect(STUDENT_DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(sql)
        results = cursor.fetchall()
        return "\n".join(str(row) for row in results) if results else "No results found"
    except Exception as e:
        return f"SQL Error: {str(e)}"
    finally:
        conn.close()

def add_to_vector_db(nl_query: str, sql_query: str):
    """Store successful query in vector DB"""
    new_id = f"id{sql_collection.count()}"
    sql_collection.add(
        documents=[sql_query],
        metadatas=[{"nl_query": nl_query}],
        ids=[new_id]
    )


#############################################################################################


# Initialize chat history
chat_history = []


# Load data from Excel file and store it in a SQLite database   
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
        # print("Error running SQL:", e)
        print("try to rephrase your query")

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
    # initialize_vector_db() (uncomment to pre-populate vector DB) work in progress
    print("\n<========= Student Database  Query System =========>\n")
    chat_loop(engine)   