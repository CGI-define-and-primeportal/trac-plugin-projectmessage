# Author: Danny Milsom <danny.milsom@cgi.com>
# Copyright (C) 2014 CGI IT UK Ltd

from datetime import datetime
import pytz

from trac.config import ListOption
from trac.core import Component, TracError, implements
from trac.db import Table, Column, DatabaseManager
from trac.env import IEnvironmentSetupParticipant
from trac.perm import IPermissionRequestor
from trac.resource import ResourceNotFound
from tracrpc.api import IXMLRPCHandler
from trac.util.datefmt import to_utimestamp
from trac.util.translation import _

from projectmessage.models import ProjectMessage


class ProjectMessageSystem(Component):
    """
    Creates the project_message and project_message_report tables, and defines 
    new permission actions applicable to this plugin.
    """

    implements(IEnvironmentSetupParticipant, IPermissionRequestor)

    # IPermissionRequestor method

    def get_permission_actions(self):
        return ['PROJECTMESSAGE_VIEW', 'PROJECTMESSAGE_CREATE',
                ('TRAC_ADMIN', ['PROJECTMESSAGE_VIEW', 
                                'PROJECTMESSAGE_CREATE'])]

    # IEnvironmentSetupParticipant

    _schema_version = 2
    schema = [
        Table('project_message')[
            Column('name'),
            Column('message'),
            Column('button'),
            Column('mode'),
            Column('groups'),
            Column('start', type='int64'),
            Column('end', type='in64'),
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

    def environment_created(self):
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        db_connector, _ = DatabaseManager(self.env).get_connector()
        @self.env.with_transaction()
        def do_create(db):
            for table in self.schema:
                for statement in db_connector.to_sql(table):
                    cursor.execute(statement)
            cursor.execute("""INSERT INTO system (name, value) 
                              VALUES ('projectmessage_schema', %s)""", 
                           (str(self._schema_version),))

    def _check_schema_version(self, db):
        cursor = db.cursor()
        cursor.execute("""SELECT value 
                          FROM system 
                          WHERE name = 'projectmessage_schema'""")
        row = cursor.fetchone()
        return int(row[0]) if row else 0

    def environment_needs_upgrade(self, db):
        found_version = self._check_schema_version(db)
        if not found_version:
            self.log.debug("Initial schema needed for projectmessage plugin.")
            return True
        else:
            if found_version < self._schema_version:
                self.log.debug("Upgrade schema from %d to %d needed for "
                               "projectmessage plugin.", found_version, 
                               self._schema_version)
                return True

    def upgrade_environment(self, db):
        self.log.debug("Upgrading schema for projectmessage plugin.")

        cursor = db.cursor()
        db_ver = self._check_schema_version(db)
        for i in range(db_ver + 1, self._schema_version + 1):
            name  = 'db%i' % i
            try:
                upgrades = __import__('upgrades', globals(), locals(), [name])
                script = getattr(upgrades, name)
            except AttributeError:
                raise TracError(_('No upgrade module for version %(num)i '
                                  '(%(version)s.py)', num=i, version=name))
            script.do_upgrade(self.env, i, cursor)
            cursor.execute("""
                UPDATE system SET value=%s WHERE name='projectmessage_schema'
                """, (i,))
            self.log.info('Upgraded database version from %d to %d', i - 1, i)
            db.commit()


class ProjectMessageRPC(Component):
    """Create and retrieve information from the project_message table. """

    implements(IXMLRPCHandler)

    # IXMLRPCHandler methods
    def xmlrpc_namespace(self):
        return 'project_message'

    def xmlrpc_methods(self):
        yield ('PROJECTMESSAGE_CREATE', ((list, str, str, str, str, list, str, str),), 
                                self.createMessage)

    def createMessage(self, req, name, message, button, 
                            mode, groups, start, end):
        """Create a new project message.

        :param string: name
        :param string: text (supports wiki formatting)
        :param string: button text
        :param string: mode ('Alert' or 'Full Screen')
        :param list: groups who can see the message (['groupA', 'groupB'])
        :param string: start date (ISO-8601 26-07-2014)
        :param string: end date (ISO-8601 30-07-2014)
        """

        try:
            ProjectMessage(self.env, name)
        except ResourceNotFound:
            self.log.debug("Name %s is unique - creating new project message.", name)
        else:
            return ("Unable to create a new project message. Please choose a "
                    "different name, %s is already in use." % (name))

        msg = ProjectMessage(self.env)
        msg['name'] = name
        msg['message'] = message
        msg['button'] = button
        msg['mode'] = mode
        msg['groups'] = groups
        msg['start'] = start
        msg['end'] = end
        msg['author'] = req.authname
        msg['created_at'] = to_utimestamp(datetime.now(pytz.utc))

        if not msg.validate():
            return "Could not create a new message. Some attributes are invalid."

        try:
            msg.insert()
        except:
            self.log.info("Unable to create new project message via XMLRPC.")
            return "Unable to create a new project message." 
        else:
            self.log.info("Successfully created new project message via XMLRPC.")
            return "Successfully created new project message."
