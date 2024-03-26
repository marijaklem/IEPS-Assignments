import psycopg2

# Sample data for insertion
sample_data = {
    "domain": "example.com",
    "robots_content": "Sample robots content",
    "sitemap_content": "Sample sitemap content"
}

# Connect to the database
conn = psycopg2.connect(database="postgres", user="postgres", password="SMRPO_skG", host="localhost", port="5432")

# Create a cursor
cur = conn.cursor()

try:
    # Insert sample data into the database
    cur.execute("INSERT INTO crawldb.site (domain, robots_content, sitemap_content) VALUES (%s, %s, %s)", 
                (sample_data["domain"], sample_data["robots_content"], sample_data["sitemap_content"]))
    
    # Commit the transaction
    conn.commit()
    print("Data inserted successfully!")
    
    # Query the database to verify insertion
    cur.execute("SELECT * FROM crawldb.site WHERE domain = %s", (sample_data["domain"],))
    inserted_record = cur.fetchone()
    print("Inserted record:", inserted_record)
    
except psycopg2.Error as e:
    print("Error:", e)

finally:
    # Close cursor and connection
    cur.close()
    conn.close()
