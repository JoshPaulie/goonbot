# Goonbot Picks
Goonbot Picks is a collection of commands pertaining to random choice.
+++
## Teams
The `teams` command is used to create teams of any size.

You can specify an optional **team size** to determine how big each team should be. If no team size is provided, the players are made into 2 equal sized teams

### How players are selected
Whoever used the command is considered the "caller." Goonbot checks which voice channel the caller is currently in, and add everyone in that channel into a queue.

### How teams are made
The queue of players is then randomly shuffled, and players are grouped into batches of size `N`, where `N` is the specified team size.

In cases where no team size is provided, the team size defaults to half the number of players in the queue. For example, if there are 8 people in the goon HQ channel, the team size is set to 4, resulting in the creation of two balanced teams.

### How odd numbered player queues are handled
In instances where the team size is set to 4, and there are 9 players, the command creates two teams of 4 players each, along with a third team consisting of the remaining single player.
+++
## Pick for me
Simple command that presents a modal for user input. Each line represents a different option from which Goonbot can choose. Goonbot then returns all of the options, and **boldens** its choice
+++
## Dice roller
Simple command that rolls dice for you, and is uses "dnd notation" as input

### NdN notation examples
- **2d20** 👉 roll a 20 sided dice 2 times
- **4d6** 👉 roll a 6 sided dice 4 times