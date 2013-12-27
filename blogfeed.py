#!/usr/bin/env python

import json
import urllib2
import pygtk
pygtk.require('2.0')
import gtk
import webbrowser
import signal
import appindicator
from time import time

# TODO: Make check marks on the stories persistent upon refreshes

DEBUG = 1
TITLE_LENGTH = 80
CONFIG_FILE = 'feeds.config'
APP_TITLE = 'BlogFeed'
APP_D = 'blog-feed'
ICON_PATH = 'blogfeed.png'
GITHUB_LINK = 'https://github.com/nov1n/BlogFeed/'


def string_rep(iterable):
	""" Prints the String representation for an iterable """
	for x in iterable:
		print x


def read_config():
	try:
		conf = open(CONFIG_FILE, 'a+')  # Creates the file if nonexistent
	except IOError as e:
		print 'Something went wrong reading the configuration file: ' + e.message
		return
	lines = conf.readlines()
	if not lines:  # If config file is empty, show a dialog box
		message = gtk.MessageDialog(type=gtk.MESSAGE_INFO, buttons=gtk.BUTTONS_OK)
		message.set_markup('No websites found. Please head to the settings to add websites.')
		response = message.run()
		if response == gtk.RESPONSE_OK:
			message.destroy()
	return lines


def shorten(phrase):
	if len(phrase) <= TITLE_LENGTH:
		return phrase
	elif phrase[TITLE_LENGTH] == ' ':
		return phrase[:TITLE_LENGTH]
	else:
		n = TITLE_LENGTH
		while not phrase[n] == ' ':
			n -= 1
		return phrase[:n] + '...'  # Add dots to show the string was chopped


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


