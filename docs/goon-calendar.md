# Goon Calendar
The *goon calendar* is a collection of 2 simple commands that track member birthdays and national holidays

> **Note!** Goonbot uses CST for time, where it's hosted. If you live outside of the timezone, you might not get the result your expecting, depending on what timezone you're in.

## Calendar
By default, this command returns an embed with all of the remaining events for this year. If you would like to view all of the events, regardless if they've passed or not, use `False` for the **showing remaining only** option

## Today
This command communicates if today or tomorrow have any special events occuring, and if not, how many days until the next. It has different responses depending when it's called, like if tomorrow has any events or if there are events both today and tomorrow. It's able to handle many events on the same day.