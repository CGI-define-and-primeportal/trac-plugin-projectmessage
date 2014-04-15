# Author: Danny Milsom <danny.milsom@cgi.com>
# Copyright (C) 2014 CGI IT UK Ltd

from trac.db import Table, Column, DatabaseManager

schema = [
    Table('project_message')[
        Column('name'),
        Column('message'),
        Column('button'),
        Column('mode'),
        Column('groups'),
        Column('start', type='int64'),
        Column('end', type='int64'),
        Column('author'),
        Column('created_at', type='int64'),
        ],
    Table('project_message_record')[
        Column('record_id', auto_increment=True),
        Column('message_name'),
        Column('agreed_by'),
        Column('agreed_at', type='int64'),
        ]
    ]

def do_upgrade(env, i, cursor):
    cursor.execute("""CREATE TEMPORARY TABLE termsofservice_old 
                      AS SELECT * FROM termsofservice""")
    cursor.execute("""CREATE TEMPORARY TABLE termsofservice_record_old
                    AS SELECT * FROM termsofservice_record""")
    cursor.execute("DROP TABLE termsofservice")
    cursor.execute("DROP TABLE termsofservice_record")

    db_connector, _ = DatabaseManager(env)._get_connector()
    for table in schema:
        for statement in db_connector.to_sql(table):
            cursor.execute(statement)

    cursor.execute("""INSERT into project_message (name, message, button, mode, groups, start, end, author, created_at)
                  SELECT name, message, button, mode, NULL, NULL, NULL, author, "date" FROM termsofservice_old""")
    cursor.execute("""INSERT into project_message_record (message_name, agreed_by, agreed_at)
                    SELECT name, user, time FROM termsofservice_record_old""")
    cursor.execute('DROP TABLE termsofservice_old')
    cursor.execute('DROP TABLE termsofservice_record_old')

    cursor.execute("""UPDATE system
                      SET name='projectmessage_schema'
                      WHERE name='termsofservice_schema'
                   """)
