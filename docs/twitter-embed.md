# Twitter Embeds
Simple feature that automatically embeds (most) tweets containing media. For tweets that aren't automatically flagged, there's an accompanying message command

> Learn more about message commands with `/about message commands`
+++
## Why some are missed
For whatever reason, twitter appends tweets with videos with `?s=20`. Unfortunately, and inexplicably, tweets that contain more than one photo, and polls also get this little addition. Furthermore, tweets that are replies (like threads) don't get the `?s=20`

+++
## About FixTweet
FixTweet creates an embedded version of the tweet for discord (or Telegram if you're a weirdo). Works with images, videos, and even polls. You can even click on the link, which just redirects you to the actual tweet through your browser/app.

### Fun fact
FixTweet was seemingly authored by a furry. We can depend on this for years to come.