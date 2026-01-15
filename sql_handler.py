import psycopg2
from psycopg2 import Error, errorcodes
import os
import dotenv

dotenv.load_dotenv()

class SQLHandler:
    def __init__(self):
        self.connection = self._create_server_connection()
        self.schema = os.environ.get("DB_SCHEMA", "patchwork_archive")
        self._load_database(os.environ.get("DB_DATABASE").strip())
    
    def _create_server_connection(self) -> psycopg2.extensions.connection:
        connection = None
        try:
            connection = psycopg2.connect(
                host=os.environ.get("DB_HOST"),
                database=os.environ.get("DB_DATABASE"),
                user=os.environ.get("DB_USERNAME"),
                password=os.environ.get("DB_PASSWORD"),
                port=os.environ.get("DB_PORT", "5432"),
                connect_timeout=10
            )
            connection.autocommit = False
        except Error as err:
            print(f"Error: '{err}'")
        if connection is None:
            print("Connection failed")
            exit(1)
        return connection

    def get_connection(self):
        return self.connection
    
    def _qualify_table_name(self, table_name: str) -> str:
        """Add schema prefix to table name if not already present"""
        if '.' not in table_name:
            return f"{self.schema}.{table_name}"
        return table_name

    def _create_database(self, cursor, database_name: str):
        try:
            cursor.execute(
                f"CREATE DATABASE {database_name} ENCODING 'UTF8'")
        except Error as err:
            print(f"Failed creating database: {err}")
            exit(1)

    def _load_database(self, database_name: str):
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            print(f"Database {database_name} loaded successfully")
        except Error as err:
            print(f"Failed to load database: {err}")
            exit(1)

    def create_table(self, name: str, column: str):
        cursor = self.connection.cursor()
        qualified_name = self._qualify_table_name(name)
        try:
            cursor.execute(f"CREATE TABLE {qualified_name} ({column})")
            self.connection.commit()
            print(f"Table {qualified_name} created successfully")
        except Error as err:
            self.connection.rollback()
            print(err)

    def insert_row(self, table_name: str, column: str, data: tuple):
        cursor = self.connection.cursor()
        qualified_name = self._qualify_table_name(table_name)
        try:
            placeholders = ', '.join(['%s'] * len(data))
            query = f"INSERT INTO {qualified_name} ({column}) VALUES ({placeholders})"
            cursor.execute(query, data)
            self.connection.commit()
            print("Data Inserted:", data)
        except Error as err:
            self.connection.rollback()
            print("Error inserting data")
            print(err)
            if "duplicate key" not in str(err).lower():
                return False
        return True

    def close_connection(self):
        if self.connection and not self.connection.closed:
            self.connection.close()
            print("PostgreSQL connection is closed")

    def clear_table(self, name: str):
        cursor = self.connection.cursor()
        qualified_name = self._qualify_table_name(name)
        try:
            cursor.execute(f"DELETE FROM {qualified_name}")
            self.connection.commit()
            print("Table cleared successfully")
        except Error as err:
            self.connection.rollback()
            print("Error clearing table")
            print(err)

    def reset_auto_increment(self, name: str):
        cursor = self.connection.cursor()
        qualified_name = self._qualify_table_name(name)
        try:
            # PostgreSQL uses sequences for auto-increment
            cursor.execute(f"SELECT setval(pg_get_serial_sequence('{qualified_name}', 'id'), 1, false)")
            self.connection.commit()
            print("Table reset successfully")
        except Error as err:
            self.connection.rollback()
            print("Error resetting table")
            print(err)

    def copy_rows_to_new_table(self, name: str, new_name: str, column: str):
        cursor = self.connection.cursor()
        qualified_name = self._qualify_table_name(name)
        qualified_new_name = self._qualify_table_name(new_name)
        try:
            cursor.execute(
                f"INSERT INTO {qualified_new_name} ({column}) SELECT {column} FROM {qualified_name}")
            self.connection.commit()
            print("Rows copied successfully")
        except Error as err:
            self.connection.rollback()
            print("Error copying rows")
            print(err)

    def drop_table(self, name: str):
        cursor = self.connection.cursor()
        qualified_name = self._qualify_table_name(name)
        try:
            cursor.execute(f"DROP TABLE {qualified_name}")
            self.connection.commit()
            print("Table dropped successfully")
        except Error as err:
            self.connection.rollback()
            print("Error dropping table")
            print(err)
    
    def check_row_exists(self, table_name: str, column_name: str, value: str):
        """
        Checks if a row exists in a table
        """
        cursor = self.connection.cursor()
        qualified_name = self._qualify_table_name(table_name)
        try:
            cursor.execute(f"SELECT * FROM {qualified_name} WHERE {column_name} = %s", (value,))
            result = cursor.fetchone()
            if result:
                return True
            else:
                return False
        except Error as err:
            print("Error checking row")
            print(err)

    def update_row(self, name: str, column_name: str, search_val: str, replace_col: str, new_value: str):
        """
        Updates a row in a table
        """
        cursor = self.connection.cursor()
        qualified_name = self._qualify_table_name(name)
        try:
            cursor.execute(f"UPDATE {qualified_name} SET {replace_col} = %s WHERE {column_name} = %s", (new_value, search_val))
            self.connection.commit()
            print("Row updated successfully")
        except Error as err:
            self.connection.rollback()
            print("Error updating row")
            print(err)
    
    def execute_query(self, query: str):
        cursor = self.connection.cursor()
        try:
            cursor.execute(query)
            result = cursor.fetchall()
            return result
        except Error as err:
            print("Error executing query")
            print(err)
    
    def get_query_result(self, query: str):
        cursor = self.connection.cursor()
        try:
            cursor.execute(query)
            result = cursor.fetchall()
            return result
        except Error as err:
            print("Error executing query")
            print(err)

    def delete_row(self, name: str, column: str, data: tuple):
        cursor = self.connection.cursor()
        qualified_name = self._qualify_table_name(name)
        try:
            query = f"DELETE FROM {qualified_name} WHERE {column} = %s"
            cursor.execute(query, data)
            self.connection.commit()
            print("Data Deleted:", data)
        except Error as err:
            self.connection.rollback()
            print("Error deleting data")
            print(err)
            return False
        return True
    
    def get_random_row(self, table_name: str, limit: int = 1):
        cursor = self.connection.cursor()
        qualified_name = self._qualify_table_name(table_name)
        try:
            # PostgreSQL uses RANDOM() instead of RAND()
            cursor.execute(f"SELECT * FROM {qualified_name} ORDER BY RANDOM() LIMIT {limit}")
            result = cursor.fetchall()
            return result
        except Error as err:
            print("Error getting random row")
            print(err)
    
    def search_video_row(self, table_name: str, keywords: list, limit: int = 1, offset: int = 0):
        cursor = self.connection.cursor()
        qualified_name = self._qualify_table_name(table_name)
        query = f"SELECT * FROM {qualified_name} WHERE 1=1"
        keyword_conditions = [] 

        for keyword in keywords:
            keyword_condition = f"LOWER(title) LIKE %s"
            formatted_keyword = f"%{keyword.lower()}%"  
            keyword_conditions.append((keyword_condition, formatted_keyword))  
        if keyword_conditions:
            query += " AND " + " AND ".join([condition[0] for condition in keyword_conditions])
        count_query = query
        query += " LIMIT %s OFFSET %s"

        try:
            cursor.execute(count_query, ([condition[1] for condition in keyword_conditions]))
            result_count = len(cursor.fetchall())
            cursor.execute(query, ([condition[1] for condition in keyword_conditions] + [limit, offset]))
            result = cursor.fetchall()
            return result, result_count
        except Error as err:
            print("Error searching video row")
            print(err)
    
    def search_romanized(self, table_name: str, keywords: list, limit: int = 1, offset: int = 0):
        cursor = self.connection.cursor()
        qualified_name = self._qualify_table_name(table_name)
        query = f"SELECT * FROM {qualified_name} S JOIN {self.schema}.romanized R on S.video_id=R.video_id WHERE 1=1"
        keyword_conditions = [] 

        for keyword in keywords:
            # PostgreSQL uses ~ for regex matching (case-sensitive) or ~* for case-insensitive
            keyword_condition = f"LOWER(romanized_title) ~ %s"
            formatted_keyword = f"\\y{keyword.lower()}\\y"  # \y is word boundary in PostgreSQL
            keyword_conditions.append((keyword_condition, formatted_keyword))  
        if keyword_conditions:
            query += " AND " + " AND ".join([condition[0] for condition in keyword_conditions])
        count_query = query
        query += " LIMIT %s OFFSET %s"

        try:
            cursor.execute(count_query, ([condition[1] for condition in keyword_conditions]))
            result_count = len(cursor.fetchall())
            cursor.execute(query, ([condition[1] for condition in keyword_conditions] + [limit, offset]))
            result = cursor.fetchall()
            return result, result_count
        except Error as err:
            print("Error searching video row")
            print(err)