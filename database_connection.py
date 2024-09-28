#database imports
import psycopg2
import pandas as pd

def connect_to_postgresql(database_url):
    try:
        # Connect to the PostgreSQL database
        conn = psycopg2.connect(database_url)
        print("The database is connected")
        return conn
    except Exception as e:
        print("Error connecting to PostgreSQL:", e)
        return None



# Call the function to establish the connection


#-----------------
#databse tbale connection function
def get_table_data(connection, table_name):
    if connection:
        try:
            # Create a cursor object
            cursor = connection.cursor()

            # Execute the SQL query (use parameterized query to prevent SQL injection)
            query = f"SELECT * FROM {table_name}"
            cursor.execute(query)

            # Fetch all results
            results = cursor.fetchall()

            # Get the column names
            column_names = [desc[0] for desc in cursor.description]

            # Convert the result into a DataFrame
            df = pd.DataFrame(results, columns=column_names)

            return df  # Return the DataFrame

        except Exception as e:
            print("Error executing query:", e)
            return None

        finally:
            # Close the cursor and connection
            #cursor.close()
            #connection.close()
            print("The connection is closed")
    else:
        print("No connection available")
        return None