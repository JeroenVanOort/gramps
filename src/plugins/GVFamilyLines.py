#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2007  Stephane Charette
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Pubilc License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#

# $Id$

"""
Family Lines, a GraphViz-based plugin for Gramps.
"""

#------------------------------------------------------------------------
#
# python modules
#
#------------------------------------------------------------------------
import os
import time
from gettext import gettext as _

#------------------------------------------------------------------------
#
# Set up logging
#
#------------------------------------------------------------------------
import logging
log = logging.getLogger(".FamilyLines")

#------------------------------------------------------------------------
#
# GNOME/gtk
#
#------------------------------------------------------------------------
import gtk
import gobject

#------------------------------------------------------------------------
#
# GRAMPS module
#
#------------------------------------------------------------------------
import gen.lib
import Config
import Errors
import Utils
import ThumbNails
import DateHandler
import GrampsWidgets
import ManagedWindow
from PluginUtils import register_report
from ReportBase import Report, ReportUtils, ReportOptions, CATEGORY_CODE, MODE_GUI, MODE_CLI
from ReportBase import Report, MenuReportOptions, MODE_GUI, MODE_CLI, CATEGORY_GRAPHVIZ
from ReportBase._ReportDialog import ReportDialog
from PluginUtils import register_report, FilterListOption, EnumeratedListOption, BooleanOption, NumberOption, ColourButtonOption, PeoplePickerOption
from QuestionDialog import ErrorDialog, WarningDialog

#from NameDisplay import displayer as _nd       # Gramps version <  3.0
from BasicUtils import name_displayer as _nd    # Gramps version >= 3.0

from DateHandler import displayer as _dd
from DateHandler import parser
from Selectors import selector_factory

#------------------------------------------------------------------------
#
# A quick overview of the classes we'll be using:
#
#   class FamilyLinesOptions(MenuReportOptions)
#       - this class is created when the report dialog comes up
#       - all configuration controls for the report are created here
#       - see src/ReportBase/_ReportOptions.py for more information
#
#   class FamilyLinesReport(Report)
#       - this class is created only after the user clicks on "OK"
#       - the actual report generation is done by this class
#       - see src/ReportBase/_Report.py for more information
#
# Likely to be of additional interest is register_report() at the
# very bottom of this file.
#
#------------------------------------------------------------------------


