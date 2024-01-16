# Hosting
Goonbot is hosted on a Raspberry Pi Model 4. The Pi has a systemd service enabled that is responsible for
- starting the bot when the Pi boots up
- restarting the bot
  - after a crash
  - after an outage
  - after restarting the bot
- pulling changes and updating the bot before starting the bot
+++
## Changing Hosts
If goonbot ever needs a different host, I've included a bootstrapping script that installs the needed version of Python and copies the service file.

Over engineered? Yes. Will it ever be used? Probably not. Am I proud of it? Yup 😎