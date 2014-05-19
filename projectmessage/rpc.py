# Author: Danny Milsom <danny.milsom@cgi.com>
# Copyright (C) 2014 CGI IT UK Ltd

from datetime import datetime
import pytz

from trac.core import Component, implements
from trac.resource import ResourceNotFound
from tracrpc.api import IXMLRPCHandler
from trac.util.datefmt import to_utimestamp

from projectmessage.models import ProjectMessage


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
        except DatabaseError:
            self.log.info("Database error when creating a new project message via XMLRPC.")
            return "Unable to create a new project message."
        else:
            self.log.info("Successfully created new project message via XMLRPC.")
            return "Successfully created new project message."