class FamilyLinesOptions(MenuReportOptions):
    """
    Defines all of the controls necessary
    to configure the FamilyLines reports.
    """
    def __init__(self, name, person_id=None):
        MenuReportOptions.__init__(self, name, person_id)

    def add_menu_options(self, menu):

        # --------------------------------
        category = _('People of Interest')
        # --------------------------------

        peoplePicker = PeoplePickerOption(  _('People of interest'), '', None)  # todo, fixme: need access to the database (3rd parm)
        peoplePicker.set_help(              _('People of interest are used as a starting point when determining \"family lines\".'))
        menu.add_option(category, 'FLgidlist', peoplePicker)

        followParents = BooleanOption(      _('Follow parents to determine family lines'), True)
        followParents.set_help(             _('Parents and their ancestors will be considered when determining "family lines".'))
        menu.add_option(category, 'FLfollowParents', followParents)

        followChildren = BooleanOption(     _('Follow children to determine family lines'), True)
        followChildren.set_help(            _('Children will be considered when determining "family lines".'))
        menu.add_option(category, 'FLfollowChildren', followChildren)

        removeExtraPeople = BooleanOption(  _('Try to remove extra people and families'), True)
        removeExtraPeople.set_help(         _('People and families not directly related to people of interest will be removed when determining "family lines".'))
        menu.add_option(category, 'FLremoveExtraPeople', removeExtraPeople)

        # ----------------------------
        category = _('Family Colours')
        # ----------------------------

        # todo, family colours

        # -------------------------
        category = _('Individuals')
        # -------------------------

        colourMales = ColourButtonOption(   _('Males'), '#e0e0ff')
        colourMales.set_help(               _('The colour to use to display men.'))
        menu.add_option(category, 'FLcolourMales', colourMales)

        colourFemales = ColourButtonOption( _('Females'), '#ffe0e0')
        colourFemales.set_help(             _('The colour to use to display women.'))
        menu.add_option(category, 'FLcolourFemales', colourFemales)

        colourUnknown = ColourButtonOption( _('Unknown'), '#e0e0e0')
        colourUnknown.set_help(             _('The colour to use when the gender is unknown.'))
        menu.add_option(category, 'FLcolourUnknown', colourUnknown)

        colourFamily = ColourButtonOption(  _('Families'), '#ffffe0')
        colourFamily.set_help(              _('The colour to use to display families.'))
        menu.add_option(category, 'FLcolourFamilies', colourFamily)

        limitParents = BooleanOption(       _('Limit the number of parents'), False)
        limitParents.set_help(              _('The maximum number of ancestors to include.'))
        menu.add_option(category, 'FLlimitParents', limitParents)

        maxParents = NumberOption(          '', 50, 10, 9999)
        maxParents.set_help(                _('The maximum number of ancestors to include.'))
        menu.add_option(category, 'FLmaxParents', maxParents)

        limitChildren = BooleanOption(      _('Limit the number of children'), False)
        limitChildren.set_help(             _('The maximum number of children to include.'))
        menu.add_option(category, 'FLlimitChildren', limitChildren)

        maxChildren = NumberOption(          '', 50, 10, 9999)
        maxChildren.set_help(               _('The maximum number of children to include.'))
        menu.add_option(category, 'FLmaxChildren', maxChildren)

        # --------------------
        category = _('Images')
        # --------------------

        includeImages = BooleanOption(      _('Include thumbnail images of people'), True)
        includeImages.set_help(             _('The maximum number of children to include.'))
        menu.add_option(category, 'FLincludeImages', includeImages)

        imageLocation = EnumeratedListOption(_('Thumbnail location'), 0)
        imageLocation.add_item(0,          _('Above the name'))
        imageLocation.add_item(1,          _('Beside the name'))
        imageLocation.set_help(            _('Where the thumbnail image should appear relative to the name'))
        menu.add_option(category, 'FLimageOnTheSide', imageLocation)

        # ---------------------
        category = _('Options')
        # ---------------------

        includeDates = BooleanOption(       _('Include dates'), True)
        includeDates.set_help(              _('Whether to include dates for people and families.'))
        menu.add_option(category, 'FLincludeDates', includeDates)

        includePlaces = BooleanOption(      _('Include places'), True)
        includePlaces.set_help(             _('Whether to include placenames for people and families.'))
        menu.add_option(category, 'FLincludePlaces', includePlaces)

        includeNumChildren = BooleanOption( _('Include the number of children'), True)
        includeNumChildren.set_help(        _('Whether to include the number of children for families with more than 1 child.'))
        menu.add_option(category, 'FLincludeNumChildren', includeNumChildren)

        includeResearcher = BooleanOption(  _('Include researcher and date'), True)
        includeResearcher.set_help(         _('Whether to include at the bottom the researcher''s name, e-mail, and the date the report was generated.'))
        menu.add_option(category, 'FLincludeResearcher', includeResearcher)

        includePrivate = BooleanOption(     _('Include private records'), False)
        includePrivate.set_help(            _('Whether to include names, dates, and families that are marked as private.'))
        menu.add_option(category, 'FLincludePrivate', includePrivate)


