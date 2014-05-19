# Author: Danny Milsom <danny.milsom@cgi.com>
# Copyright (C) 2014 CGI IT UK Ltd

from datetime import datetime
from itertools import izip
import json
import pytz

from trac.cache import cached
from trac.core import TracError
from trac.resource import ResourceNotFound
from trac.util.datefmt import from_utimestamp, to_utimestamp, parse_date

from projectmessage.api import ProjectMessageSystem
from simplifiedpermissionsadminplugin import SimplifiedPermissions
from simplifiedpermissionsadminplugin.model import Group

class ProjectMessage(object):
    """Class to represent project wide messages."""

    message_keys = ['name', 'message', 'button', 'mode', 'groups', 
                  'start', 'end', 'author', 'created_at']

    def __init__(self, env, name=None):

        self.env = env
        self.values = {}
        if name is not None:
            self._fetch_message(name)

    def _fetch_message(self, name):
        """
        Retrieves data representing an individual project message from the 
        database, and unpacks this into a values dictionary.

        If the name provided does not match a row in the project_message 
        table, we raise a ResourceNotFound exception."""

        db = self.env.get_read_db()
        cursor = db.cursor()
        cursor.execute("""SELECT name, message, button, mode, groups,
                                 start, "end", author, created_at
                          FROM project_message
                          WHERE name=%s""", (name,))
        row = cursor.fetchone()
        if row:
            for field, value in izip(self.message_keys, row):
                if field == 'groups':
                    self.values[field] = json.loads(value)
                if field in ['start', 'date']:
                    self.values[field] = from_utimestamp(value)
                else:
                    self.values[field] = value
        else:
            raise ResourceNotFound("Project message '%s' does not exist.", (name))

    def _populate_from_database(self, row):
        """
        Takes a row returned from a cursor and populates instance 
        attributes based on these values."""

        (name, message, button, mode, 
        groups, start, end, author, created_at) = row

        self['name'] = name
        self['message'] = message
        self['button'] = button
        self['mode'] = mode
        self['groups'] = json.loads(groups) if groups else None
        self['start'] = from_utimestamp(start)
        self['end'] = from_utimestamp(end)
        self['author'] = author
        self['created_at'] = from_utimestamp(created_at)

    def __getitem__(self, key):
        return self.values.get(key)

    def __setitem__(self, key, value):
        self.values[key] = value

    @property
    def unique_name(self):
        """
        Returns a boolean to indicate if the name attribute refers to a 
        row already inserted into the projectmessage database.

        If the name is still None, returns False without querying the db.
        """

        if self['name'] is None:
            return False

        db = self.env.get_read_db()
        cursor = db.cursor()
        cursor.execute("""SELECT name
                          FROM project_message
                          WHERE name=%s""", (self['name'],))

        return False if cursor.fetchone() else True

    @property
    def valid_dates(self):
        """
        Returns a boolean to indicate if the start and end dates are valid.

        We pass these respective values to the trac utils parse_date function, 
        which will raise a ValueError exception if the date format of the 
        string is not ISO-8601 compliant.

        We also check that the end date is greater than the start date.
        """

        for date in (self['start'], self['end']):
            try:
                parse_date(date)
            except TracError:
                return False

        return self['start'] < self['end']

    @property
    def valid_mode(self):
        """
        Returns a boolean to indicate if the mode attribute is valid. This is 
        determinded by checking to see if the mode is included in the 
        projectmessage modes ListOption from the trac-ini.
        """

        if self['mode'] in ProjectMessageSystem(self.env).mode_options:
            return True
        else:
            return False

    @property
    def valid_groups(self):
        """
        Returns a boolean to indicate if the groups value is valid.

        This is determinded by checking to see if the groups attribute is 
        iterable, but not a string.

        First we check if the self.groups object is an instance of type 
        basestring (aka a unicode or bytestring object in Python 2.x). If this 
        returns True, we return False to indicate that the value is 
        invalid for our purposes.

        If we pass this condition, we then check that the object supports the 
        iterator protocol.
        """

        if isinstance(self['groups'], basestring):
            return False

        try:
            iter(self['groups'])
        except TypeError:
            return False

        return True

    def populate(self, values):
        """
        Populate attributes by passing a dictionary.

        Attributes are only updated if they are valid (aka listed in message_keys)
        """

        for k, v in values.iteritems():
            if k in self.message_keys:
                self.values[k] = v

    def validate(self):
        """
        Validates the attributes of the instance. This is implicitly called by 
        the insert() method, but can also be used as part of the API.
        """

        if all([self.unique_name, self.valid_dates, self.valid_groups, self.valid_mode]):
            return all([self['message'], self['button'], self['author']])
        else:
            return False

    def insert(self):
        """
        Insert a new project message row into the database table.

        Before any insert transaction is committed, we validate the data.

        After a successful insert, appropriate caches are invalidated.
        """

        if self.validate():
            args = []
            for key in self.message_keys:
                if key == 'groups':
                    args.append(json.dumps(self[key]))
                elif key in ['start', 'end']:
                    args.append(to_utimestamp(parse_date(self[key])))
                else:
                    args.append(self[key])

            @self.env.with_transaction()
            def do_insert(db):
                cursor = db.cursor()
                self.env.log.debug("Creating new projet message - %s", self['name'])
                cursor.execute("""INSERT INTO project_message (name, message, 
                                    button, mode, groups, 
                                    start, "end", author, created_at)
                                  VALUES (%s, %s, %s, %s, %s, 
                                    %s, %s, %s, %s)
                                """, args)

        del self._get_all_messages

    def hide(self):
        """
        We do not allow users to delete project messages, but they can be 
        hidden. This will stop the notification appearing in the user 
        interface, and is represented as a NULL value in the groups column.
        """

        @self.env.with_transaction()
        def do_update(db):
            cursor = db.cursor()
            self.env.log.info('Updating project message table so %s '
                              'is hidden', self['name'])
            cursor.execute("""UPDATE project_message
                              SET groups=%s
                              WHERE name=%s""", (None, self['name']))

    @classmethod
    def get_all_messages(cls, env):
        """
        Returns all project messages stored in the project_message table, 
        ordered by the creation timestamp.

        This result is cached for performance, but due to the 
        implementation of the trac cache system, we have to call an instance 
        method for this to work.
        """

        result = []
        for row in ProjectMessage(env)._get_all_messages:
            msg = ProjectMessage(env)
            msg._populate_from_database(row)
            result.append(msg)
        return result

    @cached
    def _get_all_messages(self, db):
        """
        Cache is invalidated after an insert into the project_message table."""
        cursor = db.cursor()
        cursor.execute("""SELECT name, message, button, mode, groups, 
                                 start, "end", author, created_at
                          FROM project_message
                          ORDER BY created_at""")
        return cursor.fetchall()

    @classmethod
    def get_filtered_messages(cls, env, username=None):
        """
        Returns filtered messages, accounting for the date, membership and 
        hidden attributes each message has.

        We always filter by date and remove any hidden messages.

        If a username is passed, we check their membership groups to 
        filter the messages accordingly too.
        """

        all_msgs = ProjectMessage.get_all_messages(env)
        today = datetime.now(pytz.utc)
        filtered_msgs = [msg for msg in all_msgs
                         if msg['start'] <= today < msg['end'] and
                         msg['groups'] is not None]

        if username is not None:
            sp = SimplifiedPermissions(env)
            user_groups = sp.group_memberships_for_user(username) + ["*"]
            filtered_msgs = [msg for msg in filtered_msgs
                                        if any(group in msg['groups'] 
                                            for group in user_groups)]

        return filtered_msgs

    @classmethod
    def get_agreed_messages(cls, env, user):
        """
        Returns a list of all project messages the specified user has 
        acknowledged, ordered by agreement date.
        """

        db = env.get_read_db()
        cursor = db.cursor()
        cursor.execute("""SELECT m.name, m.message, m.button, m.mode,
                                 m.groups, m.start, m."end",
                                 m.author, m.created_at
                          FROM project_message as m
                          JOIN project_message_record as r
                            ON m.name = r.message_name
                          WHERE r.agreed_by=%s
                          ORDER BY r.agreed_at""", (user,))

        result = []
        for row in cursor.fetchall():
            msg = ProjectMessage(env)
            msg._populate_from_database(row)
            result.append(msg)
        return result

    @classmethod
    def get_unagreed_messages(cls, env, username, mode=None):
        """
        Identifies project messages the specified user has not acknowledged, 
        returning them sorted by date.

        If a mode argument is passed, we filter the results so only 
        messages with the mode key specified are returned. By default 
        this is None, so all unseen messages are returned.

        The returned results also respect any membership group and date 
        filters set, as we call get_filtered_messages().
        """

        if mode:
            all_msgs = [m for m in ProjectMessage.get_filtered_messages(env, username) 
                            if m['mode'] == mode]
        else:
            all_msgs = [m for m in ProjectMessage.get_filtered_messages(env, username)]

        agreed_msgs = [m['name'] for m in ProjectMessage.get_agreed_messages(env, username)]
        unseen = set(m['name'] for m in all_msgs) - set(agreed_msgs)

        return [m for m in all_msgs if m['name'] in unseen]


