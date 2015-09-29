# Author: Danny Milsom <danny.milsom@cgi.com>
# Copyright (C) 2014 CGI IT UK Ltd

from datetime import datetime, timedelta
import json
import unittest

from trac.core import *
from trac.test import EnvironmentStub
from trac.util.datefmt import from_utimestamp

from projectmessage.models import ProjectMessage, ProjectMessageRecord
from projectmessage.api import ProjectMessageSystem

class ProjectMessageTestCase(unittest.TestCase):

    start_date = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
    end_date = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")

    default_data = {
            'name': "Test Term",
            'message': "Hello World!",
            'button': "Agree",
            'mode': "Alert",
            'groups': ["project_managers"],
            'start': start_date,
            'end': end_date,
            'author': "milsomd",
            'created_at': "1396975221114382",
            'foo': 'bar', # shouldn't be added as attribute via populate()
    }

    def setUp(self):
        self.env = EnvironmentStub(default_data=True)
        self.term_system = ProjectMessageSystem(self.env)
        self.term_system.environment_created()

    def tearDown(self):
        self.env.reset_db()

    def _create_new_message(self):
        msg = ProjectMessage(self.env)
        msg['name'] = "Test Term"
        msg['message'] = "Hello World!"
        msg['button'] = "Agree"
        msg['mode'] = "Alert"
        msg['groups'] = ["project_managers"]
        msg['start'] = self.start_date
        msg['end'] = self.end_date
        msg['author'] = "milsomd"
        msg['created_at'] = "1396975221114382"
        return msg

    def test_create_term(self):
        msg = self._create_new_message()
        self.assertEqual('Test Term', msg['name'])
        self.assertEqual('Hello World!', msg['message'])
        self.assertEqual('Agree', msg['button'])
        self.assertEqual(['project_managers'], msg['groups'])
        self.assertEqual("milsomd", msg['author'])
        self.assertEqual("1396975221114382", msg['created_at'])
        msg.insert()

    def test_get_term(self):
        # insert the ticket using dummy data
        msg = self._create_new_message()
        msg.insert()
        # retrieve ticket and test dummy data
        retrieved_msg = ProjectMessage(self.env, "Test Term")
        self.assertEqual('Test Term', retrieved_msg['name'])
        self.assertEqual('Hello World!', retrieved_msg['message'])
        self.assertEqual('Agree', retrieved_msg['button'])
        self.assertEqual(['project_managers'], json.loads(retrieved_msg['groups']))
        self.assertEqual("milsomd", retrieved_msg['author'])
        self.assertEqual(1396975221114382, retrieved_msg['created_at'])

    def test_term_is_valid(self):
        msg = self._create_new_message()
        self.assertEqual(True, msg.validate())

    def test_term_name_not_unique(self):
        msg = self._create_new_message()
        msg.insert()
        term2 = ProjectMessage(self.env)
        term2['name'] = msg['name']
        self.assertEqual(False, term2.unique_name)

    def test_dates_are_valid(self):
        msg = self._create_new_message()
        self.assertEqual(True, msg.valid_date_format)

    def test_dates_are_invalid(self):
        msg = ProjectMessage(self.env)
        msg['start'] = "2014-20-04" # not ISO-8601
        msg['end'] = "2014-30-04" # not ISO-8601
        self.assertEqual(False, msg.valid_date_format)

    def test_populate(self):
        msg = ProjectMessage(self.env)
        msg.populate(self.default_data)
        self.assertEqual('Test Term', msg['name'])
        self.assertEqual('Hello World!', msg['message'])
        self.assertEqual('Agree', msg['button'])
        self.assertEqual(['project_managers'], msg['groups'])
        self.assertEqual(self.start_date, msg['start'])
        self.assertEqual(self.end_date, msg['end'])
        self.assertEqual("milsomd", msg['author'])
        self.assertEqual("1396975221114382", msg['created_at'])
        self.assertRaises(AttributeError, lambda: msg.foo)
        msg.insert()

    def test_hide(self):
        msg = self._create_new_message()
        msg.insert()
        msg.hide()
        all_msgs = ProjectMessage(self.env).get_filtered_messages(self.env)
        self.assertEqual(0, len(all_msgs))

    def test_filtered_message_dates(self):
        # start date is before and end date is after today
        msg = self._create_new_message()
        msg['start'] = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
        msg['end'] = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
        msg.insert()
        filtered_msgs = ProjectMessage.get_filtered_messages(self.env)
        self.assertEqual(1, len(filtered_msgs))

    def test_filtered_message_dates_2(self):
        # start date is today and end date is tomorrow
        msg = self._create_new_message()
        msg.start = datetime.now().strftime("%Y-%m-%d")
        msg.end = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        msg.insert()
        filtered_msgs = ProjectMessage.get_filtered_messages(self.env)
        self.assertEqual(1, len(filtered_msgs))

    def test_filtered_message_dates_3(self):
        # start date is tomorrow and end date is next week
        msg = self._create_new_message()
        msg['start'] = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        msg['end ']= (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        msg.insert()
        filtered_msgs = ProjectMessage.get_filtered_messages(self.env)
        self.assertEqual(0, len(filtered_msgs))


class ProjectMessageRecordTestCase(unittest.TestCase):

    def setUp(self):
        self.env = EnvironmentStub(default_data=True)
        self.term_system = ProjectMessageSystem(self.env)
        self.term_system.environment_created()

    def tearDown(self):
        self.env.reset_db()

    def _create_new_record(self):
        record = ProjectMessageRecord(self.env)
        record['record_id'] = 1
        record['message_name'] = "Test Case"
        record['agreed_by'] = "milsomd"
        record['agreed_at'] = "1396975221114382"
        return record

    def _create_new_record_two(self):
        record = ProjectMessageRecord(self.env)
        record['record_id'] = 2
        record['message_name'] = "Another Test Case"
        record['agreed_by'] = "goldinge"
        record['agreed_at'] = "1396975221114388"
        return record

    def test_create_record(self):
        record = self._create_new_record()
        self.assertEqual(1, record['record_id'])
        self.assertEqual("Test Case", record['message_name'])
        self.assertEqual("milsomd", record['agreed_by'])
        self.assertEqual("1396975221114382", record['agreed_at'])
        record.insert()

    def test_get_term(self):
        record = self._create_new_record()
        record.insert()
        # retrieve data from db
        retrieved_record = ProjectMessageRecord(self.env, 1)
        self.assertEqual(1, retrieved_record['record_id'])
        self.assertEqual("Test Case", retrieved_record['message_name'])
        self.assertEqual("milsomd", retrieved_record['agreed_by'])
        self.assertEqual(from_utimestamp(1396975221114382), retrieved_record['agreed_at'])

    def test_get_all_records(self):
        record = self._create_new_record()
        record.insert()
        all_records = ProjectMessageRecord.get_all_records(self.env)
        self.assertEqual(1, len(all_records))
        self.assertEqual(1, all_records[0]['record_id'])
        self.assertEqual("Test Case", all_records[0]['message_name'])
        self.assertEqual("milsomd", all_records[0]['agreed_by'])
        self.assertEqual(from_utimestamp(1396975221114382), all_records[0]['agreed_at'])
        record2 = self._create_new_record_two()
        record2.insert()
        all_records = ProjectMessageRecord.get_all_records(self.env)
        self.assertEqual(2, len(all_records))
        self.assertEqual(2, all_records[1]['record_id'])
        self.assertEqual("Another Test Case", all_records[1]['message_name'])
        self.assertEqual("goldinge", all_records[1]['agreed_by'])
        self.assertEqual(from_utimestamp(1396975221114388), all_records[1]['agreed_at'])

    def test_get_user_records(self):
        record = self._create_new_record()
        record.insert()
        record2 = self._create_new_record_two()
        record2.insert()
        user_records = ProjectMessageRecord.get_user_records(self.env, "milsomd")
        self.assertEqual(1, user_records[0]['record_id'])
        self.assertEqual("Test Case", user_records[0]['message_name'])
        user_records = ProjectMessageRecord.get_user_records(self.env, "goldinge")
        self.assertEqual(2, user_records[0]['record_id'])
        self.assertEqual("Another Test Case", user_records[0]['message_name'])
        user_records = ProjectMessageRecord.get_user_records(self.env, "clarki")
        self.assertEqual([], user_records)

def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(ProjectMessageTestCase, 'test'))
    suite.addTest(unittest.makeSuite(ProjectMessageRecordTestCase, 'test'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
