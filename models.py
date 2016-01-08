"""
module models provides classes and enums useful for representing a catan game.

The main class is Game, which contains Players, a Board, and a CatanLog.

See module boardbuilder for the mechanics of creating and modifying Board objects.

All classes in this module:
- Game
- Player
- Board
- Tile
- Terrain
- HexNumber
- Port
- Piece
- PieceType
"""
import copy
import logging
import commands
import hexgrid
import states
import catanlog
from enum import Enum
import undo


class Game(object):
    """
    class Game represents a single game of catan. It has players, a board, and a log.

    A Game has observers. Observers register themselves by adding themselves to
    the Game's observers set. When the Game changes, it will notify all its observers,
    who can then poll the game state and make changes accordingly.

    e.g. self.game.observers.add(self)

    A Game has state. When changing state, remember to pass the current game to the
    state's constructor. This allows the state to modify the game as appropriate in
    the current state.

    e.g. self.set_state(states.GameStateNotInGame(self))
    """
    def __init__(self, players=None, board=None, log=None, pregame='on'):
        """
        Create a Game with the given options.

        :param players: list(Player)
        :param board: Board
        :param log: CatanLog
        :param pregame: (on|off)
        """
        self.observers = set()
        self.undo_manager = undo.UndoManager()
        self.options = {
            'pregame': pregame,
        }
        self.players = players or list()
        self.board = board or Board()
        self.robber = Piece(PieceType.robber, None)
        self.catanlog = log or catanlog.CatanLog()

        self.state = None # set in #set_state
        self.dev_card_state = None # set in #set_dev_card_state
        self._cur_player = None # set in #set_players
        self.last_roll = None # set in #roll
        self.last_player_to_roll = None # set in #roll
        self._cur_turn = 0 # incremented in #end_turn
        self.robber_tile = None # set in #move_robber

        self.board.observers.add(self)

        self.set_state(states.GameStateNotInGame(self))
        self.set_dev_card_state(states.DevCardNotPlayedState(self))

    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            if k == 'observers':
                setattr(result, k, set(v))
            elif k == 'state':
                setattr(result, k, v)
            else:
                setattr(result, k, copy.deepcopy(v, memo))
        return result

    def undo(self):
        """
        Rewind the game to the previous state.
        :return:
        """
        self.undo_manager.undo()
        self.notify_observers()
        logging.debug('undo_manager.stack={}'.format(self.undo_manager.command_stack))

    def copy(self):
        """
        Return a deep copy of this Game object. See Game.__deepcopy__ for the copy implementation.
        :return: Game
        """
        return copy.deepcopy(self)

    def restore(self, game):
        """
        Restore this Game object to match the properties and state of the given Game object
        :param game: properties to restore to the current (self) Game
        """
        self.observers = game.observers
        # self.undo_manager = game.undo_manager
        self.options = game.options
        self.players = game.players
        self.board.restore(game.board)
        self.robber = game.robber
        self.catanlog = game.catanlog

        self.state = game.state
        self.state.game = self

        self.dev_card_state = game.dev_card_state

        self._cur_player = game._cur_player
        self.last_roll = game.last_roll
        self.last_player_to_roll = game.last_player_to_roll
        self._cur_turn = game._cur_turn
        self.robber_tile = game.robber_tile

        self.notify_observers()

    def notify(self, observable):
        self.notify_observers()

    def notify_observers(self):
        for obs in self.observers.copy():
            obs.notify(self)

    def set_state(self, game_state):
        _old_state = self.state
        _old_board_state = self.board.state
        self.state = game_state
        if game_state.is_in_game():
            self.board.lock()
        else:
            self.board.unlock()
        logging.info('Game now={}, was={}. Board now={}, was={}'.format(
            type(self.state).__name__,
            type(_old_state).__name__,
            type(self.board.state).__name__,
            type(_old_board_state).__name__
        ))
        self.notify_observers()

    def set_dev_card_state(self, dev_state):
        self.dev_card_state = dev_state
        self.notify_observers()

    def start(self, players):
        """
        Start the game.

        The value of option 'pregame' determines whether the pregame will occur or not.

        - Resets the board
        - Sets the players
        - Sets the game state to the appropriate first turn of the game
        - Finds the robber on the board, sets the robber_tile appropriately
        - Logs the catanlog header

        :param players: players to start the game with
        """
        import boardbuilder
        self.reset()
        if self.board.opts.get('players') == boardbuilder.Opt.debug:
            players = Game.get_debug_players()
        self.set_players(players)
        if self.options.get('pregame') is None or self.options.get('pregame') == 'on':
            logging.debug('Entering pregame, game options={}'.format(self.options))
            self.set_state(states.GameStatePreGamePlaceSettlement(self))
        elif self.options.get('pregame') == 'off':
            logging.debug('Skipping pregame, game options={}'.format(self.options))
            self.set_state(states.GameStateBeginTurn(self))

        terrain = list()
        numbers = list()
        ports = list()
        for tile in self.board.tiles:
            terrain.append(tile.terrain)
            numbers.append(tile.number)

        for (_, coord), piece in self.board.pieces.items():
            if piece.type == PieceType.robber:
                self.robber_tile = hexgrid.tile_id_from_coord(coord)
                logging.debug('Found robber at coord={}, set robber_tile={}'.format(coord, self.robber_tile))

        self.catanlog.log_game_start(self.players, terrain, numbers, self.board.ports)
        self.notify_observers()

    def end(self):
        self.catanlog.log_player_wins(self.get_cur_player())
        self.set_state(states.GameStateNotInGame(self))

    def reset(self):
        self.players = list()
        self.state = states.GameStateNotInGame(self)

        self.last_roll = None
        self.last_player_to_roll = None
        self._cur_player = None
        self._cur_turn = 0

        self.notify_observers()

    def get_cur_player(self):
        if self._cur_player is None:
            return Player(1, 'nobody', 'nobody')
        else:
            return Player(self._cur_player.seat, self._cur_player.name, self._cur_player.color)

    def set_cur_player(self, player):
        self._cur_player = Player(player.seat, player.name, player.color)

    def set_players(self, players):
        self.players = list(players)
        self.set_cur_player(self.players[0])
        self.notify_observers()

    def cur_player_has_port(self, port):
        return self.player_has_port(self.get_cur_player(), port)

    def player_has_port(self, player, port):
        logging.warning('player_has_port not yet implemented in models, returning True')
        return True

    def roll(self, roll):
        self.undo_manager.do(commands.CmdRoll(self, roll))

    def move_robber(self, tile):
        self.undo_manager.do(commands.CmdMoveRobber(self, tile))

    def steal(self, victim):
        self.undo_manager.do(commands.CmdSteal(self, victim))

    def stealable_players(self):
        if self.robber_tile is None:
            return list()
        stealable = set()
        for node in hexgrid.nodes_touching_tile(self.robber_tile):
            pieces = self.board.get_pieces(types=(PieceType.settlement, PieceType.city), coord=node)
            if pieces:
                logging.debug('found stealable player={}, cur={}'.format(pieces[0].owner, self.get_cur_player()))
                stealable.add(pieces[0].owner)
        if self.get_cur_player() in stealable:
            stealable.remove(self.get_cur_player())
        logging.debug('stealable players={} at robber tile={}'.format(stealable, self.robber_tile))
        return stealable

    def buy_road(self, edge):
        #self.assert_legal_road(edge)
        self.undo_manager.do(commands.CmdBuyRoad(self, edge))

    def buy_settlement(self, node):
        #self.assert_legal_settlement(node)
        piece = Piece(PieceType.settlement, self.get_cur_player())
        self.board.place_piece(piece, node)
        self.catanlog.log_player_buys_settlement(self.get_cur_player(), node)
        if self.state.is_in_pregame():
            self.set_state(states.GameStatePreGamePlaceRoad(self))
        else:
            self.set_state(states.GameStateDuringTurnAfterRoll(self))

    def buy_city(self, node):
        #self.assert_legal_city(node)
        piece = Piece(PieceType.city, self.get_cur_player())
        self.board.place_piece(piece, node)
        self.catanlog.log_player_buys_city(self.get_cur_player(), node)
        self.set_state(states.GameStateDuringTurnAfterRoll(self))

    def buy_dev_card(self):
        self.catanlog.log_player_buys_dev_card(self.get_cur_player())
        self.notify_observers()

    def place_road(self, edge_coord):
        self.state.place_road(edge_coord)

    def place_settlement(self, node_coord):
        self.state.place_settlement(node_coord)

    def place_city(self, node_coord):
        self.state.place_city(node_coord)

    def trade(self, trade):
        giver = trade.giver().color
        giving = [(n, t.value) for n, t in trade.giving()]
        getting = [(n, t.value) for n, t in trade.getting()]
        if trade.getter() in PortType:
            getter = trade.getter().value
            self.catanlog.log_player_trades_with_port(giver, giving, getter, getting)
            logging.debug('trading {} to port={} to get={}'.format(giving, getter, getting))
        else:
            getter = trade.getter().color
            self.catanlog.log_player_trades_with_other(giver, giving, getter, getting)
            logging.debug('trading {} to player={} to get={}'.format(giving, getter, getting))
        self.notify_observers()

    def play_knight(self):
        self.set_dev_card_state(states.DevCardPlayedState(self))
        self.set_state(states.GameStateMoveRobberUsingKnight(self))

    def play_monopoly(self, resource):
        self.catanlog.log_player_plays_dev_monopoly(self.get_cur_player(), resource)
        self.set_dev_card_state(states.DevCardPlayedState(self))

    def play_year_of_plenty(self, resource1, resource2):
        self.catanlog.log_player_plays_dev_year_of_plenty(self.get_cur_player(), resource1, resource2)
        self.set_dev_card_state(states.DevCardPlayedState(self))

    def play_road_builder(self, edge1, edge2):
        self.catanlog.log_player_plays_dev_road_builder(self.get_cur_player(), edge1, edge2)
        self.set_dev_card_state(states.DevCardPlayedState(self))

    def play_victory_point(self):
        self.catanlog.log_player_plays_dev_victory_point(self.get_cur_player())
        self.set_dev_card_state(states.DevCardPlayedState(self))

    def end_turn(self):
        self.catanlog.log_player_ends_turn(self.get_cur_player())
        self.set_cur_player(self.state.next_player())
        self._cur_turn += 1

        self.set_dev_card_state(states.DevCardNotPlayedState(self))
        if self.state.is_in_pregame():
            self.set_state(states.GameStatePreGamePlaceSettlement(self))
        else:
            self.set_state(states.GameStateBeginTurn(self))

    @classmethod
    def get_debug_players(cls):
        return [Player(1, 'yurick', 'green'),
                Player(2, 'josh', 'blue'),
                Player(3, 'zach', 'orange'),
                Player(4, 'ross', 'red')]


