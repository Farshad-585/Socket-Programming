# Written by Farshad Ghanbari (21334883)
# Tested on Windows 10 only

import socket
import sys
import threading
from tkinter.constants import X
import tiles
import random
import time
import queue
from tiles import BOARD_HEIGHT


class Server:
    COUNT_DOWN = 2          # Count down for a new game
    WAIT_CONNECTIONS = 1    # Server checks for connection to start game
    WAIT_PLAYERS = 1        # If connection, server waits for few more players
    WAIT_MOVE = 10          # Wait time for server to place a tile instead

    def __init__(self, host, port):
        self.sock = None
        self.host = host
        self.port = port
        self.board = tiles.Board()
        self.idnum_counter = -1
        self.connections = []       # Stores all connected clients
        self.players = []           # Stores players currently in game
        self.live_idnums = []       # Stores idnumber of the players in game
        self.eliminated = []        # Stores the eliminated players
        self.tiles_placed = []      # Keeps track of all tile placements
        self.position_updates = []  # keeps track of position updates
        self.game_running = False   # True if a game is currently running
        self.curr_player = None     # Stores the current player turn
        self.turn_queue = queue.Queue(tiles.PLAYER_LIMIT)   # Player turn queue

    # Checks if a selected token position is valid
    # Copied from tiles.py. Used when the server is doing the move.
    def valid_token_move(self, x, y, position):
        if (position == 0 or position == 1) and y != BOARD_HEIGHT - 1:
            return False
        if (position == 2 or position == 3) and x != BOARD_HEIGHT - 1:
            return False
        if (position == 4 or position == 5) and y != 0:
            return False
        if (position == 6 or position == 7) and x != 0:
            return False
        return True

    # Selects the x, y position of first tile
    # It is called again if x, y position returned is already taken
    # Used when the server is doing the move
    def first_tile_xy(self):
        x = random.randint(0, 4)
        y = 0
        if x == 0 or x == 4:
            y = random.randint(0, 4)
        else:
            y = random.choice([0, 4])
        return (x, y)

    # If player does not make a move, server will do the movement
    # Function returns a 'chunk' of data similar to what clients send
    def do_player_move(self, player):
        # first move for each player, Placing a tile
        if player["turn"] == 1:
            # Other players first moves are added to this list
            # So that a selected x, y position does not overlap
            tiles_on_board = []
            for p in self.players:
                if p["start_pos"] == None:
                    continue
                tiles_on_board.append(p["start_pos"])
            (x, y) = self.first_tile_xy()
            while (x, y) in tiles_on_board:
                (x, y) = self.first_tile_xy()

            tileid = random.choice(player["hand"])
            rotation = random.randint(0, 3)
            player["start_pos"] = (x, y)

            chunk = tiles.MessagePlaceTile(
                player["idnum"], tileid, rotation, x, y).pack()
            return chunk
        # Second move for each player, token position
        elif player["turn"] == 2:
            idnum = player["idnum"]
            x = player["start_pos"][0]
            y = player["start_pos"][1]

            # Keeps looking for a valid token position
            position = random.randint(0, 7)
            while not self.valid_token_move(x, y, position):
                position = random.randint(0, 7)

            chunk = tiles.MessageMoveToken(idnum, x, y, position).pack()
            return chunk
        else:
            # Subsequent moves for each player
            x, y, position = self.board.get_player_position(player["idnum"])

            tileid = random.choice(player["hand"])
            rotation = random.randint(0, 3)

            chunk = tiles.MessagePlaceTile(
                player["idnum"], tileid, rotation, x, y).pack()
            return chunk

    # Processes client disconection
    def disconnect_client(self, client):
        print('client {} disconnected'.format(client["addr"]))
        if client in self.players:
            self.connections.remove(client)
            idnum = client["idnum"]
            self.eliminate_player([idnum])
            self.broadcast(tiles.MessagePlayerLeft(idnum).pack())
        # If player not currently in a game
        else:
            self.connections.remove(client)
            self.broadcast(tiles.MessagePlayerLeft(client["idnum"]).pack())

    # For each player in the eliminated list given, player is eliminated
    def eliminate_player(self, eliminated):
        for idnum in eliminated:
            # Additional for loop because I store players as well as live_idnums
            for player in self.players:
                if player["idnum"] == idnum:
                    self.players.remove(player)
                    self.eliminated.append(player)
            self.live_idnums.remove(idnum)
            self.broadcast(tiles.MessagePlayerEliminated(idnum).pack())

    # Called from handle_game() function when it gets the next player turn from
    # the queue. It calls handle_player() and passes the current player turn to it.
    # Handles most of the game logic for the player.
    def handle_player(self, player):
        buffer = bytearray()
        conn = player["conn"]
        idnum = player["idnum"]

        conn.settimeout(self.WAIT_MOVE)
        try:
            chunk = conn.recv(4096)
            # If player doesn't make a move, server will do the move instead.
        except:
            print(f"Player [{idnum}] timedout.")
            print("Server will do player's move.")
            chunk = self.do_player_move(player)

        # Disconnected player is processed
        if not chunk:
            self.disconnect_client(player)
            return

        buffer.extend(chunk)
        while True:
            msg, consumed = tiles.read_message_from_bytearray(buffer)
            if not consumed:
                break

            buffer = buffer[consumed:]
            print('received message {}'.format(msg))

            # sent by the player to put a tile onto the board
            #  (in all turns except their second)
            if isinstance(msg, tiles.MessagePlaceTile):
                if self.board.set_tile(
                        msg.x, msg.y, msg.tileid, msg.rotation, msg.idnum):

                    # Notify client that placement was successful
                    # In this implementation I decided not to run client threads,
                    # Simultaneously. So, the only way I can detect if a client is
                    # disconnected is when there is an exception error when server
                    # is trying to send a message to each client. That is when,
                    # server detects a client has been disconnected. A disconnected
                    # client is also detected when its their turn through 'not chunk'.
                    # broadcast() returns the disconnected player.
                    dc = self.broadcast(msg.pack())
                    if dc == player:
                        return

                    # Server stores each players start position. It was needed
                    # so that when server is doing the first move automatically,
                    # it does not place a tile over another players' tile.
                    if player["start_pos"] == None:
                        player["start_pos"] = (msg.x, msg.y)

                    # check for token movement
                    positionupdates, eliminated = self.board.do_player_movement(
                        self.live_idnums)

                    for message in positionupdates:
                        dc = self.broadcast(message.pack())
                        if dc == player:
                            return
                        # Keeping track of position updates
                        self.position_updates.append(message.pack())

                    if idnum in eliminated:
                        self.eliminate_player(eliminated)
                        return

                    # Keeping track of tile placements
                    self.tiles_placed.append(msg.pack())
                    # Remove the tile used from hand
                    player["hand"].remove(msg.tileid)
                    # Pick up a new tile
                    tileid = tiles.get_random_tileid()
                    player["hand"].append(tileid)
                    conn.send(tiles.MessageAddTileToHand(tileid).pack())

                # If player sends an invalid chunk, function is recursively called
                # again. Not the best implementation, but it works.
                else:
                    print(
                        f"Inavlid tile placement. Player[{idnum}] must try again.")
                    self.handle_player(player)
                    return

            # sent by the player in the second turn, to choose their token's
            # starting path
            elif isinstance(msg, tiles.MessageMoveToken):
                if not self.board.have_player_position(msg.idnum):
                    if self.board.set_player_start_position(
                            msg.idnum, msg.x, msg.y, msg.position):
                        # check for token movement
                        positionupdates, eliminated = self.board.do_player_movement(
                            self.live_idnums)

                        for message in positionupdates:
                            dc = self.broadcast(message.pack())
                            if dc == player:
                                break
                            # Keeping track of position updates
                            self.position_updates.append(message.pack())

                        if idnum in eliminated:
                            self.eliminate_player(eliminated)
                            return

            # Incrementing player specific hand turn
            player["turn"] += 1

    # Servers' main game loop. Called from start_game() function.
    # Gives each selected player random tiles.
    # Constantly get the next player from the queue.
    def handle_game(self):
        # Adding tiles to hand for each player
        for player in self.players:
            for _ in range(tiles.HAND_SIZE):
                tileid = tiles.get_random_tileid()
                # Keeping track of each player's hand
                player["hand"].append(tileid)
                player["conn"].send(tiles.MessageAddTileToHand(tileid).pack())

        # Game runs until there is only 1 player left.
        while True:
            self.curr_player = self.turn_queue.get()
            idnum = self.curr_player["idnum"]
            # If the player received from the queue has been previously disconnected,
            # or eliminated, it is ignored, so we get the next in queue.
            while idnum not in self.live_idnums:
                self.curr_player = self.turn_queue.get()
                idnum = self.curr_player["idnum"]

            self.broadcast(tiles.MessagePlayerTurn(idnum).pack())
            self.handle_player(self.curr_player)

            # After handle_player() returns, the current player might have been
            # eliminated. So we should not put it back into the queue.
            if self.curr_player not in self.eliminated:
                self.turn_queue.put(self.curr_player)

            # Game is over in the below cases.
            if len(self.live_idnums) == 1 or len(self.live_idnums) == 0:
                break

        # Start the next game.
        self.start_game()

    # Selects players for a new round of game
    def select_players(self):
        # Wait few more seconds if there aren't 4 clients connected
        if len(self.connections) < tiles.PLAYER_LIMIT:
            # waiting for more connections
            print(f"Waiting {self.WAIT_PLAYERS} sec for more players")
            time.sleep(self.WAIT_PLAYERS)

        # If still less than 4 connections, start game anyway with random turn
        if len(self.connections) < tiles.PLAYER_LIMIT:
            self.players = random.sample(
                self.connections, len(self.connections))
        else:
            # If 4 or more clients, select 4 at random
            self.players = random.sample(self.connections, tiles.PLAYER_LIMIT)

        # Each selected player is added to turn queue and live_idnums
        for player in self.players:
            self.turn_queue.put(player)
            self.live_idnums.append(player["idnum"])
            # Reseting from previous round
            player["turn"] = 1
            player["hand"] = []
            player["start_port"] = None

    # Start a new round of game
    def start_game(self):
        while True:
            if self.connections:
                # reset everything from previous game
                self.board.reset()
                self.players = []
                self.live_idnums = []
                self.eliminated = []
                self.tiles_placed = []
                self.position_updates = []
                self.curr_idnum = None
                self.turn_queue = queue.Queue(tiles.PLAYER_LIMIT)

                self.broadcast(tiles.MessageCountdown().pack())
                print(f"New game will start in {self.COUNT_DOWN} seconds...")
                time.sleep(self.COUNT_DOWN)

                # Select players at random
                self.select_players()
                self.broadcast(tiles.MessageGameStart().pack())
                print("Game starts.")
                self.game_running = True

                # handle the main game loop
                self.handle_game()
                break

            print("waiting for connections...")
            time.sleep(self.WAIT_CONNECTIONS)

    # Sends a message to all connected clients
    def broadcast(self, message):
        for client in self.connections:
            try:
                client["conn"].send(message)
            except:
                # if unsuccessfull, client has been disconnected
                self.disconnect_client(client)
                return client

    # Updates the new connection with the status of the runnning game
    def update_spectator(self, new_client):
        conn = new_client["conn"]
        # Previous connections are introduced to the new client
        for client in self.connections:
            conn.send(tiles.MessagePlayerJoined
                      (client["name"], client["idnum"]).pack())
        # The new client is updated with player turns, eliminated players,
        # tile placements and token movements
        if self.game_running:
            for idnum in self.live_idnums:
                conn.send(tiles.MessagePlayerTurn(idnum).pack())
            for loser in self.eliminated:
                conn.send(tiles.MessagePlayerEliminated(loser["idnum"]).pack())
            conn.send(tiles.MessagePlayerTurn(
                self.curr_player["idnum"]).pack())
            for tile in self.tiles_placed:
                conn.send(tile)
            for update in self.position_updates:
                conn.send(update)

    # hande client welcoming and updating them with the status of running game
    def handle_client(self, client):
        name = client["name"]
        conn = client["conn"]
        idnum = client["idnum"]

        conn.send(tiles.MessageWelcome(idnum).pack())
        # The new client is introduced to previous connections
        self.broadcast(tiles.MessagePlayerJoined(name, idnum).pack())
        # Updates the new client with the status of the running game
        self.update_spectator(client)
        self.connections.append(client)

    # Accepts all incoming connections
    def handle_connections(self):
        while True:
            conn, addr = self.sock.accept()
            # Sets a new idnum for the client
            self.idnum_counter = (self.idnum_counter + 1) % tiles.IDNUM_LIMIT
            print('received connection from {}'.format(addr))
            host, port = addr
            name = '{}:{}'.format(host, port)

            # Each client is a dictionary
            new_client = {
                "name": name,
                "conn": conn,
                "addr": addr,
                "idnum": self.idnum_counter,
                "turn": 1,
                "hand": [],
                "start_pos": None
            }
            handle_client = threading.Thread(
                target=self.handle_client, args=(new_client, ), daemon=True)
            handle_client.start()

    # Starts the server socket. Creats a thread that constantly listens
    # for new connections
    def start_server(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((self.host, self.port))
        self.sock.listen()
        print('listening on {} ...'.format(self.sock.getsockname()))

        # handle_connections constantly accepts new connections
        handle_conns = threading.Thread(target=self.handle_connections)
        handle_conns.start()

        # Server starts handling the game
        self.start_game()


# ------------------ #
# START OF EXECUTION #
# -------------------#
server = Server('', 30020)
server.start_server()
