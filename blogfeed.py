#!/usr/bin/env python

import json
import urllib2
import os
import pygtk
import pynotify

pygtk.require('2.0')
import gtk
import webbrowser
import signal
import appindicator
from time import time


DEBUG = 1
TITLE_LENGTH = 80
REFRESH_INTERVAL = 5 * 60 * 1000  # 5 minutes

CONFIG_FILE = 'feeds.config'
HISTORY_FILE = 'feeds.history'
APP_TITLE = 'BlogFeed'
APP_D = 'blog-feed'
ICON_PATH = 'blogfeed.png'
GITHUB_LINK = 'https://github.com/nov1n/BlogFeed/'
HEADERS = {'User-Agent': 'blogfeed-133'}


def string_rep(iterable):
    """ Prints the String representation for an iterable, used for logging """
    for item in iterable:
        print item


def get_resource_path(rel_path):
    """ Fetches the absolute path from a relative path """
    dir_of_py_file = os.path.dirname(__file__)
    rel_path_to_resource = os.path.join(dir_of_py_file, rel_path)
    abs_path_to_resource = os.path.abspath(rel_path_to_resource)
    return abs_path_to_resource


def show_dialog_ok(text):
    """ Shows a dialog with the supplied message """
    message = gtk.MessageDialog(type=gtk.MESSAGE_INFO, buttons=gtk.BUTTONS_OK)
    message.set_markup(text)
    response = message.run()
    if response == gtk.RESPONSE_OK:
        message.destroy()


def read_config():
    """ Open the config file, if nonexistent create it and return the \
        containing lines """
    try:
        # Creates the file if nonexistent
        conf = open(get_resource_path(CONFIG_FILE), 'a+')
    except IOError as ex:
        print 'Something went wrong reading the configuration file: ' \
            + ex.message
        return()
    lines = conf.readlines()
    if not lines:  # If config file is empty, show a dialog box
        show_dialog_ok(
            'No locations found. Please head to the settings to add them.')
    return lines


def shorten(phrase, length=TITLE_LENGTH):
    """ Shortens the title of a story to the desired length, adds dots for \
        more fancyness """
    if len(phrase) <= length:
        return phrase
    elif phrase[length] == ' ':
        return phrase[:length]
    else:
        index = length
        while not phrase[index] == ' ':
            index -= 1
        return phrase[:index] + '...'  # Add dots to show the string was chopped


def uts_to_time(uts):
    """ Converts Unix Time Stamp to Days and Hours """
    uts = int(uts) / 3600
    days = 0
    hours = 0
    while uts - 24 >= 0:
        days += 1
        uts -= 24 * 3600
    hours += uts
    if days == 1:
        return "1 day ago"
    elif days > 1:
        return str(days) + " days ago"
    elif days <= 0:
        if hours > 1:
            return str(hours) + " hours ago"
        else:
            return "1 hour ago"


def api_call(url):
    """ Send a request to the API server and return the json contents \
        loaded into a Python dictionary """
    req = urllib2.Request(url, None, HEADERS)
    try:
        data = urllib2.urlopen(req)
        return json.load(data)
    except Exception, ex:
        print 'Could not connect to server: %s, %s' % (url, str(ex))