class Player(object):
    """class Player represents a single player on the game board.

    :param seat: integer, with 1 being top left, and increasing clockwise
    :param name: will be lowercased, spaces will be removed
    :param color: will be lowercased, spaces will be removed
    """
    def __init__(self, seat, name, color):
        if not (1 <= seat <= 4):
            raise Exception("Seat must be on [1,4]")
        self.seat = seat

        self.name = name.lower().replace(' ', '')
        self.color = color.lower().replace(' ', '')

    def __eq__(self, other):
        if other is None:
            return False
        return (self.color == other.color
                and self.name == other.name
                and self.seat == other.seat)

    def __repr__(self):
        return '{} ({})'.format(self.color, self.name)

    def __hash__(self):
        return sum(bytes(str(self), encoding='utf8'))


class Tile(object):
    """
    class Tile represents a hex tile on the catan board.

    It contains a tile identifier, a terrain type, and a number.
    """
    def __init__(self, tile_id, terrain, number):
        """
        :param tile_id: tile identifier, int, see module hexgrid
        :param terrain: Terrain
        :param number: HexNumber
        :return:
        """
        self.tile_id = tile_id
        self.terrain = terrain
        self.number = number

# Number of tiles on the catan board. This should probably be in module hexgrid.
NUM_TILES = 3+4+5+4+3


