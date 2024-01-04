# Goonbot Picks
Goonbot Picks is a collection of commands pertaining to random choice.
+++
## Teams
The `teams` command is used to create teams of any size.

By default, players will be split into 2 equal sized teams. You can choose to specify a **team size** to determine how big each team will be.

### How players are selected
Whoever used the command is considered the "organizer." Goonbot checks which voice channel the organizer is in, and add everyone in that channel into a queue.

### How teams are made
The queue of players is randomly shuffled, and players are grouped into batches of size `N`, where `N` is the specified team size.

In cases where no team size is provided, the team size defaults to half the number of players in the queue. For example, if there are 8 people in the goon HQ channel, the team size will be set to 4, resulting in the creation of two balanced teams.

### How remaining players are handled
After the teams are made, there may be left over players. They're added to a team that is smaller than the others. This a byproduct of how the players are grouped together, but it may be used a "bench" for players that didn't get picked this go around.

In instances where the team size is set to 4, and there are 9 players, Goonbot creates two teams of 4 players ..along with a third team consisting of the remaining single player.
+++
## Pick for me
Simple command that presents a modal for user input. Each line represents a different option from which Goonbot can choose. Goonbot then returns all of the options, and **boldens** its choice
+++
## Dice roller
Simple command that rolls dice for you, and is uses "dnd notation" as input

### NdN notation examples
- **2d20** 👉 roll a 20 sided dice 2 times
- **4d6** 👉 roll a 6 sided dice 4 times