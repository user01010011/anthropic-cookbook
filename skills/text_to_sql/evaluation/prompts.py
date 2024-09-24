import sqlite3

DATABASE_PATH = '../data/data.db'

def get_schema_info():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    schema_info = []
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    for (table_name,) in tables:
        # Get columns for this table
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        
        table_info = f"Table: {table_name}\n"
        table_info += "\n".join(f"  - {col[1]} ({col[2]})" for col in columns)
        schema_info.append(table_info)
    
    conn.close()
    return "\n\n".join(schema_info)

def generate_prompt(context):
    user_query = context['vars']['user_query']
    schema = get_schema_info()
    return f"""
    You are an AI assistant that converts natural language queries into SQL. 
    Given the following SQL database schema:

    {schema}

    Convert the following natural language query into SQL:

    {user_query}

    Provide only the SQL query in your response, enclosed within <sql> tags.
    """

def generate_prompt_with_examples(context):
    user_query = context['vars']['user_query']
    examples = """
        Example 1:
        <query>List all employees in the HR department.</<query>
        <output>SELECT e.name FROM employees e JOIN departments d ON e.department_id = d.id WHERE d.name = 'HR';</output>

        Example 2:
        User: What is the average salary of employees in the Engineering department?
        SQL: SELECT AVG(e.salary) FROM employees e JOIN departments d ON e.department_id = d.id WHERE d.name = 'Engineering';

        Example 3:
        User: Who is the oldest employee?
        SQL: SELECT name, age FROM employees ORDER BY age DESC LIMIT 1;
    """

    schema = get_schema_info()

    return f"""
        You are an AI assistant that converts natural language queries into SQL.
        Given the following SQL database schema:

        <schema>
        {schema}
        </schema>

        Here are some examples of natural language queries and their corresponding SQL:

        <examples>
        {examples}
        </examples>

        Now, convert the following natural language query into SQL:
        <query>
        {user_query}
        </query>

        Provide only the SQL query in your response, enclosed within <sql> tags.
    """

def generate_prompt_with_cot(context):
    user_query = context['vars']['user_query']
    schema = get_schema_info()
    examples = """
    <example>
    <query>List all employees in the HR department.</query>
    <thought_process>
    1. We need to join the employees and departments tables.
    2. We'll match employees.department_id with departments.id.
    3. We'll filter for the HR department.
    4. We only need to return the employee names.
    </thought_process>
    <sql>SELECT e.name FROM employees e JOIN departments d ON e.department_id = d.id WHERE d.name = 'HR';</sql>
    </example>

    <example>
    <query>What is the average salary of employees hired in 2022?</query>
    <thought_process>
    1. We need to work with the employees table.
    2. We need to filter for employees hired in 2022.
    3. We'll use the YEAR function to extract the year from the hire_date.
    4. We'll calculate the average of the salary column for the filtered rows.
    </thought_process>
    <sql>SELECT AVG(salary) FROM employees WHERE YEAR(hire_date) = 2022;</sql>
    </example>
    """

    return f"""You are an AI assistant that converts natural language queries into SQL.
    Given the following SQL database schema:

    <schema>
    {schema}
    </schema>

    Here are some examples of natural language queries, thought processes, and their corresponding SQL:

    <examples>
    {examples}
    </examples>

    Now, convert the following natural language query into SQL:
    <query>
    {user_query}
    </query>

    Within <thought_process> tags, explain your thought process for creating the SQL query.
    Then, within <sql> tags, provide your output SQL query.
    """

def generate_prompt_with_rag(context):
    from vectordb import VectorDB

    # Load the vector database
    vectordb = VectorDB()
    vectordb.load_db()

    user_query = context['vars']['user_query']

    if not vectordb.embeddings:
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            schema_data = [
                {"text": f"Table: {table[0]}, Column: {col[1]}, Type: {col[2]}", 
                "metadata": {"table": table[0], "column": col[1], "type": col[2]}}
                for table in cursor.fetchall()
                for col in cursor.execute(f"PRAGMA table_info({table[0]})").fetchall()
            ]
        vectordb.load_data(schema_data)
    
    relevant_schema = vectordb.search(user_query, k=10, similarity_threshold=0.3)
    schema_info = "\n".join([f"Table: {item['metadata']['table']}, Column: {item['metadata']['column']}, Type: {item['metadata']['type']}"
                             for item in relevant_schema])
    return f"""
    You are an AI assistant that converts natural language queries into SQL.
    Given the following relevant columns from the SQL database schema:

    {schema_info}

    Convert the following natural language query into SQL:

    {user_query}

    First, provide your thought process within <thought_process> tags, explaining how you'll approach creating the SQL query.
    Then, provide the SQL query within <sql> tags.

    Ensure your SQL query is compatible with SQLite syntax.
    """


def generate_prompt_with_self_improvement(context):
    from vectordb import VectorDB

    # Load the vector database
    vectordb = VectorDB()
    vectordb.load_db()

    user_query = context['vars']['user_query']

    if not vectordb.embeddings:
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            schema_data = [
                {"text": f"Table: {table[0]}, Column: {col[1]}, Type: {col[2]}", 
                "metadata": {"table": table[0], "column": col[1], "type": col[2]}}
                for table in cursor.fetchall()
                for col in cursor.execute(f"PRAGMA table_info({table[0]})").fetchall()
            ]
        vectordb.load_data(schema_data)

    relevant_schema = vectordb.search(user_query, k=10, similarity_threshold=0.3)
    schema_info = "\n".join([f"Table: {item['metadata']['table']}, Column: {item['metadata']['column']}, Type: {item['metadata']['type']}" 
                             for item in relevant_schema])
    
    return f"""You are an AI assistant that converts natural language queries into SQL.
    Given the following relevant columns from the SQL database schema:

    <schema>
    {schema_info}
    </schema>

    Convert the following natural language query into SQL:

    <query>
    {user_query}
    </query>

    Please provide up to three attempts to generate the correct SQL query. For each attempt:
    1. Explain your thought process in <thought_process> tags.
    2. Provide the SQL query in <sql> tags.
    3. Imagine you are executing this query. If you think it might fail, explain why in <error> tags.
    4. If you think the query might fail, provide an improved version in the next attempt.

    After your attempts, provide your final, best SQL query in <final_sql> tags.

    Format your response like this:

    <attempt1>
    <thought_process>
    Your thought process here
    </thought_process>
    <sql>
    Your SQL query here
    </sql>
    <error>
    Potential error message here (if any)
    </error>
    </attempt1>

    <attempt2>
    ...
    </attempt2>

    <attempt3>
    ...
    </attempt3>

    <final_sql>
    Your final, best SQL query here
    </final_sql>
    """