class Terrain(Enum):
    wood = 'wood'
    brick = 'brick'
    wheat = 'wheat'
    sheep = 'sheep'
    ore = 'ore'
    desert = 'desert'

    def __repr__(self):
        return self.value


class HexNumber(Enum):
    none = None
    two = 2
    three = 3
    four = 4
    five = 5
    six = 6
    eight = 8
    nine = 9
    ten = 10
    eleven = 11
    twelve = 12


class PortType(Enum):
    any4 = '4:1' # not used in UI, only used in trading
    any3 = '3:1'
    wood = 'wood'
    brick = 'brick'
    wheat = 'wheat'
    sheep = 'sheep'
    ore = 'ore'
    none = 'none' # only used in UI, not used in trading

    @classmethod
    def list_ui(cls):
        return list(filter(lambda pt: pt != PortType.any4, PortType))

    @classmethod
    def list_trading(cls):
        return list(filter(lambda pt: pt != PortType.none, PortType))

    @classmethod
    def next_ui(cls, ptype):
        types = list(PortType)
        next_idx = (types.index(ptype) + 1) % len(types)
        next_port_type = types[next_idx]
        if next_port_type == PortType.any4:
            next_port_type = PortType.next_ui(next_port_type)
        return next_port_type


class Port(object):
    """
    class Port represents a single port on the board.

    Allowed types are described in enum PortType.
    """
    def __init__(self, tile_id, direction, type):
        self.tile_id = tile_id
        self.direction = direction
        self.type = type

    def __repr__(self):
        return '{}({},{})'.format(self.type.value, self.tile_id, self.direction)


