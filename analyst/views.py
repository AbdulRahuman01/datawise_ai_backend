# This is a Django view file that handles API requests.

from groq import Groq
import os
import MySQLdb
from rest_framework.decorators import api_view
from rest_framework.response import Response

# Initialize Groq client using an environment variable for the API key.
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# List of SQL keywords we explicitly forbid to prevent destructive database actions.
FORBIDDEN = ["delete", "drop", "update", "insert", "alter", "truncate"]

# Database connection setup (Note: In production, use environment variables for credentials)
db = MySQLdb.connect(
    host="127.0.0.1",
    user="root",
    password="",  # your mysql password
    database="ott_platform",
    charset="utf8mb4"
)
# Cursor configured to return results as dictionaries (DictCursor)
cursor = db.cursor(MySQLdb.cursors.DictCursor)


def get_schema():
    """Fetches the schema (table and column names/types) from the database."""
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()

    schema = ""

    for t in tables:
        # Extract the table name from the dictionary returned by fetchall
        table_name = list(t.values())[0]
        cursor.execute(f"DESCRIBE {table_name}")
        columns = cursor.fetchall()

        # Format column details into a string (e.g., 'id INT, name VARCHAR(255)')
        col_str = ", ".join([f"{c['Field']} {c['Type']}" for c in columns])
        # Append to the schema string (e.g., 'employees(id INT, name VARCHAR(255))\n')
        schema += f"{table_name}({col_str})\n"

    return schema


def clean_sql(sql: str) -> str:
    """Removes common markdown formatting Groq might add to the SQL output."""
    sql = sql.replace("```sql", "")
    sql = sql.replace("```", "")
    return sql.strip()


@api_view(['POST'])
def ask_ai(request):
    """
    Main API endpoint. Takes a natural language question, gets SQL from Groq,
    executes the SQL, and gets an explanation of the results.
    """
    question = request.data.get("question", "").strip()

    if not question:
        return Response({"error": "Question is required bro 😭"})

    # 1) Get DB schema
    schema = get_schema()

    # 2) Build prompt for SQL generation
    sql_prompt = [
        {
            "role": "system",
            "content": (
                "You are an expert SQL generator for a MySQL database.\n"
                "Rules:\n"
                "- Only return a single SELECT query.\n"
                "- Do NOT use DELETE, UPDATE, INSERT, DROP, ALTER, TRUNCATE.\n"
                "- Use this schema:\n"
                f"{schema}"
            ),
        },
        {
            "role": "user",
            "content": question,
        },
    ]

    # 3) Ask Groq to generate SQL using the Llama 3 70B model
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=sql_prompt,
    )

    raw_sql = completion.choices[0].message.content.strip()
    generated_sql = clean_sql(raw_sql)

    # Remove trailing semicolon if present, as MySQLdb handles it better without
    if generated_sql.endswith(";"):
        generated_sql = generated_sql[:-1]

    # 4) Block dangerous SQL
    lowered = generated_sql.lower()
    for word in FORBIDDEN:
        if word in lowered:
            return Response({
                "error": "Dangerous SQL blocked bro 🔥",
                "sql": generated_sql,
            })

    # 5) Execute SQL and handle the whole process inside a try block
    try:
        cursor.execute(generated_sql)
        result = cursor.fetchall()

        # 6) Ask Groq to explain the results (Relies on 'result', so it's inside the 'try')
        explain_prompt = [
            {
                "role": "system",
                "content": "You are a senior data analyst. Explain the SQL result in clear, simple English. Be concise and highlight key insights."
            },
            {
                "role": "user",
                "content": f"SQL Result: {result}"
            }
        ]

        explanation_completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=explain_prompt,
        )

        explanation = explanation_completion.choices[0].message.content.strip()

    except Exception as e:
        # If any error occurs during execution (SQL error, DB connection issue)
        return Response({
            "error": f"Database Error: {str(e)}",
            "sql": generated_sql,
        })

    # 7) Final response (Executes only if the 'try' block was successful)
    return Response({
        "message": "SQL executed successfully bro!",
        "sql": generated_sql,
        "result": result,
        "explanation": explanation,
    })