class BlogFeed:

    """ Represents the app indicator filled with stories from various \
        websites """

    def __init__(self):
        # Create an indicator applet
        self.ind = appindicator.Indicator(
            APP_TITLE, APP_D, appindicator.CATEGORY_APPLICATION_STATUS)
        self.ind.set_status(appindicator.STATUS_ACTIVE)
        self.ind.set_icon(get_resource_path(ICON_PATH))

        # Create a menu
        self.menu = gtk.Menu()

        self.separators = []

        # Create items for the menu - refresh, quit and a separator
        menu_separator = gtk.SeparatorMenuItem()
        self.menu.append(menu_separator)

        # Settings button
        btn_settings = gtk.MenuItem('Settings')
        btn_settings.connect('activate', self.show_settings)
        self.menu.append(btn_settings)

        # About button
        btn_about = gtk.MenuItem('About')
        btn_about.connect('activate', self.show_about)
        self.menu.append(btn_about)

        # Refresh button
        btn_refresh = gtk.MenuItem('Refresh')
        # The last parameter is for not running the timer
        btn_refresh.connect('activate', self.refresh, True)
        self.menu.append(btn_refresh)

        # Quit button
        btn_quit = gtk.MenuItem('Quit')
        btn_quit.connect('activate', self.quit)
        self.menu.append(btn_quit)

        self.menu.show_all()

        self.ind.set_menu(self.menu)
        self.refresh()

    @staticmethod
    def show_settings(self, widget=None):
        """ This method shows the settings panel """
        settings = SettingsPanel()
        settings.main()

    @staticmethod
    def show_about(self, widget=None):
        """ Show about info """
        webbrowser.open(GITHUB_LINK)

    @staticmethod
    def quit(self, widget=None):
        """ Handle the quit button """
        gtk.main_quit()

    def run(self):
        """ gtk driver """
        signal.signal(signal.SIGINT, self.quit)
        gtk.main()
        return 0

    def open(self, widget):
        """ Opens the link in the web browser """
        ident = str(hash(widget.item_id))
        if widget.get_active():
            print 'Writing to history file..'
            history = map(str.rstrip, \
                open(get_resource_path(HISTORY_FILE), 'r').readlines())
            if ident in history:  # ident already written to the history file
                print 'Duplicate..'
                return
            history = open(get_resource_path(HISTORY_FILE), 'a+')
            history.write(ident + '\n')  # Write the hashed ident to the file
        # This prevents the check mark from toggling and opening the webpage
        # twice
        else:
            widget.disconnect(widget.signal_id)
            widget.set_active(True)
            widget.signal_id = widget.connect('activate', self.open)
        webbrowser.open(widget.url)

    def add_item(self, item):
        """ Adds an item to the menu """
        i = gtk.CheckMenuItem(
            ' ' + str(item.score).zfill(3) + '\t' + item.title)
        i.set_active(False)
        i.url = item.url
        i.signal_id = i.connect('activate', self.open)
        i.hn_id = item.id
        i.item_id = item.id
        i.title = item.title
        try:
            # Check if history file exists
            with open(get_resource_path(HISTORY_FILE), 'r') as history:
                for line in history.readlines():
                    if str(hash(i.item_id)) == str(line).rstrip():
                        # This prevents the self.open callback from firing when
                        # adding the story
                        i.disconnect(i.signal_id)
                        i.set_active(True)
                        i.signal_id = i.connect('activate', self.open)
        except IOError:
            # Generate the file
            open(get_resource_path(HISTORY_FILE), 'a')
        self.menu.prepend(i)
        i.show()

    def refresh(self, widget=None, no_timer=False):
        """ Refreshes the menu """
        old_stories = {}
        new_stories = {}

        # Remove all the current stories
        for i in self.menu.get_children():
            if hasattr(i, 'url'):  # needed not to remove the menu items
                self.menu.remove(i)
            if hasattr(i, 'item_id'):
                old_stories[i.item_id] = i.title
        self.separators[:] = []  # Remove all the separators

        # Fetch all the stories from the desired websites
        fetcher = Fetcher()
        fetcher.fetch()

        # Iterate over all the stories of all the sites and add them to the
        # menu
        sep = gtk.SeparatorMenuItem()
        for site in fetcher.story_collection.itervalues():
            # Add a title for each site
            # Get the name of the site
            title = gtk.MenuItem('\t\t' + site[0].site)
            title.url = site[0].site  # This causes it to be removed on refresh
            title.show()

            # Add the stories from that site
            for story in reversed(site):
                self.add_item(story)

                # Check for new stories for the notification
                if not story.id in old_stories:
                    new_stories[story.id] = story.title
            sep = gtk.SeparatorMenuItem()
            sep.url = site[0].site  # This causes it to be removed on refresh
            self.separators.append(sep)
            sep.show()
            self.menu.prepend(title)
            self.menu.prepend(sep)
        self.menu.remove(sep)  # Remove the top separator --> unnecessary

        # Generate notification with new stories
        if len(new_stories):
            title = str(len(new_stories)) + ' new stories:'
            status = '\n'.join([shorten(p, length=50)
                               for p in new_stories.values()])

            pynotify.init('BlogFeed')
            pynotify.Notification(title, status).show()

        # Refresh once every refresh interval
        if not no_timer:
            gtk.timeout_add(REFRESH_INTERVAL, self.refresh)