class PieceType(Enum):
    settlement = 'settlement'
    road = 'road'
    city = 'city'
    robber = 'robber'


class Piece(object):
    """
    class Piece represents a single game piece on the board.

    Allowed types are described in enum PieceType
    """
    def __init__(self, type, owner):
        self.type = type
        self.owner = owner

    def __repr__(self):
        return '<Piece type={}, owner={}>'.format(self.type.value, self.owner)


class Board(object):
    """
    class Board represents a catan board. It has tiles, ports, and pieces.

    A Board has pieces, which is a dictionary mapping (hexgrid.TYPE, coord) -> Piece.

    Use #place_piece, #move_piece, and #remove_piece to manage pieces on the board.

    Use #get_pieces to get all the pieces at a particular coordinate of the allowed types.
    """
    def __init__(self, terrain=None, numbers=None, ports=None, pieces=None, players=None):
        """
        Create a new board. Creation will be delegated to module boardbuilder.

        :param terrain: terrain option, boardbuilder.Opt
        :param numbers: numbers option, boardbuilder.Opt
        :param ports: ports option, boardbuilder.Opt
        :param pieces: pieces option, boardbuilder.Opt
        :param players: players option, boardbuilder.Opt
        """
        self.tiles = list()
        self.ports = list()
        self.state = states.BoardState(self)
        self.pieces = dict()

        self.opts = dict()
        if terrain is not None:
            self.opts['terrain'] = terrain
        if numbers is not None:
            self.opts['numbers'] = numbers
        if ports is not None:
            self.opts['ports'] = ports
        if pieces is not None:
            self.opts['pieces'] = pieces
        if players is not None:
            self.opts['players'] = players

        self.reset()
        self.observers = set()

    def __deepcopy__(self, memo):
        cls = self.__class__
        result = object.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            if k == 'observers':
                setattr(result, k, set(v))
            else:
                setattr(result, k, copy.deepcopy(v, memo))
        return result

    def restore(self, board):
        """
        Restore this Board object to match the properties and state of the given Board object
        :param board: properties to restore to the current (self) Board
        """
        self.tiles = board.tiles
        self.ports = board.ports

        self.state = board.state
        self.state.board = self

        self.pieces = board.pieces
        self.opts = board.opts
        self.observers = board.observers

        self.notify_observers()

    def notify_observers(self):
        for obs in self.observers:
            obs.notify(self)

    def lock(self):
        self.state = states.BoardStateLocked(self)
        for port in self.ports.copy():
            if port.type == PortType.none:
                self.ports.remove(port)
        self.notify_observers()

    def unlock(self):
        self.state = states.BoardStateModifiable(self)

    def reset(self, terrain=None, numbers=None, ports=None, pieces=None, players=None):
        import boardbuilder
        opts = self.opts.copy()
        if terrain is not None:
            opts['terrain'] = terrain
        if numbers is not None:
            opts['numbers'] = numbers
        if ports is not None:
            opts['ports'] = ports
        if pieces is not None:
            opts['pieces'] = pieces
        if players is not None:
            opts['players'] = players
        boardbuilder.reset(self, opts=opts)

    def can_place_piece(self, piece, coord):
        if piece.type == PieceType.road:
            logging.warning('"Can place road" not yet implemented')
            return True
        elif piece.type == PieceType.settlement:
            logging.warning('"Can place settlement" not yet implemented')
            return True
        elif piece.type == PieceType.city:
            logging.warning('"Can place city" not yet implemented')
            return True
        elif piece.type == PieceType.robber:
            logging.warning('"Can place robber" not yet implemented')
            return True
        else:
            logging.debug('Can\'t place piece={} on coord={}'.format(
                piece.value, hex(coord)
            ))
            return self.pieces.get(coord) is None

    def place_piece(self, piece, coord):
        if not self.can_place_piece(piece, coord):
            logging.critical('ILLEGAL: Attempted to place piece={} on coord={}'.format(
                piece.value, hex(coord)
            ))
        logging.debug('Placed piece={} on coord={}'.format(
            piece, hex(coord)
        ))
        hex_type = self._piece_type_to_hex_type(piece.type)
        self.pieces[(hex_type, coord)] = piece

    def move_piece(self, piece, from_coord, to_coord):
        from_index = (self._piece_type_to_hex_type(piece.type), from_coord)
        if from_index not in self.pieces:
            logging.warning('Attempted to move piece={} which was NOT on the board'.format(from_index))
            return
        self.place_piece(piece, to_coord)
        self.remove_piece(piece, from_coord)

    def remove_piece(self, piece, coord):
        index = (self._piece_type_to_hex_type(piece.type), coord)
        try:
            self.pieces.pop(index)
            logging.debug('Removed piece={}'.format(index))
        except ValueError:
            logging.critical('Attempted to remove piece={} which was NOT on the board'.format(index))

    def get_pieces(self, types=tuple(), coord=None):
        if coord is None:
            logging.critical('Attempted to get_piece with coord={}'.format(coord))
            return Piece(None, None)
        indexes = set((self._piece_type_to_hex_type(t), coord) for t in types)
        pieces = [self.pieces[idx] for idx in indexes if idx in self.pieces]
        if len(pieces) == 0:
            #logging.warning('Found zero pieces at {}'.format(indexes))
            pass
        elif len(pieces) == 1:
            logging.debug('Found one piece at {}: {}'.format(indexes, pieces[0]))
        elif len(pieces) > 1:
            logging.debug('Found {} pieces at {}: {}'.format(len(pieces), indexes, coord, pieces))
        return pieces

    def get_port_at(self, tile_id, direction):
        """
        If no port is found, a new none port is made and added to self.ports.

        Returns the port.

        :param tile_id:
        :param direction:
        :return: Port
        """
        for port in self.ports:
            if port.tile_id == tile_id and port.direction == direction:
                return port
        port = Port(tile_id, direction, PortType.none)
        self.ports.append(port)
        return port

    def _piece_type_to_hex_type(self, piece_type):
        if piece_type in (PieceType.road, ):
            return hexgrid.EDGE
        elif piece_type in (PieceType.settlement, PieceType.city):
            return hexgrid.NODE
        elif piece_type in (PieceType.robber, ):
            return hexgrid.TILE
        else:
            logging.critical('piece type={} has no corresponding hex type. Returning None'.format(piece_type))
            return None

    def cycle_hex_type(self, tile_id):
        if self.state.modifiable():
            tile = self.tiles[tile_id - 1]
            next_idx = (list(Terrain).index(tile.terrain) + 1) % len(Terrain)
            next_terrain = list(Terrain)[next_idx]
            tile.terrain = next_terrain
        else:
            logging.debug('Attempted to cycle terrain on tile={} on a locked board'.format(tile_id))
        self.notify_observers()

    def cycle_hex_number(self, tile_id):
        if self.state.modifiable():
            tile = self.tiles[tile_id - 1]
            next_idx = (list(HexNumber).index(tile.number) + 1) % len(HexNumber)
            next_hex_number = list(HexNumber)[next_idx]
            tile.number = next_hex_number
        else:
            logging.debug('Attempted to cycle number on tile={} on a locked board'.format(tile_id))
        self.notify_observers()

    def cycle_port_type(self, tile_id, direction):
        if self.state.modifiable():
            port = self.get_port_at(tile_id, direction)
            port.type = PortType.next_ui(port.type)
        else:
            logging.debug('Attempted to cycle port on coord=({},{}) on a locked board'.format(tile_id, direction))
        self.notify_observers()