#------------------------------------------------------------------------
#
# FamilyLinesReport -- created once the user presses 'OK'
#
#------------------------------------------------------------------------
class FamilyLinesReport(Report):
    def __init__(self, database, person, options):
        """
        Creates FamilyLinesReport object that eventually produces the report.
        
        The arguments are:

        database    - the GRAMPS database instance
        person      - currently selected person
        options     - instance of the FamilyLinesOptions class for this report
        """

        # initialize several convenient variables
        self.options            = options
        self.db                 = database
        self.peopleToOutput     = set() # handle of people we need in the report
        self.familiesToOutput   = set() # handle of families we need in the report
        self.deletedPeople      = 0
        self.deletedFamilies    = 0

        # inherited from parent; see "usesubgraphs" in _GraphvizReportDialog.py
        self.useSubgraphs       = options.handler.options_dict['usesubgraphs'           ]   

        # the remainder of the options are specific to this report
        self.followParents      = options.handler.options_dict['FLfollowParents'        ]
        self.followChildren     = options.handler.options_dict['FLfollowChildren'       ]
        self.removeExtraPeople  = options.handler.options_dict['FLremoveExtraPeople'    ]
        self.gidlist            = options.handler.options_dict['FLgidlist'              ]
        self.colourMales        = options.handler.options_dict['FLcolourMales'          ]
        self.colourFemales      = options.handler.options_dict['FLcolourFemales'        ]
        self.colourUnknown      = options.handler.options_dict['FLcolourUnknown'        ]
        self.colourFamilies     = options.handler.options_dict['FLcolourFamilies'       ]
        self.limitParents       = options.handler.options_dict['FLlimitParents'         ]
        self.maxParents         = options.handler.options_dict['FLmaxParents'           ]
        self.limitChildren      = options.handler.options_dict['FLlimitChildren'        ]
        self.maxChildren        = options.handler.options_dict['FLmaxChildren'          ]
        self.includeImages      = options.handler.options_dict['FLincludeImages'        ]
        self.imageOnTheSide     = options.handler.options_dict['FLimageOnTheSide'       ]
        self.includeDates       = options.handler.options_dict['FLincludeDates'         ] 
        self.includePlaces      = options.handler.options_dict['FLincludePlaces'        ]
        self.includeNumChildren = options.handler.options_dict['FLincludeNumChildren'   ]
        self.includeResearcher  = options.handler.options_dict['FLincludeResearcher'    ]
        self.includePrivate     = options.handler.options_dict['FLincludePrivate'       ]

        # the gidlist is annoying for us to use since we always have to convert
        # the GIDs to either Person or to handles, so we may as well convert the
        # entire list right now and not have to deal with it ever again
        self.interestSet = set()
        for gid in self.gidlist.split():
            person = self.db.get_person_from_gramps_id(gid)
            self.interestSet.add(person.get_handle())

        # convert the 'surnameColours' string to a dictionary of names and colours
        self.surnameColours = {}
        tmp = '' # TODO, FIXME options.handler.options_dict['FLsurnameColours'].split()
        while len(tmp) > 1:
            surname = tmp.pop(0).encode('iso-8859-1','xmlcharrefreplace')
            colour = tmp.pop(0)
            self.surnameColours[surname] = colour


    def begin_report(self):
        # inherited method; called by report() in _ReportDialog.py
        #
        # this is where we'll do all of the work of figuring out who
        # from the database is going to be output into the report

        self.progress = Utils.ProgressMeter(_('Generate family lines'),_('Starting'))

        # starting with the people of interest, we then add parents:
        self.peopleToOutput.clear()
        self.familiesToOutput.clear()
        self.progress.set_pass(_('Finding ancestors and children'), self.db.get_number_of_people())
        if self.followParents:
            self.findParents()

            if self.removeExtraPeople:
                self.removeUninterestingParents()

        # ...and/or with the people of interest we add their children:
        if self.followChildren:
            self.findChildren()
        # once we get here we have a full list of people
        # and families that we need to generate a report


    def write_report(self):
        # inherited method; called by report() in _ReportDialog.py

        # since we know the exact number of people and families,
        # we can then restart the progress bar with the exact
        # number
        self.progress.set_pass(_('Writing family lines'),
            len(self.peopleToOutput     ) + # every person needs to be written
            len(self.familiesToOutput   ) + # every family needs to be written
            len(self.familiesToOutput   ))  # every family needs people assigned to it

        # now that begin_report() has done the work, output what we've
        # obtained into whatever file or format the user expects to use
        self.writePeople()
        self.writeFamilies()
        self.progress.close()


    def findParents(self):
        # we need to start with all of our "people of interest"
        ancestorsNotYetProcessed = set(self.interestSet)

        # now we find all the immediate ancestors of our people of interest

        while len(ancestorsNotYetProcessed) > 0:
            handle = ancestorsNotYetProcessed.pop()
            self.progress.step()

            # One of 2 things can happen here:
            #   1) we've already know about this person and he/she is already in our list
            #   2) this is someone new, and we need to remember him/her
            #
            # In the first case, there isn't anything else to do, so we simply go back
            # to the top and pop the next person off the list.
            #
            # In the second case, we need to add this person to our list, and then go
            # through all of the parents this person has to find more people of interest.

            if handle not in self.peopleToOutput:

                person = self.db.get_person_from_handle(handle)

                # if this is a private record, and we're not
                # including private records, then go back to the
                # top of the while loop to get the next person
                if person.private and not self.includePrivate:
                    continue

                # remember this person!
                self.peopleToOutput.add(handle)

                # see if a family exists between this person and someone else
                # we have on our list of people we're going to output -- if
                # there is a family, then remember it for when it comes time
                # to link spouses together
                for familyHandle in person.get_family_handle_list():
                    family = self.db.get_family_from_handle(familyHandle)
                    spouseHandle = ReportUtils.find_spouse(person, family)
                    if spouseHandle:
                        if spouseHandle in self.peopleToOutput or spouseHandle in ancestorsNotYetProcessed:
                            self.familiesToOutput.add(familyHandle)

                # if we have a limit on the number of people, and we've
                # reached that limit, then don't attempt to find any
                # more ancestors
                if self.limitParents and (self.maxParents < (len(ancestorsNotYetProcessed) + len(self.peopleToOutput))):
                    # get back to the top of the while loop so we can finish
                    # processing the people queued up in the "not yet processed" list
                    continue

                # queue the parents of the person we're processing
                for familyHandle in person.get_parent_family_handle_list():
                    family = self.db.get_family_from_handle(familyHandle)

                    if (family.private and self.includePrivate) or not family.private:

                        father = self.db.get_person_from_handle(family.get_father_handle())
                        mother = self.db.get_person_from_handle(family.get_mother_handle())
                        if father:
                            if (father.private and self.includePrivate) or not father.private:
                                ancestorsNotYetProcessed.add(family.get_father_handle())
                                self.familiesToOutput.add(familyHandle)
                        if mother:
                            if (mother.private and self.includePrivate) or not mother.private:
                                ancestorsNotYetProcessed.add(family.get_mother_handle())
                                self.familiesToOutput.add(familyHandle)


    def removeUninterestingParents(self):
        # start with all the people we've already identified
        parentsNotYetProcessed = set(self.peopleToOutput)

        while len(parentsNotYetProcessed) > 0:
            handle = parentsNotYetProcessed.pop()
            self.progress.step()
            person = self.db.get_person_from_handle(handle)

            # There are a few things we're going to need,
            # so look it all up right now; such as:
            # - who is the child?
            # - how many children?
            # - parents?
            # - spouse?
            # - is a person of interest?
            # - spouse of a person of interest?
            # - same surname as a person of interest?
            # - spouse has the same surname as a person of interest?

            childHandle = None
            numberOfChildren = 0
            spouseHandle = None
            numberOfSpouse = 0
            fatherHandle = None
            motherHandle = None
            spouseFatherHandle = None
            spouseMotherHandle = None
            spouseSurname = ""
            surname = person.get_primary_name().get_surname().encode('iso-8859-1','xmlcharrefreplace')

            # first we get the person's father and mother
            for familyHandle in person.get_parent_family_handle_list():
                family = self.db.get_family_from_handle(familyHandle)
                handle = family.get_father_handle()
                if handle in self.peopleToOutput:
                    fatherHandle = handle
                handle = family.get_mother_handle()
                if handle in self.peopleToOutput:
                    motherHandle = handle

            # now see how many spouses this person has
            for familyHandle in person.get_family_handle_list():
                family = self.db.get_family_from_handle(familyHandle)
                handle = ReportUtils.find_spouse(person, family)
                if handle in self.peopleToOutput:
                    numberOfSpouse += 1
                    spouse = self.db.get_person_from_handle(handle)
                    spouseHandle = handle
                    spouseSurname = spouse.get_primary_name().get_surname().encode('iso-8859-1','xmlcharrefreplace')

                    # see if the spouse has parents
                    if spouseFatherHandle == None and spouseMotherHandle == None:
                        for familyHandle in spouse.get_parent_family_handle_list():
                            family = self.db.get_family_from_handle(familyHandle)
                            handle = family.get_father_handle()
                            if handle in self.peopleToOutput:
                                spouseFatherHandle = handle
                            handle = family.get_mother_handle()
                            if handle in self.peopleToOutput:
                                spouseMotherHandle = handle

            # get the number of children that we think might be interesting
            for familyHandle in person.get_family_handle_list():
                family = self.db.get_family_from_handle(familyHandle)
                for childRef in family.get_child_ref_list():
                    if childRef.ref in self.peopleToOutput:
                        numberOfChildren += 1
                        childHandle = childRef.ref

            # we now have everything we need -- start looking for reasons
            # why this is a person we need to keep in our list, and loop
            # back to the top as soon as a reason is discovered

            # if this person has many children of interest, then we
            # automatically keep this person
            if numberOfChildren > 1:
                continue

            # if this person has many spouses of interest, then we
            # automatically keep this person
            if numberOfSpouse > 1:
                continue

            # if this person has parents, then we automatically keep
            # this person
            if fatherHandle != None or motherHandle != None:
                continue

            # if the spouse has parents, then we automatically keep
            # this person
            if spouseFatherHandle != None or spouseMotherHandle != None:
                continue;

            # if this is a person of interest, then we automatically keep
            if person.get_handle() in self.interestSet:
                continue;

            # if the spouse is a person of interest, then we keep
            if spouseHandle in self.interestSet:
                continue

            # if the surname (or the spouse's surname) matches a person
            # of interest, then we automatically keep this person
            bKeepThisPerson = False
            for personOfInterestHandle in self.interestSet:
                personOfInterest = self.db.get_person_from_handle(personOfInterestHandle)
                surnameOfInterest = personOfInterest.get_primary_name().get_surname().encode('iso-8859-1','xmlcharrefreplace')
                if surnameOfInterest == surname or surnameOfInterest == spouseSurname:
                    bKeepThisPerson = True
                    break

            if bKeepThisPerson:
                continue

            # if we have a special colour to use for this person,
            # then we automatically keep this person
            if surname in self.surnameColours:
                continue

            # if we have a special colour to use for the spouse,
            # then we automatically keep this person
            if spouseSurname in self.surnameColours:
                continue

            # took us a while, but if we get here, then we can remove this person
            self.deletedPeople += 1
            self.peopleToOutput.remove(person.get_handle())

            # we can also remove any families to which this person belonged
            for familyHandle in person.get_family_handle_list():
                if familyHandle in self.familiesToOutput:
                    self.deletedFamilies += 1
                    self.familiesToOutput.remove(familyHandle)

            # if we have a spouse, then ensure we queue up the spouse
            if spouseHandle:
                if spouseHandle not in parentsNotYetProcessed:
                    parentsNotYetProcessed.add(spouseHandle)

            # if we have a child, then ensure we queue up the child
            if childHandle:
                if childHandle not in parentsNotYetProcessed:
                    parentsNotYetProcessed.add(childHandle)


    def findChildren(self):
        # we need to start with all of our "people of interest"
        childrenNotYetProcessed = set(self.interestSet)
        childrenToInclude = set()

        # now we find all the children of our people of interest

        while len(childrenNotYetProcessed) > 0:
            handle = childrenNotYetProcessed.pop()
            self.progress.step()

            if handle not in childrenToInclude:

                person = self.db.get_person_from_handle(handle)

                # if this is a private record, and we're not
                # including private records, then go back to the
                # top of the while loop to get the next person
                if person.private and not self.includePrivate:
                    continue

                # remember this person!
                childrenToInclude.add(handle)

                # if we have a limit on the number of people, and we've
                # reached that limit, then don't attempt to find any
                # more children
                if self.limitChildren and (self.maxChildren < ( len(childrenNotYetProcessed) + len(childrenToInclude))):
                    # get back to the top of the while loop so we can finish
                    # processing the people queued up in the "not yet processed" list
                    continue

                # iterate through this person's families
                for familyHandle in person.get_family_handle_list():
                    family = self.db.get_family_from_handle(familyHandle)
                    if (family.private and self.includePrivate) or not family.private:

                        # queue up any children from this person's family
                        for childRef in family.get_child_ref_list():
                            child = self.db.get_person_from_handle(childRef.ref)
                            if (child.private and self.includePrivate) or not child.private:
                                childrenNotYetProcessed.add(child.get_handle())
                                self.familiesToOutput.add(familyHandle)

                        # include the spouse from this person's family
                        spouseHandle = ReportUtils.find_spouse(person, family)
                        if spouseHandle:
                            spouse = self.db.get_person_from_handle(spouseHandle)
                            if (spouse.private and self.includePrivate) or not spouse.private:
                                childrenToInclude.add(spouseHandle)
                                self.familiesToOutput.add(familyHandle)

        # we now merge our temp set "childrenToInclude" into our master set
        self.peopleToOutput.update(childrenToInclude)


    def writePeople(self):
        # if we're going to attempt to include images, then use the HTML style of .dot file
        bUseHtmlOutput = False
        if self.includeImages:
            bUseHtmlOutput = True

        # loop through all the people we need to output
        for handle in self.peopleToOutput:
            self.progress.step()
            person = self.db.get_person_from_handle(handle)
            name = person.get_primary_name().get_regular_name()

            # figure out what colour to use
            colour = self.colourUnknown
            if person.get_gender() ==  gen.lib.Person.MALE:
                colour = self.colourMales
            if person.get_gender() ==  gen.lib.Person.FEMALE:
                colour = self.colourFemales

            # see if we have surname colours that match this person
            surname = person.get_primary_name().get_surname().encode('iso-8859-1','xmlcharrefreplace')
            if surname in self.surnameColours:
                colour = self.surnameColours[surname]

            # see if we have a birth date we can use
            birthStr = None
            if self.includeDates and person.get_birth_ref():
                event = self.db.get_event_from_handle(person.get_birth_ref().ref)
                if (event.private and self.includePrivate) or not event.private:
                    date = event.get_date_object()
                    if date.get_day_valid() and date.get_month_valid() and date.get_year_valid():
                        birthStr = _dd.display(date)
                    elif date.get_year_valid():
                        birthStr = '%d' % date.get_year()

            # see if we have a birth place (one of:  city, state, or country) we can use
            birthplace = None
            if self.includePlaces and person.get_birth_ref():
                event = self.db.get_event_from_handle(person.get_birth_ref().ref)
                if (event.private and self.includePrivate) or not event.private:
                    place = self.db.get_place_from_handle(event.get_place_handle())
                    if place:
                        location = place.get_main_location()
                        if location.get_city:
                            birthplace = location.get_city()
                        elif location.get_state:
                            birthplace = location.get_state()
                        elif location.get_country:
                            birthplace = location.get_country()

            # see if we have a deceased date we can use
            deathStr = None
            if self.includeDates and person.get_death_ref():
                event = self.db.get_event_from_handle(person.get_death_ref().ref)
                if (event.private and self.includePrivate) or not event.private:
                    date = event.get_date_object()
                    if date.get_day_valid() and date.get_month_valid() and date.get_year_valid():
                        deathStr = _dd.display(date)
                    elif date.get_year_valid():
                        deathStr = '%d' % date.get_year()

            # see if we have a place of death (one of:  city, state, or country) we can use
            deathplace = None
            if self.includePlaces and person.get_death_ref():
                event = self.db.get_event_from_handle(person.get_death_ref().ref)
                if (event.private and self.includePrivate) or not event.private:
                    place = self.db.get_place_from_handle(event.get_place_handle())
                    if place:
                        location = place.get_main_location()
                        if location.get_city:
                            deathplace = location.get_city()
                        elif location.get_state:
                            deathplace = location.get_state()
                        elif location.get_country:
                            deathplace = location.get_country()

            # see if we have an image to use for this person
            imagePath = None
            if self.includeImages:
                mediaList = person.get_media_list()
                if len(mediaList) > 0:
                    mediaHandle = mediaList[0].get_reference_handle()
                    media = self.db.get_object_from_handle(mediaHandle)
                    mediaMimeType = media.get_mime_type()
                    if mediaMimeType[0:5] == "image":
                        imagePath = ThumbNails.get_thumbnail_path(media.get_path())

            # put the label together and ouput this person
            label = u""
            lineDelimiter = '\\n'
            if bUseHtmlOutput:
                lineDelimiter = '<BR/>'

            # if we have an image, then start an HTML table; remember to close the table afterwards!
            if imagePath:
                label = u'<TABLE BORDER="0" CELLSPACING="2" CELLPADDING="0" CELLBORDER="0"><TR><TD><IMG SRC="%s"/></TD>'  % imagePath
                if self.imageOnTheSide == 0:
                    label += u'</TR><TR>'
                label += '<TD>'

            # at the very least, the label must have the person's name
            label += name

            if birthStr or deathStr:
                label += ' %s(' % lineDelimiter
                if birthStr:
                    label += '%s' % birthStr
                label += ' - '
                if deathStr:
                    label += '%s' % deathStr
                label += ')'
            if birthplace or deathplace:
                if birthplace == deathplace:
                    deathplace = None    # no need to print the same name twice
                label += ' %s' % lineDelimiter
                if birthplace:
                    label += '%s' % birthplace
                if birthplace and deathplace:
                    label += ' / '
                if deathplace:
                    label += '%s' % deathplace

            # see if we have a table that needs to be terminated
            if imagePath:
                label += '</TD></TR></TABLE>'

            if bUseHtmlOutput:
                label = '<%s>' % label
            else:
                label = '"%s"' % label
            self.write('  %s [shape="box", fillcolor="%s", label=%s];\n' % (person.get_gramps_id(), colour, label))


    def writeFamilies(self):
        # loop through all the families we need to output
        for familyHandle in self.familiesToOutput:
            self.progress.step()
            family = self.db.get_family_from_handle(familyHandle)
            fgid = family.get_gramps_id()

            # figure out a wedding date or placename we can use
            weddingDate = None
            weddingPlace = None
            if self.includeDates or self.includePlaces:
                for event_ref in family.get_event_ref_list():
                    event = self.db.get_event_from_handle(event_ref.ref)
                    if event.get_type() == gen.lib.EventType.MARRIAGE:
                        # get the wedding date
                        if (event.private and self.includePrivate) or not event.private:
                            if self.includeDates:
                                date = event.get_date_object()
                                if date.get_day_valid() and date.get_month_valid() and date.get_year_valid():
                                    weddingDate = _dd.display(date)
                                elif date.get_year_valid():
                                    weddingDate = '%d' % date.get_year()
                            # get the wedding location
                            if self.includePlaces:
                                place = self.db.get_place_from_handle(event.get_place_handle())
                                if place:
                                    location = place.get_main_location()
                                    if location.get_city:
                                        weddingPlace = location.get_city()
                                    elif location.get_state:
                                        weddingPlace = location.get_state()
                                    elif location.get_country:
                                        weddingPlace = location.get_country()
                        break

            # figure out the number of children (if any)
            childrenStr = None
            if self.includeNumChildren:
                numberOfChildren = len(family.get_child_ref_list())
