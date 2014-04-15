# Author: Danny Milsom <danny.milsom@cgi.com>
# Copyright (C) 2014 CGI IT UK Ltd

from datetime import datetime
import pytz

from trac.admin import AdminCommandError, IAdminCommandProvider
from trac.core import Component, implements
from trac.resource import ResourceNotFound
from trac.util.datefmt import to_utimestamp

from projectmessage.models import ProjectMessage


class ProjectMessageAdmin(Component):
    """Providers trac-admin commands for project message administration."""

    implements(IAdminCommandProvider)

    # IAdminCommandProvider

    def get_admin_commands(self):
        yield ('projectmessage create', '<name> <message> <button> <mode> <start> <end> [groups]',
               """
               Creates a new project message users must acknowledge to hide.

               :param string: name
               :param string: text (supports wiki formatting)
               :param string: button text
               :param string: mode ('Alert' or 'Full Screen')
               :param string: start date (ISO-8601 26-07-2014)
               :param string: end date (ISO-8601 30-07-2014)
               :param string: optional arguments representing groups who should see this message

               """
               ,
               None, self._insert_message)

    # Other class methods

    def _insert_message(self, name, message, button, mode, start, end, *args):
        """
        Inserts a new project message into the project_message table, 
        validating each argument passed prior to the transaction 
        being completed.

        This code is intended to be used only by IAdminCommandProvider.
        """

        try:
            ProjectMessage(self.env, name)
        except ResourceNotFound:
            self.log.debug("Name is unique - creating message.")
        else:
            raise AdminCommandError("There is already a project message "
                                    "with the name %s. Please choose "
                                    "a different name." % name)

        new_msg = ProjectMessage(self.env)
        new_msg['name'] = name
        new_msg['message'] = message
        new_msg['button'] = button
        new_msg['mode'] = mode
        new_msg['groups'] = [group for group in args]
        new_msg['start'] = start
        new_msg['end'] = end
        new_msg['author'] = "system" # anyone could lie about who they are
        new_msg['created_at'] = to_utimestamp(datetime.now(pytz.utc))

        if not new_msg.validate():
            raise AdminCommandError("Could not create a new message. Some "
                                    "attributes are invalid.")

        try:
            new_msg.insert()
        except:
            AdminCommandError("We were unable to save that "
                             "message. Please try again.")
        else:
            AdminCommandError("You created a new project message.")
            self.log.info("Created a new project message - %s", name)
