"""Database connector tool scaffold."""
def get_connection():
    return psycopg2.connect(
        host="localhost",
        port=5433,
        dbname="sql_optimizer",
        user="y",
        password="mypassword123"
    )