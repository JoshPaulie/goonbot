# Creator Watch
Many of our favorite content creators can be quickly linked to with `/creator <creator name>`.

If they post content to both Twitch and Youtube, a message appears containing 2 buttons, one for each platform. Users can use either to trigger one of the following responses. If they only post content to one or the other, the buttons are skipped and one of the following responses is provided.

## Twitch
Returns a rich embed that changes depending on if they are currently live. If they are live, stream details like title, game, tags, and others are returned. If they aren't live, their "offline profile pic" is used but a link is still provided to watch previous VODs.

## Youtube
Returns a link to a given creator's latest Youtube, uses the default embedding discord provides.