import sqlite3
from contextlib import closing

DBNAME = 'env.db'

class db_entry():
    def __init__(self) -> None:        
        pass
    def create_db(self):
        with closing(sqlite3.connect(DBNAME)) as con:
            cur = con.cursor()
            sql = 'CREATE TABLE enviroment (data_id integer PRIMARY KEY AUTOINCREMENT, date TIMESTAMP DEFAULT(DATETIME(\'now\', \'localtime\')), tmp real NOT NULL, hum real NOT NULL)'
            cur.execute(sql)
            con.commit()
            con.close()
    def insert_db(self, tmp, hum):
        with closing(sqlite3.connect(DBNAME)) as con:
            cur = con.cursor()
            sql = 'insert into enviroment (tmp , hum) values (?,?)'
            data = (tmp, hum)
            cur.execute(sql, data)
            con.commit()
            con.close()
    def read_db(self):
        with closing(sqlite3.connect(DBNAME)) as con:
            cur = con.cursor()
            sql = 'select * from test '
            for row in cur.execute(sql):
                print(row)
            con.close()

def main ():
    db = db_entry()
    try:
        db.create_db()
    except:
        pass
    db.insert_db(12.34, 43.21)
    db.read_db()


if __name__ == '__main__':
    main()
