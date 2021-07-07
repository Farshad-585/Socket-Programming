# Socket Programming

---
### CITS3002 - Computer Networks
#### The University of Western Australia

---
#### Project goals
This project helped me expand my knowledge of socket programming in python.

---
#### Description
Congratulations! You've been given an internship at one of the larger game developers, Electronic Farce,
who have just launched a new and addictive turn-based strategic tile placing game. The company initially
started developing this game last year, but due to the pandemic, the engineer in charge left the project and
had to focus on maintaining RNG battle royale that was developed back in 2019. EF decided to reboot this
game project by hiring you.

The previous engineer managed to write the client code, but did not provide any documentations. Because
the client is already written, the message format for communication between the server and clients is
already set. You can use the client to test your server as your development progresses. He also wrote a small
sample server written in Python. But this server is deficient in that it only allows a single client to play a
rather pointless game alone. However, you can inspect this server to see how to pass and receive the
predetermined game messages. You can also use the server to see the basic flow of the game.

In a rather spectacular but not altogether surprising fashion, EF have tasked all of the interns (you) to
implement their server in a short period of time. Your task is to write an upgraded server for the strategic
tile placing game. We provide more specific game details below.

---
#### The Game
The game in question is a strategic tile placing game. Each player is given a set of random tiles (from a preset list of tiles) by the server. A tile has two points on each side (north, east, south, and west). Each of these eight points is connected to one of the other points on the tile, so there are four connections in total. Example tiles are shown below.

<img src="https://user-images.githubusercontent.com/61343458/124699659-cbbae180-df1d-11eb-8b5e-0f4ca5086641.png" width="300" height="75">

---
#### The Gameplay
The board is initially empty. One at a time, in an order determined by the server, each player places a single
tile on the board, ensuring that the first tile is connected to the edge of the board.

In the second turn, each player chooses where their token will enter the board. This must be one of the
points on the tile that they placed in the first turn, so there will be either two or four possible locations
(depending on whether or not the tile was placed in a corner).

The player's token automatically follows the connection across the tile, reaching a new square of the board.
If that board already has a tile, the token will follow the connection in the new tile, continuing until it either
reaches an empty square or the edge of the board.

If a player's token reaches the edge of the board, that player is eliminated.

On the third turn, and all subsequent turns, each remaining player may place a single tile from their hand
onto the empty square that their token is entering. Any other players who are entering the same square will
be moved automatically according to the connections on the placed tile, so it is possible for other players to
be eliminated.

If only one player remains alive, that player is considered the winner.

You can find what it looks like as a multiplayer below.

<img src="https://user-images.githubusercontent.com/61343458/124699923-5bf92680-df1e-11eb-9f57-deff83bd8497.png">

---
#### Program Flow/Requirements
  1. A selection of at most four players is chosen from all connected clients.
  2. A random turn order for the four players is also determined.
  3. Each client is notified that a new game is starting.
  4. Each player is provided tiles to fill their starting hand.
  5. While more than one player is alive:
      - Notify all clients whose turn it is
      - Wait for the current player to make a valid move
      - Process the results of the move
          - Notify all clients of new tile placements
          - Notify all clients of new token positions
          - Notify all clients of any eliminated players
          - If there are less than two players remaining, exit the loop
  6. If the current player played a tile, send them a new tile
  7. Switch to the next (remaining) player's turn

When a game is completed, the server should start a new game if there are enough clients available.
Otherwise it should wait for more clients to join.

---
### Exceptions in gameplay
Note that much of the game logic about legal tile placements, etc., was already handled for us in tiles.py module. Our server, needed to ensure that players behave correctly. for example:
  - Players should only be allowed to play tiles that are currently in their hand.
  - If a player sends a message when it is not their turn, it should be ignored.
  - Players should only be able to choose a token position on their second turn (i.e. when they don't already
have a token on the board).

---
### How to start game
Run the server.py file, then run the client.py file. You can run multiple clients.

---
NOTE: THIS PROJECT WAS PART OF THE COMPUTER NETWORKS (CITS3002) UNIT AT THE UNIVERSITY OF WESTERN AUSTRALIA. SOME OF THE CODE AND LOGIC WAS PROVIDED BY THE UNIT COORDINATORS.
