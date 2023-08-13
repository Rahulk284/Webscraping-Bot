import mysql.connector
from datetime import datetime

db = mysql.connector.connect(
    host="localhost",
    user="root",
    passwd="Sarvdayal1943",
    database="testdatabase",
)

mycursor = db.cursor()

# mycursor.execute("CREATE TABLE Test (name varchar(50) NOT NULL, created datetime NOT NULL, gender ENUM('M', 'F', 'O') NOT NULL, id int PRIMARY KEY NOT NULL AUTO_INCREMENT)")
# mycursor.execute("INSERT INTO Test (name, created, gender) VALUES (%s, %s, %s)", ("Navjot", datetime.now(), "M"))

mycursor.execute("ALTER TABLE Test CHANGE first_name first_name VARCHAR(6)")

mycursor.execute("DESCRIBE Test")

for x in mycursor:
    print(x)


