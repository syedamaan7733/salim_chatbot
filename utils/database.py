import os

import psycopg2
import json
from psycopg2.extras import RealDictCursor

class PostgreSQLConnector:
    def __init__(self):
        self.host = os.getenv('TARGET_HOST')
        self.user = os.getenv('TARGET_USER')
        self.password = os.getenv('TARGET_PASSWORD')
        self.database = os.getenv('TARGET_DATABASE')
        self.port = int(os.getenv('TARGET_PORT'))
        self.schema = os.getenv('TARGET_SCHEMA')
        self.connection = None
        self.table_columns = {}  # Store column names for tables

    def create_connection(self):
        return psycopg2.connect(
            host=self.host,
            user=self.user,
            password=self.password,
            database=self.database,
            port=self.port,
            cursor_factory=RealDictCursor,
            options=f'-c search_path={self.schema}'
        )
        
    def execute_query(self, query: str):
        print(f"Query -> {query}")
        with self.create_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query)
                if query.strip().upper().startswith('SELECT'):
                    rows = [dict(row) for row in cursor.fetchall()]
                    return rows
                else:
                    connection.commit()

    def fetch_columns(self, tbl_name: str):
        if tbl_name in self.table_columns:
            return self.table_columns[tbl_name]
        
        query = f"""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = '{self.schema}' AND table_name = '{tbl_name}';
        """
        columns = self.execute_query(query)
        column_names = [col['column_name'] for col in columns]
        self.table_columns[tbl_name] = column_names
        return column_names
    
    def preprocess_data(self, tbl_name, data):
        columns = self.fetch_columns(tbl_name)
        valid_data = {key: value for key, value in data.items() if key in columns}
        if not valid_data:
            raise ValueError("No valid data provided for the table columns.")
        for key, value in valid_data.items():
            if type(value) is list or type(value) is dict:
                valid_data[key] = json.dumps(value)
        return valid_data
        
        

    def insert(self, tbl_name: str, data: dict):       
        valid_data = self.preprocess_data(tbl_name, data) 
        column_names = ', '.join(valid_data.keys())
        placeholders = ', '.join(f"'{value}'" for value in valid_data.values())
        
        query = f"""
        INSERT INTO {self.schema}.{tbl_name} ({column_names})
        VALUES ({placeholders});
        """
        
        return self.execute_query(query)

    def update(self, tbl_name: str, data: dict, condition: str = ''):
        valid_data = self.preprocess_data(tbl_name, data) 
        set_clause = ', '.join(f"{key} = '{value}'" for key, value in valid_data.items())
        
        query = f"""
        UPDATE {self.schema}.{tbl_name}
        SET {set_clause}
        """
        if condition:
            query += f" WHERE {condition};"
        else:
            query += ";"
        
        return self.execute_query(query)

    def upsert(self, tbl_name: str, data: dict, conflict_columns: list):
        valid_data = self.preprocess_data(tbl_name, data) 
        column_names = ', '.join(valid_data.keys())
        placeholders = ', '.join(f"'{value}'" for value in valid_data.values())
        
        update_clause = ', '.join(f"{key} = EXCLUDED.{key}" for key in valid_data.keys() if key not in conflict_columns)
        conflict_target = ', '.join(conflict_columns)
        
        query = f"""
        INSERT INTO {self.schema}.{tbl_name} ({column_names})
        VALUES ({placeholders})
        ON CONFLICT ({conflict_target})
        DO UPDATE SET {update_clause};
        """
        
        return self.execute_query(query)