class BlogFeed:
	""" Represents the app indicator filled with stories from various websites """
	def __init__(self):
		# create an indicator applet
		self.ind = appindicator.Indicator(APP_TITLE, APP_D, appindicator.CATEGORY_APPLICATION_STATUS)
		self.ind.set_status(appindicator.STATUS_ACTIVE)
		self.ind.set_icon(pygtk.os.path.abspath(ICON_PATH))

		# create a menu
		self.menu = gtk.Menu()

		self.separators = []

		# create items for the menu - refresh, quit and a separator
		menu_separator = gtk.SeparatorMenuItem()
		self.menu.append(menu_separator)

		# settings button
		btn_settings = gtk.MenuItem('Settings')
		btn_settings.connect('activate', self.show_settings)
		self.menu.append(btn_settings)

		# about button
		btn_about = gtk.MenuItem('About')
		btn_about.connect('activate', self.show_about)
		self.menu.append(btn_about)

		# refresh button
		btn_refresh = gtk.MenuItem('Refresh')
		btn_refresh.connect('activate', self.refresh, True)  # The last parameter is for not running the timer
		self.menu.append(btn_refresh)

		# quit button
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
	def quit(self, widget=None, data=None):
		""" Handle the quit button """
		gtk.main_quit()

	def run(self):
		signal.signal(signal.SIGINT, self.quit)
		gtk.main()
		return 0

	def open(self, widget):
		""" Opens the link in the web browser """
		if not widget.get_active():
			widget.disconnect(widget.signal_id)
			widget.set_active(True)
			widget.signal_id = widget.connect('activate', self.open)
		webbrowser.open(widget.url)

	def add_item(self, item):
		""" Adds an item to the menu """
		i = gtk.CheckMenuItem(' ' + str(item.score).zfill(3) + '\t' + item.title)
		i.set_active(False)
		i.url = item.url
		i.signal_id = i.connect('activate', self.open)
		i.hn_id = item.id
		i.item_id = item.id
		self.menu.prepend(i)
		i.show()

	def refresh(self, widget=None, no_timer=False):
		""" Refreshes the menu """
		# Remove all the current stories
		for i in self.menu.get_children():
			if hasattr(i, 'url'):  # needed not to remove the menu items
				self.menu.remove(i)
		self.separators[:] = []  # Remove all the separators

		# Fetch all the stories from the desired websites
		fetcher = Fetcher()
		fetcher.fetch()

		# Iterate over all the stories of all the sites and add them to the menu
		sep = gtk.SeparatorMenuItem()
		for site in fetcher.story_collection.itervalues():
			# Add a title for each site
			title = gtk.MenuItem('\t\t' + site[0].site)  # Get the name of the site
			title.url = site[0].site  # This prevents it from being removed on refresh
			title.show()

			# Add the stories from that site
			for story in reversed(site):
				self.add_item(story)
			sep = gtk.SeparatorMenuItem()
			sep.url = site[0].site  # This causes it from being removed on refresh
			self.separators.append(sep)
			sep.show()
			self.menu.prepend(title)
			self.menu.prepend(sep)
		self.menu.remove(sep)  # Remove the top separator --> unnecessary

		# Call every 5 minutes
		if not no_timer:
			gtk.timeout_add(5 * 60 * 1000, self.refresh)


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

	# This event is called by the window manager when the cross is pressed
	@staticmethod
	def delete_event(self, widget, event, data=None):
		return False  # Change to true if the main window should not be destroyed

	@staticmethod
	def destroy(self, widget, data=None):
		gtk.main_quit()

	def __init__(self):
		# Create a new window
		self.window = gtk.Window(gtk.WIN_POS_MOUSE)

		# Link the destroy event to the destroy function
		# This event happens when we return False from the delete_event function
		self.window.connect('destroy', self.destroy)

		# Set title
		self.window.set_title('Settings')

		# Set the border width
		self.window.set_border_width(10)

		# Center the window
		self.window.set_position(gtk.WIN_POS_MOUSE)  # TODO: Fix log error here

		# Set windows size
		self.window.set_size_request(250, 350)

		# Disable resizing
		self.window.set_resizable(False)

		# Create the list to fill the TreeView
		self.feeds_liststore = gtk.ListStore(str, int)
		# Create a TreeView for the feeds
		self.treeview = gtk.TreeView(self.feeds_liststore)
		# Create column for the feed
		self.feed_column = gtk.TreeViewColumn()
		self.feed_column.set_title('Name')
		# Create column for the amount
		self.amount_column = gtk.TreeViewColumn()
		self.amount_column.set_title('Amount')
		# Add the columns to the treeview
		self.treeview.append_column(self.feed_column)
		self.treeview.append_column(self.amount_column)

		# Add the tree to the window
		self.window.add(self.treeview)

		# Show the window
		self.window.show_all()

	def fill_feed(self):
		# TODO: Implement this

		pass

	def main(self):
		# Fill the treeview
		self.fill_feed()
		# Control ends here, waiting for an event to occur
		gtk.main()


class Fetcher:
	""" Fetches stories from various user-defined websites """
	HN_API = 'http://api.ihackernews.com/page'
	HN_NAME = 'Hacker News'
	REDDIT_API_BASE = 'http://www.reddit.com/r/subr/hot.json'
	REDDIT_NAME = 'Reddit'
	HEADERS = {'User-Agent': 'blogfeed-133'}

	story_collection = {}

	def __init__(self):
		pass

	def api_call(self, url):
		req = urllib2.Request(url, None, self.HEADERS)
		try:
			data = urllib2.urlopen(req)
			return json.load(data)
		except Exception, e:
			print 'Could not connect to server: %s, %s' % (url, str(e))

	def fetch_hn(self, amount=3):
		""" Get the top n (3 by default) stories from HackerNews """

		# Make the api call
		json_data = self.api_call(self.HN_API)
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
		for x in range(0, amount):
			id = most_points[x]
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
			stories.append(Story(self.HN_NAME, title_short, score, id, date, url))

		self.story_collection[self.HN_NAME] = stories # Add the list of stories to the collection
		if DEBUG: print string_rep(stories)

	def fetch_reddit(self, subr, amount=3):
		""" Get the top n (3 by default) stories from Reddit """

		site = self.REDDIT_NAME + '/' + subr
		subr_api = self.REDDIT_API_BASE.replace('subr', subr)  # Edit according to given subreddit

		# Make the api call
		json_data = self.api_call(subr_api)
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
		for x in range(0, amount):
			id = most_points[x]
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
		if DEBUG: print string_rep(stories)

	def fetch(self):
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
	indicator = BlogFeed()
	indicator.run()

main()
