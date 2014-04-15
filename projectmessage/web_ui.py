# Author: Danny Milsom <danny.milsom@cgi.com>
# Copyright (C) 2014 CGI IT UK Ltd

import copy
from datetime import datetime, timedelta
from genshi.builder import tag
from genshi.filters.transform import Transformer
import itertools
from pkg_resources import resource_filename
import pytz

from trac.admin.api import IAdminPanelProvider
from trac.config import Option, ListOption
from trac.core import Component, implements
from trac.mimeview import Context
from trac.prefs import IPreferencePanelProvider
from trac.resource import ResourceNotFound
from trac.util.datefmt import to_utimestamp
from trac.util.presentation import to_json
from trac.web import ITemplateStreamFilter
from trac.web.api import IRequestHandler
from trac.web.chrome import (ITemplateProvider, add_stylesheet,
                             Chrome, add_notice, add_script, add_warning)
from trac.web.main import IRequestFilter
from trac.wiki.formatter import format_to_html

from projectmessage.models import ProjectMessage, ProjectMessageRecord
from simplifiedpermissionsadminplugin.model import Group


class ProjectMessageUI(Component):
    """
    A notification system which allows users with the appropriate permissions 
    to create and send messages to project members through the user interface.

    You can set the timeout_period to reduce the number of database queries 
    executed with each request. We set a session attribute to track this, 
    and compare this timestamp to see if we should query for new notifications.
    """

    implements (IRequestHandler, IAdminPanelProvider, ITemplateStreamFilter,
                ITemplateProvider, IRequestFilter, IPreferencePanelProvider)

    timeout_period = Option('projectmessage', 'timeout_period', 
                    timedelta(minutes=10))

    mode_options = ListOption('projectmessage', 'modes', 
                    ['Alert', 'Full Screen'])

    url_requests = ListOption('projectmessage', 'url_requests', 
                    ['/projectmessage', '/ajax/projectmessage'])

    # IAdminPanelProvider methods 

    def get_admin_panels(self, req):
        if 'LOGIN_ADMIN' in req.perm:
            yield ('general', 'General', 'project-message', 
                        'Project Message')
            yield ('auditing', 'Auditing', 'project-message-records', 
                        'Project Message Records')

    def render_admin_panel(self, req, cat, page, path_info):

        if 'LOGIN_ADMIN' in req.perm:

            if (page == 'project-message' and 
                'PROJECTMESSAGE_CREATE' in req.perm):

                groups = (sid for sid in Group.groupsBy(self.env))
                previous_msgs = ProjectMessage.get_all_messages(self.env)
                for m in previous_msgs:
                    for k in ('created_at', 'start', 'end'):
                        m[k] = m[k].strftime('%Y-%m-%d')

                data = {
                        'mode_options': self.mode_options,
                        'group_options': itertools.chain(groups, ['*']),
                        'msgs': previous_msgs,
                        'start_date': datetime.now().strftime("%Y-%m-%d"),
                        'end_date': (datetime.now() + 
                                     timedelta(days=7)).strftime("%Y-%m-%d"),
                }

                # the message can be wiki mark-up
                Chrome(self.env).add_wiki_toolbars(req)
                add_script(req, 'projectmessage/js/project_message_admin.js')
                add_stylesheet(req, 'projectmessage/css/project_message_admin.css')

                if req.method == 'POST':
                    name = req.args.get('name')
                    message = req.args.get('message')
                    button = req.args.get('button')
                    mode = req.args.get('mode')
                    groups = req.args.get('groups', [])
                    start = req.args.get('start')
                    end = req.args.get('end')

                    if not all((name, message, button, mode, groups, start, end)):
                        add_notice(req, "Please complete the form - some "
                                        "fields were left blank.")
                        data.update(req.args)
                        return 'project_message_admin.html', data

                    new_msg = ProjectMessage(self.env)
                    msg_args = copy.deepcopy(req.args)
                    msg_args['author'] = req.authname
                    msg_args['created_at'] = to_utimestamp(datetime.now(pytz.utc))
                    if isinstance(groups, basestring):
                        msg_args['groups'] = [groups]
                    new_msg.populate(msg_args)

                    error = None
                    if not new_msg.unique_name:
                        add_notice(req, "There is already a project message "
                                        "with the name %s. Please choose "
                                        "a different name." % name)
                        error = True
                    elif not new_msg.valid_dates:
                        add_notice(req, "Incorrect format for %s date. "
                                        "Should be YYYY-MM-DD" % (new_msg.end))
                        error = True
                    if error:
                        data.update(req.args)
                        return 'project_message_admin.html', data

                    new_msg.insert()
                    try:
                        ProjectMessage(self.env, name)
                    except ResourceNotFound:
                        add_warning(req, "Unable to save project message. "
                            "Please try again.")
                        data.update(req.args)
                    else:
                        add_notice(req, "New project message created.")
                        self.log.info("New project message '%s' created", name)
                        data['msgs'].append(new_msg)

                return 'project_message_admin.html', data

            elif (page == 'project-message-records' and 
                'PROJECTMESSAGE_VIEW' in req.perm):

                records = ProjectMessageRecord.get_all_records(self.env)
                for r in records:
                    r['agreed_at'] = r['agreed_at'].strftime("%Y-%m-%d %H:%M")

                data = {
                        'records': records,
                }

                return 'project_message_records.html', data

    # IPreferencePanelProvider methods

    def get_preference_panels(self, req):
        yield ('projectmessage', 'Project Messages')

    def render_preference_panel(self, req, panel):

        agreed = ProjectMessageRecord.get_user_records(self.env, req.authname)
        for m in agreed:
            m['agreed_at'] = m['agreed_at'].strftime("%Y-%m-%d %H:%M")
        disagreed = ProjectMessage.get_unagreed_messages(self.env, req.authname)

        data = {
            'agreed': agreed,
            'unagreed': disagreed,
        }

        return 'project_message_prefs.html', data

    # IRequestFilter methods

    def pre_process_request(self, req, handler):
        """
        Check for full screen message to show authenticated user.

        If there are any full screen project message the authenticated user 
        has not agreed to, we redirect the user to a project message
        before their original request is processed.
        """

        if req.authname != 'anonymous':
            timeout_exceeded = self._timeout_limit_exceeded(req)
            if timeout_exceeded or timeout_exceeded is None:

                if (not req.path_info.startswith('/projectmessage') and not
                        req.path_info.startswith('/chrome') and
                        handler != self):
                    pm = ProjectMessage
                    unagreed_full_screen = pm.get_unagreed_messages(self.env, 
                                                req.authname, 'Full Screen')
                    if unagreed_full_screen:
                        m = unagreed_full_screen[0] # only show one at a time
                        return req.redirect(req.href.projectmessage(m['name']))

        return handler

    def post_process_request(self, req, template, data, content_type):
        return template, data, content_type

    # IRequestHandler methods

    def match_request(self, req):
        """
        Listens to Ajax requests and requests to render a full screen 
        project message.
        """

        return any(req.path_info.startswith(url) for url in self.url_requests)

    def process_request(self, req):
        """
        If the request is AJAX, inserts a new row into the record table for 
        the authenticated user to show they have seen a particular 
        notification.

        If the request is a normal GET, try and show the appropriate full 
        screen project message.
        """

        if req.path_info.startswith('/projectmessage'):
            try:
                name = req.path_info.split('/projectmessage/')[1]
            except IndexError:
                name = None
                self.log.debug("No project messages to show at "
                                "/projectmessage")

            if name:
                try:
                    msg = ProjectMessage(self.env, name)
                except ResourceNotFound:
                    self.log.debug("No project messages found")
                else:
                    add_script(req, 'projectmessage/js/project_message.js')
                    data = {
                        'name': msg['name'],
                        'message': msg['message'],
                        'button': msg['button'],
                    }
                    return 'project_message.html', data, None
            data = {'message': 'No project messages to show.'}
            return 'project_message.html', data, None

        elif (req.method == 'POST' and
                req.path_info.startswith('/ajax/projectmessage')):
            if req.args.get('name'):
                new_record = ProjectMessageRecord(self.env)
                new_record.populate(req)
                try:
                    new_record.insert()
                except:
                    self.log.info("Unable to create record that %s agreed "
                                  " to %s", new_record['agreed_by'], 
                                  new_record['message_name'])
                finally:
                    self.log.debug("Created a new record to show %s agreed "
                                   "to %s", new_record['agreed_by'],
                                   new_record['message_name'])
                data = {'success': True}
                req.send(to_json(data), 'text/json')

    # ITemplateStreamFilter

    def filter_stream(self, req, method, filename, stream, data):
        """
        Check for alert messages to show authenticated user.

        If there are any project messages that the authenticated user has not 
        seen, which are selected to be viewed as alert based notifications, 
        we add the necessary mark-up and javscript.
        """

        if req.authname != 'anonymous':

            timeout_exceeded = self._timeout_limit_exceeded(req)
            if timeout_exceeded or timeout_exceeded is None:

                # we can check for alert notifications
                unagreed = ProjectMessage.get_unagreed_messages(self.env, 
                            req.authname, 'Alert')
                if unagreed:
                    # we only shown one notification at a time currently
                    msg = unagreed[0]
                    msg['message'] = format_to_html(self.env, 
                                        Context.from_request(req), msg['message'])
                    alert_markup = tag(
                                    tag.div(
                                        tag.i(
                                            class_="alert-icon icon-info-sign"
                                        ),
                                        tag.ul(
                                            tag.li(msg['message'],
                                                class_="alert-message"
                                            ),
                                        ),
                                        tag.button(msg['button'],
                                            class_="close btn btn-mini",
                                            type="button",
                                            data_dismiss="alert"
                                        ),
                                        id_=msg['name'],
                                        class_="project-message cf alert alert-info alert-dismissable individual"
                                    ),
                                    tag.form(
                                        tag.input(
                                            name="name",
                                            value=msg['name'],
                                            type="text",
                                        ),
                                        tag.input(
                                            name="agree",
                                            value=True,
                                            type="text",
                                        ),
                                        class_="hidden",
                                        method="post",
                                        action="",
                                    ),
                                  )

                    stream |= Transformer("//*[@id='main']/*[1]").before(alert_markup)
                    add_script(req, 'projectmessage/js/project_message.js')

                # if the timeout has been exceeded or does not exist yet, 
                # and there are no notifications to show, we update the 
                # session attribute table
                if not ProjectMessage.get_unagreed_messages(self.env, req.authname):
                    stamp = str(to_utimestamp(datetime.now(pytz.utc)))
                    req.session['project_message_timeout'] = stamp
                    req.session.save()

        return stream

    # ITemplateProvider methods

    def get_htdocs_dirs(self):
        return [('projectmessage', resource_filename(__name__, 'htdocs'))]

    def get_templates_dirs(self):
        return [resource_filename(__name__, 'templates')]

    # Other class methods

    def _timeout_limit_exceeded(self, req):
        """
        Looks in session table to see if we have exceeded the timeout limit.

        If the timeout limit has been exceeded, we return True. If the 
        timeout_period hasn't been exceeded, we return False. If the 
        timeout_period hasn't been set, we return None.
        """

        timeout = req.session.get('project_message_timeout')
        if timeout:
            if timeout < str(to_utimestamp(datetime.now(pytz.utc))):
                return True
            else:
                return False