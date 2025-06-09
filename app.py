"""
app.py

Description: Initializes the Flask application and sets up the database connection.

Author: Mohammed Hamza
Date: 2025-06-09
"""
import pandas as pd

df = pd.read_excel("students.xlsx")

print(df.to_string())