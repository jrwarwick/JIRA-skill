# Copyright 2018 Justin Warwick and Mycroft AI, Inc.
#
# This file is an extension to Mycroft Core.
#
# Mycroft Core is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Mycroft Core is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Mycroft Core.  If not, see <http://www.gnu.org/licenses/>.


# Visit https://docs.mycroft.ai/skill.creation for more detailed information
# on the structure of this skill and its containing folder, as well as
# instructions for designing your own skill based on this template.


# Import statements: the list of outside modules you'll be using in your
# skills, whether from other files in mycroft-core or from external libraries
from os.path import dirname

from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill
from mycroft.util.log import getLogger
import mycroft.audio
import mycroft.util

from jira import JIRA
import os
import re
import time
import datetime
import dateutil.parser

__author__ = 'jrwarwick'

# Logger: used for debug lines, like "LOGGER.debug(xyz)". These
# statements will show up in the command line when running Mycroft.
LOGGER = getLogger(__name__)

# The logic of each skill is contained within its own class, which inherits
# base methods from the MycroftSkill class with the syntax you can see below:
# "class ____Skill(MycroftSkill)"


class JIRASkill(MycroftSkill):
    # Constants from the core IP skill
    SEC_PER_LETTER = 0.65  # timing based on Mark 1 screen
    LETTERS_PER_SCREEN = 9.0
    # Special Constants discoverd from Atlassian product documentation
    # omit leading slash, but include trailing slash
    JIRA_REST_API_PATH = 'rest/api/2/'

    # The constructor of the skill, which calls MycroftSkill's constructor
    def __init__(self):
        super(JIRASkill, self).__init__(name="JIRASkill")
        self.jira = None
        self.project_key = None

    # Establish basic login via jira package interface (RESTful API)
    # RETURN the connection object.
    def server_login(self):
        new_jira_connection = None
        try:
            # TODO: revisit this. null/none/"" ?
            if self.settings.get("url", "") or \
                self.settings.get("username", "") or \
                self.settings.get("password", ""):
                    self._is_setup = True
            else:
                # There appears to be a planned, but so far only stub for this
                # get_intro_message(self)   in docs. So, TODO-one-day?
                self.speak("Please navigate to home.mycroft.ai to establish or "
                           "complete JIRA Service Desk server access configuration.")
        except Exception as e:
            LOGGER.error(e)
        try:
            # Would a config fallback be appropriate?
            #   jira = JIRA(server=os.environ['JIRA_SERVER_URL'],
            #      basic_auth=(os.environ['JIRA_USER'],os.environ['JIRA_PASSWORD']))
            #  http://bakjira01.int.bry.com:8080/rest/api/2/
            #  Is there some kind of magical or clever way to 
            # discover the current available API revision? 
            # Maybe let user know if we are not using it?
            server_url = self.settings.get("url", "").strip()
            if (server_url[0:7].lower() != 'http://' and
                server_url[0:8].lower() != 'https://'):
                self.speak("It seems that you have specified an invalid server "
                           "URL. A valid server URL must include the h t t p "
                           "colon slash slash prefix.")
                self.speak("Please navigate to home.mycroft.ai "
                           "to amend or update the JIRA Service Desk "
                           "server access configuration.")
                raise ValueError('server_url contained invalid URL, missing '
                                 'correct prefix: {server_url}'
                                 .format(server_url=repr(server_url)))
            if server_url[-11:] == self.JIRA_REST_API_PATH:
                self.speak("It seems that you have included the rest api 2 "
                           "path in the server URL. This should work fine. "
                           "However, if the API is upgraded, you may need to "
                           "update my record of the endpoint URL.")
                self.speak("Please navigate to home.mycroft.ai "
                           "to amend or update the JIRA Service Desk "
                           "server access configuration.")
            else:
                if server_url[-1:] != '/':
                    server_url = server_url + '/'
                server_url = server_url + self.JIRA_REST_API_PATH

            new_jira_connection = JIRA(server=self.settings.get("url", ""),
                                       basic_auth=(self.settings.get("username", ""),
                                                   self.settings.get("password", ""))
                                      )
        except Exception as e:
            LOGGER.error('JIRA Server connection failure!')
            LOGGER.error(e)

        return new_jira_connection

    # Determine project key (prefix to issue IDs)
    # RETURN string which is project key
    def get_jira_project(self):
            # Probably a bit sloppy to just take the first project from a list
            # but this skill is oriented around a single-project Servie Desk
            # only type install. Caveat Emptor or something.
            # LOGGER.debug("--SELF reveal: " + str(type(self)) + " | " +
            #             str(id(self)) + "  |  " + str(self.__dict__.keys()) )
            return self.jira.projects()[0].key

    # TODO: a helper function to collect together clean-ups for summary line
    # i.e., since people are sometimes careless and lazy with
    # email subject lines and sending an email in to an automated handler
    # is a common way of raising JIRA issues, we see lots of cruft in the
    # summary lines such as FW: and RE:
    # just have a single standard, flexible inline-string-cleaner. 
    # but be careful not to have false positives like:
    #    Require: diagrams and software
    # re.sub('([fF][wW]:)+', '', blocker.fields.summary))
    # re.sub('(^\s*)[rR][eE]:', '', blocker.fields.summary))


    # Accept a datetime (or parsable string representation of same) as "then"
    # to compare with an evaluated now.
    # RETURN string which is a speakable, natural clause of form "X days ago"
    def descriptive_past(self, then):
        # is this "overloading" method pythonic? and/or "GoodProgramming(R)TM"?
        if isinstance(then, basestring):
            then = dateutil.parser.parse(then)
        if then.tzinfo is None:
            then = datetime.datetime(then.year, then.month, then.day, tzinfo=tzlocal())
        ago = datetime.datetime.now(then.tzinfo) - then
        cronproximate = ''
        # TODO: handle negatives, or rather when then is in the future.
        if ago.days == 0:
            # TODO: a bit about crossing day boundaries if 22 hours etc ago
            cronproximate = 'today.'
            # TODO: a bit with less than 60 minutes (3600 sec) is VERY RECENT subcase
            # TODO: add a "just minutes ago" subsubcase
            # TODO: add a "late last night" subcase
        else:
            cronproximate = str(ago.days) + ' days ago.'
        return cronproximate

    # This method loads the files needed for the skill's functioning, and
    # creates and registers each intent that the skill uses
    def initialize(self):
        self.load_data_files(dirname(__file__))

        status_report_intent = IntentBuilder("StatusReportIntent").\
            require("StatusReportKeyword").build()
        self.register_intent(status_report_intent,
                             self.handle_status_report_intent)

        issues_open_intent = IntentBuilder("IssuesOpenIntent").\
            require("IssueRecordsKeyword").require("OpenKeyword").build()
        self.register_intent(issues_open_intent,
                             self.handle_issues_open_intent)

        issues_overdue_intent = IntentBuilder("IssuesOverdueIntent").\
            require("IssueRecordsKeyword").require("OverdueKeyword").build()
        self.register_intent(issues_overdue_intent,
                             self.handle_issues_overdue_intent)

        issue_status_intent = IntentBuilder("IssueStatusIntent").\
            require("IssueStatusKeyword").build()
        self.register_intent(issue_status_intent,
                             self.handle_issue_status_intent)

        raise_issue_intent = IntentBuilder("RaiseIssueIntent").\
            require("RaiseKeyword").require("IssueRecordKeyword").\
            build()
        self.register_intent(raise_issue_intent,
                             self.handle_raise_issue_intent)

        contact_info_intent = IntentBuilder("ContactInfoIntent").\
            require("ContactKeyword").require("ServiceDeskStaffKeyword").\
            build()
        self.register_intent(contact_info_intent,
                             self.handle_contact_info_intent)

        self.jira = self.server_login()
        self.project_key = self.get_jira_project()
        LOGGER.info("JIRA project key set to '" + self.project_key + "'.")


    # The "handle_xxxx_intent" functions define Mycroft's behavior when
    # each of the skill's intents is triggered: in this case, he simply
    # speaks a response. Note that the "speak_dialog" method doesn't
    # actually speak the text it's passed--instead, that text is the filename
    # of a file in the dialog folder, and Mycroft speaks its contents when
    # the method is called.
    def handle_status_report_intent(self, message):
        if self.jira is None:
            LOGGER.info('____' + str(type(self)) + ' :: ' + str(id(self)))
            self.jira = self.server_login()
        else:
            LOGGER.info('JIRA Server login appears to have succeded already.')

        self.speak("JIRA Service Desk status report:")
        inquiry = self.jira.search_issues('assignee is EMPTY AND '
                                          'status != Resolved '
                                          'ORDER BY createdDate DESC')
        if inquiry.total < 1:
            self.speak("No JIRA issues found in the unassigned queue.")
        else:
            self.speak(str(inquiry.total) + " issue" + ('', 's')[inquiry.total > 1] +
                       " found in the unassigned queue.")
            thissue = self.jira.issue(inquiry[0].key, fields='summary,comment')
            self.speak("Latest issue is regarding: " +
                       re.sub('([fF][wW]:)+', '', thissue.fields.summary))

        inquiry = self.jira.search_issues('status != Resolved AND '
                                          'duedate < now() '
                                          'ORDER BY duedate')
        if inquiry.total < 1:
            self.speak("No overdue issues.")
        else:
            self.speak(str(inquiry.total) + " issue" + ('', 's')[inquiry.total > 1] +
                       " overdue!")
            thissue = self.jira.issue(inquiry[0].key, fields='summary,comment')
            self.speak("Most overdue issue is regarding: " +
                       re.sub('([fF][wW]:)+', '', thissue.fields.summary))

        inquiry = self.jira.search_issues('resolution = Unresolved '
                                          'AND priority > Medium '
                                          'ORDER BY priority DESC')
        if inquiry.total < 1:
            self.speak("No HIGH priority JIRA issues remain open.")
        else:
            self.speak(str(inquiry.total) + " high priority "
                       issue" + ('', 's')[inquiry.total > 1] +
                       " remain" + ('s', '')[inquiry.total > 1] + " open!")
            thissue = self.jira.issue(inquiry[0].key, fields='summary,comment')
            self.speak("Highest priority issue is regarding: " +
                       re.sub('([fF][wW]:)+', '', thissue.fields.summary))
        # TODO: SLAs breached or nearly so, if you have that sort of thing.


    def handle_issues_open_intent(self, message):
        if self.jira is None:
            LOGGER.info('____' + str(type(self)) + ' :: ' + str(id(self)))
            self.jira = self.server_login()
        else:
            LOGGER.info('JIRA Server login appears to have succeded already.')

        inquiry = self.jira.search_issues('status != Resolved '
                                          'ORDER BY priority DESC, duedate ASC')
        if inquiry.total < 1:
            self.speak("No unresolved issues.")
        else:
            self.speak(str(inquiry.total) + " issue" + ('', 's')[inquiry.total > 1] +
                       " remain unresolved.")
            thissue = self.jira.issue(inquiry[0].key, fields='summary,comment')
            self.speak("Highest priority unresolved issue is regarding: " +
                       re.sub('([fF][wW]:)+', '', thissue.fields.summary))

    def handle_issues_overdue_intent(self, message):
        if self.jira is None:
            LOGGER.info('____' + str(type(self)) + ' :: ' + str(id(self)))
            self.jira = self.server_login()
        else:
            LOGGER.info('JIRA Server login appears to have succeded already.')

        inquiry = self.jira.search_issues('status != Resolved AND '
                                          'duedate < now() '
                                          'ORDER BY duedate')
        if inquiry.total < 1:
            self.speak("No overdue issues.")
        else:
            self.speak(str(inquiry.total) + " issue" + ('', 's')[inquiry.total > 1] +
                       " overdue!")
            thissue = self.jira.issue(inquiry[0].key, fields='summary,comment')
            self.speak("Most overdue issue is regarding: " +
                       re.sub('([fF][wW]:)+', '', thissue.fields.summary))

    # TODO: def handle_how_many_open_high_priority_issues(self, message):
    # TODO: def handle_how_many_vip_issues(self, message):
    # TODO: def handle_most_urgent_issue(self, message):

    def handle_issue_status_intent(self, message):
        # TODO: flexibly, and somewhat reliably  detect if user
        # uttered the project name abbrev. prefix and just deal with it.

        # issue_id = re.sub(r'\s+', '', self.get_response('specify.issue'))

        def issue_id_validator(utterance):
            # Confesion: "20 characters" is an arbitrary max in this re
            return re.match(r'^[\s0-9]{1,20}$', utterance)

        def valid_issue_id_desc(utterance):
            return ('A valid issue I D is an integer number.'
                    ' No prefix, if you please.'
                    ' I will prefix the issue I D with a predetermined'
                    ' JIRA project name abbreviation.'
                    ' Let us try again.')

        issue_id = self.get_response(dialog='specify.issue',
                                     validator=issue_id_validator,
                                     on_fail=valid_issue_id_desc, num_retries=3 )
        issue_id = re.sub(r'\s+', '', issue_id)
        LOGGER.info('Attempted issue_id understanding:  "' + issue_id + '"')
        # TODO if this issue has/had a blocking issue: then examine that issue
        #   for recent resolution. If so, then mention it, and then
        #   offer to "tickle/remind/refresh" this issue
        if isinstance(int(issue_id), int):
            self.speak("Searching for issue " +
                       self.project_key + '-' + str(issue_id))
            try:
                issue = self.jira.issue(self.project_key + '-' + str(issue_id))
                self.speak(re.sub('([fF][wW]:)+', '', issue.fields.summary))
                if issue.fields.resolution is None:
                    self.speak(" is not yet resolved.")
                    if issue.fields.duedate is not None:
                        then = dateutil.parser.parse(issue.fields.duedate)
                        if then.tzinfo is None:
                            then = datetime.datetime(then.year, then.month, then.day, tzinfo=tzlocal())
                        ago = datetime.datetime.now(then.tzinfo) - then
                        cronproximate = ''
                        if ago.days < 0:
                            if ago.days > -3:
                                self.speak("This issue is due very soon.")
                        elif ago.days == 0:
                            self.speak("This issue is due today!")
                        elif ago.days > 0:
                            cronproximate = str(ago.days) + ' days.'
                            self.speak("This issue is overdue by " + cronproximate)
                    if issue.fields.updated is None:
                        self.speak('No recorded progress on this issue, yet.')
                    else:
                        cronproximate = self.descriptive_past(issue.fields.updated)
                        self.speak('Record last updated ' + cronproximate)
                    self.speak('Issue is at ' + issue.fields.priority.name +
                               ' priority.')
                    if issue.fields.assignee is None:
                        self.speak('And the issue has not yet been assigned '
                                   'to a staff person.')
                    # linked/related issues check. At least 'duplicates' and
                    # "blocks" although there is a little start here, making
                    # the bad assumption of only one link. a lot TODO here.
                    if (len(issue.fields.issuelinks) and
                        issue.fields.issuelinks[0].type.name.lower() == 'blocks'):
                        blocker = issue.fields.issuelinks[0].inwardIssue
                        if blocker.fields.status.name.lower() != 'resolved':
                            #TODO: consider dialog file for this one
                            self.speak('Also note taht this issue is currently '
                                       'blocked by outstanding issue ' +
                                       blocker.key + ' ' +
                                       re.sub('([fF][wW]:)+', '', blocker.fields.summary))
                else:
                    self.speak("This issue is already resolved. ")
                    self.speak(issue.fields.resolution.description)
                    # TODO: "about" should be conditional, descript-past  might be "Today"
                    self.speak(" about " + self.descriptive_past(issue.fields.resolutiondate))
                    # TODO: yield a trimmed version of resolutiondate,perhaps January 21st
                    # in in same year, "January 21st, 2018" if outside of current year.
                    self.speak(" on " + issue.fields.resolutiondate)
            except Exception as e:
                self.speak("Search for further details on the issue record "
                           "failed. Sorry.")
                LOGGER.error('JIRA issue API error!')
                LOGGER.error(e)
        else:
            self.speak('I am afraid that is not a valid issue id number '
                       'or perhaps I misunderstood.')

    def handle_raise_issue_intent(self, message):
        # TODO: pull from settings, but also have some kind of fallback, else.
        self.speak('Unfortunately, I do not yet have the ability to file ' +
                   'an issue record by myself.')
        telephone_number = self.settings.get("support_telephone", "")
        # TODO check and fallback on telephone number

        email_address = ' '.join(list(self.settings.get("support_email", "")))
        email_address = email_address.replace('.', 'dot')
        # TODO: once the core pronounce_email method is available,
        # replace this naive spell-out approach
        data = {'telephone_number': telephone_number,
                'email_address': email_address}
        self.speak_dialog("human.contact.info", data)

        self.enclosure.deactivate_mouth_events()
        self.enclosure.mouth_text(telephone_number)
        time.sleep((self.LETTERS_PER_SCREEN + len(telephone_number)) *
                   self.SEC_PER_LETTER)
        mycroft.audio.wait_while_speaking()
        self.enclosure.activate_mouth_events()
        self.enclosure.mouth_reset()

        # Establish requestor identity
        # Get brief general description
        # Get priority
        # Make a quick search through open
        # (and perhaps very recently closed) issues,
        #    is this a duplicate issue?
        # Create Issue, read out ticket key/ID (also print it out,
        # if printer attached;
        #    also IM tech staff, if high priority)

    def handle_contact_info_intent(self, message):
        telephone_number = self.settings.get("support_telephone", "")
        # TODO check and fallback on telephone number
        data = {'telephone_number': telephone_number,
                'email_address': self.settings.get("support_email", "")}
        self.speak_dialog("human.contact.info", data)

        self.enclosure.deactivate_mouth_events()
        self.enclosure.mouth_text(telephone_number)
        time.sleep((self.LETTERS_PER_SCREEN + len(telephone_number)) *
                   self.SEC_PER_LETTER)
        mycroft.audio.wait_while_speaking()
        self.enclosure.activate_mouth_events()
        self.enclosure.mouth_reset()

    # The "stop" method defines what Mycroft does when told to stop during
    # the skill's execution. In this case, since the skill's functionality
    # is extremely simple, the method just contains the keyword "pass", which
    # does nothing.
    def stop(self):
        pass


# The "create_skill()" method is used to create an instance of the skill.
# Note that it's outside the class itself.
def create_skill():
    return JIRASkill()