class Story:

    """ Contains information about a story """

    def __init__(self, site='Unknown', title='Unknown', score='Unknown', id='Unknown', date='Unknown', url='Unknown'):
        self.site = site
        self.title = title
        self.score = score
        self.id = id
        self.date = date
        self.url = url

    def __str__(self):
        return 'Site: %s\nTitle: %s\nScore: %s\nID: %s\nDate: %s\nURL: %s\n' % (
            self.site, self.title, self.score, self.id, self.date, self.url)


class SettingsPanel:
    """ Displays the settings panel which allows user to define the locations \
        from which the stories are fetched """

    # This event is called by the window manager when the cross is pressed
    @staticmethod
    def delete_event(self, widget, event, data=None):
        # Change to true if the main window should not be destroyed
        return False

    @staticmethod
    def destroy(self, widget, data=None):
        gtk.main_quit()

    def __init__(self):

        # Create a new window
        self.window = gtk.Window()

        # Link the destroy event to the destroy function
        # This event happens when we return False from the delete_event
        # function
        self.window.connect('destroy', self.destroy, 0)

        # Set title
        self.window.set_title('Settings')

        # Set the border width
        self.window.set_border_width(10)

        # Center the window
        self.window.set_position(gtk.WIN_POS_MOUSE)

        # Set windows size
        self.window.set_size_request(300, 200)

        # Disable resizing
        self.window.set_resizable(False)

        # Create the list to fill the TreeView
        self.feeds_liststore = gtk.ListStore(str, str)

        # Create a TreeView for the feeds
        self.treeview = gtk.TreeView(model=self.feeds_liststore)

        # Put the TreeView in a scrollable container
        self.scrolled_window = gtk.ScrolledWindow()
        self.scrolled_window.add(self.treeview)

        # Create the columns
        columns = ['Location', 'Amount']

        for i in range(len(columns)):
            # Cellrenderer to render the text
            cell = gtk.CellRendererText()
            cell.connect('edited', self.on_cell_edited,
                         (self.feeds_liststore, i))
            cell.set_property('editable', True)
            # The column is created
            col = gtk.TreeViewColumn(columns[i], cell, text=i)
            # And it is appended to the TreeView
            self.treeview.append_column(col)

        # When a row of the treeview is selected, it emits a signal and saves
        # row contents into a variable
        self.selection = self.treeview.get_selection()
        self.selection.set_mode(gtk.SELECTION_MULTIPLE)

        # A button to add new locations, connected to a callback function
        self.button_add = gtk.Button(label="Add")
        self.button_add.connect("clicked", self.add_cb)

        # Two entries for the location and the amount
        self.location_entry = gtk.Entry()
        self.amount_entry = gtk.Entry()

        # A button to remove locations, connected to a callback function
        self.button_remove = gtk.Button(label="Remove")
        self.button_remove.connect("clicked", self.remove_cb)

        # A button to save the changes connected to a callback
        self.button_save = gtk.Button(label="Save")
        self.button_save.connect("clicked", self.save_cb)

        # A button to remove all locations, connected to a callback function
        self.button_remove_all = gtk.Button(label="Remove All")
        self.button_remove_all.connect("clicked", self.remove_all_cb)

        # A grid to attach the widgets
        grid = gtk.Table(8, 10, False)
        grid.set_col_spacing(15, 15)
        grid.attach(self.scrolled_window, 0, 7, 0, 6)
        grid.attach(gtk.HSeparator(), 0, 7, 6, 7)
        grid.attach(self.button_remove, 0, 1, 7, 8)
        grid.attach(self.button_remove_all, 1, 2, 7, 8)
        grid.attach(self.button_save, 3, 4, 7, 8)
        grid.attach(self.button_add, 0, 1, 8, 9)
        grid.attach(self.location_entry, 1, 3, 8, 9)
        grid.attach(self.amount_entry, 3, 4, 8, 9)

        # Normalize
        self.scrolled_window.set_size_request(240, 120)
        self.amount_entry.set_size_request(50, 30)
        self.location_entry.set_size_request(100, 30)
        self.button_remove.set_size_request(70, 30)
        self.button_remove_all.set_size_request(100, 30)
        self.button_add.set_size_request(30, 20)

        self.window.add(grid)

        # Show the window
        self.window.show_all()

    def on_cell_edited(self, cell, path, new_text, user_data):
        """ On edited callback handler """
        self.feeds_liststore, column = user_data
        self.feeds_liststore[path][column] = new_text
        return

    def add_cb(self, widget):
        """ Add button callback handler """
        location = self.location_entry.get_text()
        amount = self.amount_entry.get_text()
        if not location:
            show_dialog_ok('Please enter a location')
            return
        if not amount:
            amount = 3
        self.feeds_liststore.append([location, amount])

    def remove_cb(self, widget):
        """ Remove button callback handler """
        (model, pathlist) = self.selection.get_selected_rows()
        for path in pathlist:
            tree_iter = model.get_iter(path)
            self.feeds_liststore.remove(tree_iter)

    def remove_all_cb(self, widget):
        """ Remove all button callback handler """
        self.feeds_liststore.clear()

    def save_cb(self, widget):
        """ Callback for the save event """
        conf = open(get_resource_path(CONFIG_FILE), 'w')
        for item in self.feeds_liststore:
            conf.write(item[0] + ' ' + item[1] + '\n')
        conf.close()
        show_dialog_ok('Settings saved.')

    def sync_feeds(self):
        """ Fill the TreeView model (liststore) with the data from the \
            config file """
        lines = read_config()
        for line in lines:
            print line.split()
            self.feeds_liststore.append(line.split())

    def main(self):
        """ Fill the listview and display the settings panel """
        # Fill the treeview
        self.sync_feeds()
        # Control ends here, waiting for an event to occur
        gtk.main()