class ProjectMessageRecord(object):
    """
    Class to represent records detailing the acknowledgement of a project 
    message.
    """

    record_keys = ['record_id', 'message_name', 'agreed_by', 'agreed_at']

    def __init__(self, env, record_id=None):
        self.env = env
        self.values = {}
        if record_id is not None:
            self._fetch_record(record_id)

    def _fetch_record(self, record_id):
        """
        Retrieves data representing an individual project message from the 
        database, and unpacks this into a values dictionary.

        If the name provided does not match a row in the project_message 
        table, we raise a ResourceNotFound exception."""

        db = self.env.get_read_db()
        cursor = db.cursor()
        cursor.execute("""SELECT record_id, message_name, agreed_by, agreed_at
                          FROM project_message_record
                          WHERE record_id=%s""", (record_id,))
        row = cursor.fetchone()
        if row:
            for field, value in izip(self.record_keys, row):
                if field == 'agreed_at':
                    self.values[field] = from_utimestamp(value)
                else:
                    self.values[field] = value
        else:
            raise ResourceNotFound("Project message record '%s' does "
                                   "not exist.", (record_id))

    def _populate_from_database(self, row):
        """
        Takes a row returned from a cursor and populates instance 
        attributes based on these values.
        """

        (record_id, name, user, agreed_at) = row

        self['record_id'] = record_id
        self['message_name'] = name
        self['agreed_by'] = user
        self['agreed_at'] = from_utimestamp(agreed_at)

    def __getitem__(self, key):
        return self.values.get(key)

    def __setitem__(self, key, value):
        self.values[key] = value

    def populate(self, req):
        """
        Populate attributes by passing the request object as an argument.
        """

        self['message_name'] = req.args.get('name')
        self['agreed_by'] = req.authname
        self['agreed_at'] = to_utimestamp(datetime.now(pytz.utc))

    def insert(self):
        """
        Inserts a new row into the project_message_record table, to record 
        the details surrounding the acknowledgement of any message.
        """

        @self.env.with_transaction()
        def add_record(db):
            args = []
            for key in [k for k in self.record_keys if k != 'record_id']:
                args.append(self[key])
            cursor = db.cursor()
            cursor.execute("""INSERT into project_message_record(message_name, agreed_by, agreed_at) 
                              VALUES (%s, %s, %s)""", args)

        del self._get_all_records

    @classmethod
    def get_all_records(cls, env):
        """
        Returns a list of all records, detailing the messages acknowledged 
        by each user. For convenience this is sorted by agreement date, 
        and cached for performance.
        """

        result = []
        for row in ProjectMessageRecord(env)._get_all_records:
            record = ProjectMessageRecord(env)
            record._populate_from_database(row)
            result.append(record)
        return result

    @cached
    def _get_all_records(self, db):
        """
        Cache is invalidated after an insert into the project_message_records 
        table.
        """

        cursor = db.cursor()
        cursor.execute("""SELECT record_id, message_name, agreed_by, agreed_at
                          FROM project_message_record
                          ORDER BY agreed_at""")
        return cursor.fetchall()

    @classmethod
    def get_user_records(cls, env, username):
        """
        Returns a list of all message that the specified user has acknowledged.
        For convenience the result is ordered by agreement date.
        """

        db = env.get_read_db()
        cursor = db.cursor()
        cursor.execute("""SELECT record_id, message_name, agreed_by, agreed_at
                          FROM project_message_record
                          WHERE agreed_by=%s
                          ORDER BY agreed_at""", (username,))

        result = []
        for row in cursor.fetchall():
            record = ProjectMessageRecord(env)
            record._populate_from_database(row)
            result.append(record)
        return result