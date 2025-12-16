# This is a Django view file that handles API requests.

import os
from groq import Groq

from django.db import connection
from rest_framework.decorators import api_view
from rest_framework.response import Response

# Initialize Groq client using environment variable
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Forbidden SQL keywords (read-only safety)
FORBIDDEN = ["delete", "drop", "update", "insert", "alter", "truncate"]


def get_schema():
    """
    Fetch database schema (tables + columns) in a PostgreSQL-safe way
    using Django's database connection.
    """
    schema = ""

    with connection.cursor() as cursor:
        # Get all tables from public schema
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
        """)
        tables = cursor.fetchall()

        for (table_name,) in tables:
            cursor.execute("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = %s
            """, [table_name])

            columns = cursor.fetchall()
            col_str = ", ".join(
                [f"{col} {dtype}" for col, dtype in columns]
            )
            schema += f"{table_name}({col_str})\n"

    return schema


def clean_sql(sql: str) -> str:
    """Remove markdown formatting from Groq output."""
    sql = sql.replace("```sql", "").replace("```", "")
    return sql.strip()


@api_view(["POST"])
def ask_ai(request):
    question = request.data.get("question", "").strip()

    if not question:
        return Response({"error": "Question is required bro 😭"})

    # 1️⃣ Get DB schema
    schema = get_schema()

    # 2️⃣ Prompt Groq to generate SQL
    sql_prompt = [
        {
            "role": "system",
            "content": (
                "You are an expert SQL generator for a PostgreSQL database.\n"
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

    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=sql_prompt,
    )

    raw_sql = completion.choices[0].message.content.strip()
    generated_sql = clean_sql(raw_sql)

    if generated_sql.endswith(";"):
        generated_sql = generated_sql[:-1]

    # 3️⃣ Block dangerous SQL
    lowered = generated_sql.lower()
    for word in FORBIDDEN:
        if word in lowered:
            return Response({
                "error": "Dangerous SQL blocked bro 🔥",
                "sql": generated_sql,
            })

    # 4️⃣ Execute SQL safely
    try:
        with connection.cursor() as cursor:
            cursor.execute(generated_sql)
            result = cursor.fetchall()

        # 5️⃣ Ask Groq to explain result
        explain_prompt = [
            {
                "role": "system",
                "content": (
                    "You are a senior data analyst. "
                    "Explain the SQL result in clear, simple English. "
                    "Be concise and highlight key insights."
                ),
            },
            {
                "role": "user",
                "content": f"SQL Result: {result}",
            },
        ]

        explanation_completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=explain_prompt,
        )

        explanation = explanation_completion.choices[0].message.content.strip()

    except Exception as e:
        return Response({
            "error": f"Database Error: {str(e)}",
            "sql": generated_sql,
        })

    # 6️⃣ Final response
    return Response({
        "message": "SQL executed successfully bro! 🚀",
        "sql": generated_sql,
        "result": result,
        "explanation": explanation,
    })