#                if numberOfChildren == 1:
#                    childrenStr = _('1 child')
                if numberOfChildren > 1:
                    childrenStr = _('%d children') % numberOfChildren

            label = ''
            if weddingDate:
                if label != '':
                    label += '\\n'
                label += '%s' % weddingDate
            if weddingPlace:
                if label != '':
                    label += '\\n'
                label += '%s' % weddingPlace
            if childrenStr:
                if label != '':
                    label += '\\n'
                label += '%s' % childrenStr
            self.write('  %s [shape="ellipse", fillcolor="%s", label="%s"];\n' % (fgid, self.colourFamilies, label))

        # now that we have the families written, go ahead and link the parents and children to the families
        for familyHandle in self.familiesToOutput:
            self.progress.step()
            self.write('\n')

            # get the parents for this family
            family = self.db.get_family_from_handle(familyHandle)
            fgid = family.get_gramps_id()
            fatherHandle = family.get_father_handle()
            motherHandle = family.get_mother_handle()

            if self.useSubgraphs and fatherHandle and motherHandle:
                self.write('  subgraph cluster_%s\n' % fgid)
                self.write('  {\n')

            # see if we have a father to link to this family
            if fatherHandle:
                if fatherHandle in self.peopleToOutput:
                    father = self.db.get_person_from_handle(fatherHandle)
                    self.write('  %s -> %s // father: %s\n' % (fgid, father.get_gramps_id(), father.get_primary_name().get_regular_name()))

            # see if we have a mother to link to this family
            if motherHandle:
                if motherHandle in self.peopleToOutput:
                    mother = self.db.get_person_from_handle(motherHandle)
                    self.write('  %s -> %s // mother: %s\n' % (fgid, mother.get_gramps_id(), mother.get_primary_name().get_regular_name()))

            if self.useSubgraphs and fatherHandle and motherHandle:
                self.write('  }\n')

            # link the children to the family
            for childRef in family.get_child_ref_list():
                if childRef.ref in self.peopleToOutput:
                    child = self.db.get_person_from_handle(childRef.ref)
                    self.write('  %s -> %s // child:  %s\n' % (child.get_gramps_id(), fgid, child.get_primary_name().get_regular_name()))


#------------------------------------------------------------------------
#
# register_report() is defined in _PluginMgr.py and
# is used to hook the plugin into GRAMPS so that it
# appears in the "Reports" menu options
#
#------------------------------------------------------------------------
register_report(
    name            = 'familylines_graph',
    category        = CATEGORY_GRAPHVIZ,
    report_class    = FamilyLinesReport,    # must implement write_report(), called by report() in _ReportDialog.py
    options_class   = FamilyLinesOptions,   # must implement add_menu_options(), called by MenuOptions::__init__()
    modes           = MODE_GUI,
    status          = _("Stable"),
    translated_name = _("Family Lines Graph"),
    author_name     = "Stephane Charette",
    author_email    = "stephanecharette@gmail.com",
    description     =_("Generates family line graphs using GraphViz."),
    )

