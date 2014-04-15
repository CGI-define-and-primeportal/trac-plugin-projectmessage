# Author: Danny Milsom <danny.milsom@cgi.com>
# Copyright (C) 2014 CGI IT UK Ltd

from trac.db import Table, Column, DatabaseManager

schema = 
        Table('termsofservice')[
            Column('name'),
            Column('message'),
            Column('button'),
            Column('mode'),
            Column('scope'),
            Column('perms'),
            Column('author'),
            Column('date', type='int64'),
            ],
        Table('termsofservice_record')[
            Column('name'),
            Column('user'),
            Column('time', type='int64'),
            Column('terms'),
            ]
        ]

def do_upgrade(env, i, cursor):
    db = env.get_dbconnection()
    cursor = db.cursor()
    db_connector, _ = DatabaseManager(env).get_connector()
    def do_create(db):
      for table in schema:
          for statement in db_connector.to_sql(table):
              cursor.execute(statement) 
      cursor.execute("INSERT INTO system (name, value) VALUES ('termsofservice_schema', %s)",
                     (str(1),))