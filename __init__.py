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

from jira import JIRA
import os
import re

__author__ = 'jrwarwick'

# Logger: used for debug lines, like "LOGGER.debug(xyz)". These
# statements will show up in the command line when running Mycroft.
LOGGER = getLogger(__name__)

# The logic of each skill is contained within its own class, which inherits
# base methods from the MycroftSkill class with the syntax you can see below:
# "class ____Skill(MycroftSkill)"
class JIRASkill(MycroftSkill):

    # The constructor of the skill, which calls MycroftSkill's constructor
    def __init__(self):
        super(JIRASkill, self).__init__(name="JIRASkill")

    # This method loads the files needed for the skill's functioning, and
    # creates and registers each intent that the skill uses
    def initialize(self):
        self.load_data_files(dirname(__file__))
        try:
            if self.settings.get("url", "") or \
               self.settings.get("username", "") or \
               self.settings.get("password", ""):
                   self._is_setup = True
            else:
                self.speak_dialog("Please navigate to home.mycroft.ai to establish or complete JIRA Service Desk server access configuration.")
        except Exception as e:
            LOG.error(e)

        #(fallback?)#jira = JIRA(server=os.environ['JIRA_SERVER_URL'],basic_auth=(os.environ['JIRA_USER'],os.environ['JIRA_PASSWORD'])) #  http://bakjira01.int.bry.com:8080/rest/api/2/
        jira = JIRA(server=self.settings.get("url", ""),basic_auth=(self.settings.get("username", ""),self.settings.get("password", "")) #  http://bakjira01.int.bry.com:8080/rest/api/2/


        status_report_intent = IntentBuilder("StatusReportIntent").\
            require("StatusReportKeyword").build()
        self.register_intent(status_report_intent, self.handle_status_report_intent)

        thank_you_intent = IntentBuilder("ThankYouIntent").\
            require("ThankYouKeyword").build()
        self.register_intent(thank_you_intent, self.handle_thank_you_intent)

        how_are_you_intent = IntentBuilder("HowAreYouIntent").\
            require("HowAreYouKeyword").build()
        self.register_intent(how_are_you_intent,
                             self.handle_how_are_you_intent)

        hello_world_intent = IntentBuilder("HelloWorldIntent").\
            require("HelloWorldKeyword").build()
        self.register_intent(hello_world_intent,
                             self.handle_hello_world_intent)

    # The "handle_xxxx_intent" functions define Mycroft's behavior when
    # each of the skill's intents is triggered: in this case, he simply
    # speaks a response. Note that the "speak_dialog" method doesn't
    # actually speak the text it's passed--instead, that text is the filename
    # of a file in the dialog folder, and Mycroft speaks its contents when
    # the method is called.
    def handle_status_report_intent(self, message):
        self.speak_dialog("JIRA Service Desk status report:")
        inquiry = jira.search_issues('assignee is EMPTY AND status != Resolved ORDER BY createdDate DESC')
        if inquiry.total < 1:
            print "No JIRA issues found in the unassigned queue."
        else:
            print str( inquiry.total ) + " issues found in the unassigned queue."
            thissue = jira.issue(inquiry[0].key,fields='summary,comment')
            print "Latest issue is regarding: " + re.sub('([fF][wW]:)+','',thissue.fields.summary)

        inquiry = jira.search_issues('resolution = Unresolved AND priority > Medium ORDER BY priority DESC')
        if inquiry.total < 1:
            print "No HIGH priority JIRA issues remain open."
        else:
            print str( inquiry.total ) + " high priority issue" + ('','s')[inquiry.total > 1] + " remain" + ('s','')[inquiry.total > 1] + " open!"
            thissue = jira.issue(inquiry[0].key,fields='summary,comment')
            print "Highest priority issue is regarding: " + re.sub('([fF][wW]:)+','',thissue.fields.summary)


        #TODO: call python script instead? 

    def handle_thank_you_intent(self, message):
        self.speak_dialog("welcome")

    def handle_how_are_you_intent(self, message):
        self.speak_dialog("how.are.you")

    def handle_hello_world_intent(self, message):
        self.speak_dialog("hello.world")

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
