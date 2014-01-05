BlogFeed
========

Displays news stories from the internet in your system tray. 
Currently HackerNews and Reddit are supported, more might follow.
Inspired by captn3m0's hackertray (https://github.com/captn3m0/hackertray).

Usage
========

Only tested on Ubuntu.
CD into the folder where the files are located, run: python blogfeed.py.

When you click on a story, your default browser will open the corresponding webpage. A check mark is added to the story to easily show the ones you have already read.

Through the settings panel new locations can be added. Subreddits can be added by entering r/yourSubReddit with the amount of stories you want BlogFeed to show (default=3). HackerNews is added by simply adding hackernews with the amount of stories you want displayed.

Features
========
- Added history file to make read stories persistent upon opening and closing the application
- Added Settings Panel to easily add new locations
- Added notifications to display new stories when added

Final Notes
========
This is my first Python project so any tips, suggestions and improvements are more than welcome.