class Fetcher:
    """ Fetches stories from various user-defined websites """
    HN_API = 'http://api.ihackernews.com/page'
    HN_NAME = 'Hacker News'
    REDDIT_API_BASE = 'http://www.reddit.com/r/subr/hot.json'
    REDDIT_NAME = 'Reddit'

    story_collection = {}

    def __init__(self):
        pass

    def fetch_hn(self, amount=3):
        """ Get the top n (3 by default) stories from HackerNews """

        # Make the api call
        json_data = api_call(self.HN_API)
        if not json_data:
            return

        # Create a dict as ID : points
        items = json_data['items']
        points = {}
        for item in items:
            points[item['id']] = item['points']

        # Sort the items by points, pick top n
        most_points = sorted(points, key=points.get, reverse=True)
        top = []
        for index in range(0, amount):
            id = most_points[index]
            for item in items:
                if item['id'] == id:
                    top.append(item)
                    break

        # Return a list of Story objects
        stories = []
        for item in top:
            id = item['id']
            title = item['title']
            title_short = shorten(title)
            score = item['points']
            date = item['postedAgo']
            url = item['url']
            stories.append(
                Story(self.HN_NAME, title_short, score, id, date, url))

        # Add the list of stories to the collection
        self.story_collection[self.HN_NAME] = stories
        if DEBUG:
            print string_rep(stories)

    def fetch_reddit(self, subr, amount=3):
        """ Get the top n (3 by default) stories from Reddit """

        site = self.REDDIT_NAME + '/' + subr
        # Edit according to given subreddit
        subr_api = self.REDDIT_API_BASE.replace('subr', subr)

        # Make the api call
        json_data = api_call(subr_api)
        if not json_data:
            return

        # Create a dict as ID : points
        items = json_data['data']['children']
        points = {}
        for item in items:
            points[item['data']['id']] = item['data']['score']

        # Sort the items by points, pick top n
        most_points = sorted(points, key=points.get, reverse=True)
        top = []
        for index in range(0, amount):
            id = most_points[index]
            for item in items:
                if item['data']['id'] == id:
                    top.append(item)
                    break

        # Return a list of Story objects
        stories = []
        for item in top:
            id = item['data']['id']
            title = item['data']['title']
            title_short = shorten(title)
            score = item['data']['score']
            date = uts_to_time(time() - item['data']['created'])
            url = item['data']['url']
            stories.append(Story(site, title_short, score, id, date, url))

        self.story_collection[site] = stories
        if DEBUG:
            print string_rep(stories)

    def fetch(self):
        """ Fetch the stories from all the locations specified in the \
            configuration file """
        lines = read_config()
        for line in lines:
            tokens = line.strip().split()
            amount = 3
            type = tokens[0]

            if len(tokens) == 2 and tokens[1].isdigit():
                amount = int(tokens[1])

            if type.startswith('r/'):
                self.fetch_reddit(type[2:], amount)
            elif type == 'hackernews':
                self.fetch_hn(amount)
            else:
                print 'Error reading: \'%s\', invalid format.' % line.rstrip()


def main():
    """ Driver boilerplate """
    indicator = BlogFeed()
    indicator.run()

main()
