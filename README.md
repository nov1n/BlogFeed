BlogFeed
========

Displays news stories from the internet in your system tray. 
Currently HackerNews and Reddit are supported, more might follow.
Inspired by captn3m0's hackertray (https://github.com/captn3m0/hackertray).

Usage
========

CD into the folder where the files are located, run: python blogfeed.py.

You can customize the stories being displayed by editing the fetch calls starting at line 134.
Example: Adding fetcher.fetch_reddit('cats') displays the top 3 stories of the 'cats' subreddit in your tray.

To change the amount of stories displayed for each website add the optional amount parameter to the fetch calls.
Example: fetcher.fetch_reddit('TodayILearned', amount=10), displays the top 10 stories from the TodayILearned subreddit.


