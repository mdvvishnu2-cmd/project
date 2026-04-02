from flask import Flask
from flask_mysqldb import MySQL
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
mysql = MySQL(app)

with app.app_context():
    try:
        cur = mysql.connection.cursor()
        try:
            cur.execute("ALTER TABLE elections ADD COLUMN release_date DATETIME;")
            print("Successfully added `release_date` column!")
        except Exception as e:
            if "Duplicate column name" in str(e):
                print("`release_date` column already exists.")
            else:
                print(f"Error adding `release_date`: {e}")
                
        # Update existing elections to have release_date equal to end_date if it is null
        cur.execute("UPDATE elections SET release_date = end_date WHERE release_date IS NULL;")
        
        mysql.connection.commit()
        cur.close()
        print("\nDatabase update process finished.")
    except Exception as e:
        print(f"Database connection error: {e}")
