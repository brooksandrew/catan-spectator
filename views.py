import tkinter
from tkinter import messagebox
import math
import itertools
import collections
import functools

from models import Terrain, Port, Player, HexNumber


class BoardFrame(tkinter.Frame):

    def __init__(self, master, game, options=None, *args, **kwargs):
        super(BoardFrame, self).__init__()
        self.master = master
        self.game = game
        self.game.observers.add(self)

        self._board = game.board

        board_canvas = tkinter.Canvas(self, height=600, width=600, background='Royal Blue')
        board_canvas.pack(expand=tkinter.YES, fill=tkinter.BOTH)

        self._board_canvas = board_canvas
        self._center_to_edge = math.cos(math.radians(30)) * self._tile_radius

        self.game.observers.add(self)

    def tile_click(self, event):
        tag = self._board_canvas.gettags(event.widget.find_closest(event.x, event.y))[0]
        if self.master.options.get('hex_resource_selection'):
            self._board.cycle_hex_type(self._tile_id_from_tag(tag))
        if self.master.options.get('hex_number_selection'):
            self._board.cycle_hex_number(self._tile_id_from_tag(tag))
        self.redraw()

    def notify(self, observable):
        self.redraw()

    def draw(self, board):
        """Render the board to the canvas widget.

        Taking the center of the first tile as 0, 0 we follow the path of tiles
        around the graph as given by the board (must be guaranteed to be a
        connected path that visits every tile) and calculate the center of each
        tile as the offset from the last one, based on it's direction from the
        last tile and the radius of the hexagons (and padding etc.)

        We then shift all the individual tile centers so that the board center
        is at 0, 0.
        """

        centers = {}
        last = None

        for tile in board.tiles:
            if not last:
                centers[tile.tile_id] = (0, 0)
                last = tile
                continue

            # Calculate the center of this tile as an offset from the center of
            # the neighboring tile in the given direction.
            ref_center = centers[last.tile_id]
            direction = board.direction(last, tile)
            theta = self._angle_order.index(direction) * 60
            radius = 2 * self._center_to_edge + self._tile_padding
            dx = radius * math.cos(math.radians(theta))
            dy = radius * math.sin(math.radians(theta))
            centers[tile.tile_id] = (ref_center[0] + dx, ref_center[1] + dy)
            last = tile

        port_centers = []
        for tile_id, dirn, value in board.ports:
            ref_center = centers[tile_id]
            theta = self._angle_order.index(dirn) * 60
            radius = 2 * self._center_to_edge + self._tile_padding
            dx = radius * math.cos(math.radians(theta))
            dy = radius * math.sin(math.radians(theta))
            port_centers.append((ref_center[0] + dx, ref_center[1] + dy, theta))

        offx, offy = self._board_center

        # Temporary hack to center the board. Not generic to different board types.
        radius = 4 * self._center_to_edge + 2 * self._tile_padding
        offx += radius * math.cos(math.radians(240))
        offy += radius * math.sin(math.radians(240))

        centers = dict((tile_id, (x + offx, y + offy)) for tile_id, (x, y) in centers.items())
        for tile_id, (x, y) in centers.items():
            tile = board.tiles[tile_id - 1]
            self._draw_tile(x, y, tile.terrain, tile.number, tile)
            self._board_canvas.tag_bind(self._tile_tag(tile), '<ButtonPress-1>', func=self.tile_click)

        port_centers = [(x + offx, y + offy, t + 180) for x, y, t in port_centers]
        for (x, y, t), port in zip(port_centers, [v for _, _, v in board.ports]):
            self._draw_port(x, y, t, port)

    def redraw(self):
        self._board_canvas.delete(tkinter.ALL)
        self.draw(self._board)

    def _draw_hexagon(self, radius, offset=(0, 0), rotate=30, fill='black', tags=None):
        points = self._hex_points(radius, offset, rotate)
        a = self._board_canvas.create_polygon(*itertools.chain.from_iterable(points), fill=fill, tags=tags)

    def _draw_tile(self, x, y, terrain, number, tile):
        self._draw_hexagon(self._tile_radius, offset=(x, y), fill=self._colors[terrain], tags=self._tile_tag(tile))
        if number.value:
            color = 'red' if number.value in (6, 8) else 'black'
            self._board_canvas.create_text(x, y, text=str(number.value), font=self._hex_font, fill=color)

    def _draw_port(self, x, y, angle, port):
        """Draw a equilateral triangle with the top point at x, y and the bottom facing the direction
        given by the angle."""
        points = [x, y]
        for adjust in (-30, 30):
            x1 = x + math.cos(math.radians(angle + adjust)) * self._tile_radius
            y1 = y + math.sin(math.radians(angle + adjust)) * self._tile_radius
            points.extend([x1, y1])
        self._board_canvas.create_polygon(*points, fill=self._colors[port])
        self._board_canvas.create_text(x, y, text=port.value, font=self._hex_font)

    def _hex_points(self, radius, offset, rotate):
        offx, offy = offset
        points = []
        for theta in (60 * n for n in range(6)):
            x = (math.cos(math.radians(theta + rotate)) * radius) + offx
            y = (math.sin(math.radians(theta + rotate)) * radius) + offy
            points.append((x, y))
        return points

    def _tile_tag(self, tile):
        return 'tile_' + str(tile.tile_id)

    def _tile_id_from_tag(self, tag):
        return int(tag[len('tile_'):])

    _tile_radius  = 50
    _tile_padding = 3
    _board_center = (300, 300)
    _angle_order  = ('E', 'SE', 'SW', 'W', 'NW', 'NE')
    _hex_font     = (('Helvetica'), 18)
    _colors = {
        Terrain.ore: 'gray94',
        Port.ore: 'gray94',
        Terrain.wood: 'forest green',
        Port.wood: 'forest green',
        Terrain.sheep: 'green yellow',
        Port.sheep: 'green yellow',
        Terrain.brick: 'sienna4',
        Port.brick: 'sienna4',
        Terrain.wheat: 'yellow2',
        Port.wheat: 'yellow2',
        Terrain.desert: 'wheat1',
        Port.any: 'gray'}


class PregameToolbarFrame(tkinter.Frame):

    def __init__(self, master, game, options=None, *args, **kwargs):
        super(PregameToolbarFrame, self).__init__()
        self.master = master
        self.game = game

        self.options = options or dict()
        self.options.update({
            'hex_resource_selection': True,
            'hex_number_selection': False
        })

        tkinter.Label(self, text="Board Setup", anchor=tkinter.W).pack(side=tkinter.TOP, fill=tkinter.X)
        for option in TkinterOptionWrapper(self.options):
            option.callback()
            tkinter.Checkbutton(self, text=option.text, justify=tkinter.LEFT, command=option.callback, var=option.var) \
                .pack(side=tkinter.TOP, fill=tkinter.X)

        tkinter.Label(self, text="Players (name color)", anchor=tkinter.W).pack(side=tkinter.TOP, fill=tkinter.X)
        defaults = ('yurick green', 'josh blue', 'zach orange', 'ross red')
        self.player_entries_vars = [(tkinter.Entry(self), tkinter.StringVar()) for i in range(len(defaults))]
        for (entry, var), default in zip(self.player_entries_vars, defaults):
            var.set(default)
            entry.config(textvariable=var)
            entry.pack(side=tkinter.TOP, fill=tkinter.BOTH)

        btn_start_game = tkinter.Button(self, text='Start Game', command=self.on_start_game)
        btn_start_game.pack(side=tkinter.TOP, fill=tkinter.X)

    def on_start_game(self):
        def get_name(var):
            return var.get().split(' ')[0]

        def get_color(var):
            return var.get().split(' ')[1]

        self.game.start([Player(i, get_name(var), get_color(var))
                         for i, (_, var) in enumerate(self.player_entries_vars, 1)])


class GameToolbarFrame(tkinter.Frame):

    def __init__(self, master, game, *args, **kwargs):
        super(GameToolbarFrame, self).__init__()
        self.master = master
        self.game = game

        self.game.observers.add(self)

        self._cur_player = self.game.get_cur_player()
        self._cur_player_name = tkinter.StringVar()
        self.set_cur_player_name()

        label_cur_player_name = tkinter.Label(self, textvariable=self._cur_player_name, anchor=tkinter.W)
        frame_roll = RollFrame(self, self.game)
        frame_robber = RobberFrame(self, self.game)
        frame_build = BuildFrame(self, self.game)
        frame_trade = TradeFrame(self, self.game)
        frame_play_dev = PlayDevCardFrame(self, self.game)
        frame_end_turn = EndTurnFrame(self, self.game)
        frame_end_game = EndGameFrame(self, self.game)

        label_cur_player_name.pack(side=tkinter.TOP, fill=tkinter.X)
        frame_roll.pack(side=tkinter.TOP, fill=tkinter.X)
        frame_robber.pack(side=tkinter.TOP, fill=tkinter.X)
        frame_build.pack(side=tkinter.TOP, fill=tkinter.X)
        frame_trade.pack(side=tkinter.TOP, fill=tkinter.X)
        frame_play_dev.pack(side=tkinter.TOP, fill=tkinter.X)
        frame_end_turn.pack(side=tkinter.TOP, fill=tkinter.X)
        frame_end_game.pack(side=tkinter.BOTTOM, fill=tkinter.BOTH)

    def set_game(self, game):
        self.game = game

    def notify(self, observable):
        if self._cur_player.color != self.game.get_cur_player().color:
            self.set_cur_player_name()

    def set_cur_player_name(self):
        self._cur_player = self.game.get_cur_player()
        self._cur_player_name.set('Current Player: {0} ({1})'.format(
            self._cur_player.color,
            self._cur_player.name
        ))


class RollFrame(tkinter.Frame):

    def __init__(self, master, game, *args, **kwargs):
        super(RollFrame, self).__init__(master)
        self.master = master
        self.game = game
        self._cur_player = self.game.get_cur_player()
        self.game.observers.add(self)

        self.roll = tkinter.StringVar()
        self.spinner = tkinter.Spinbox(self, values=(2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12), textvariable=self.roll)
        self.button = tkinter.Button(self, text="Roll", command=self.on_roll)

        self.spinner.pack(side=tkinter.LEFT)
        self.button.pack(side=tkinter.RIGHT)

    def notify(self, observable):
        if self._cur_player.color != self.game.get_cur_player().color:
            self.button.configure(state=tkinter.NORMAL)
            self.spinner.configure(state=tkinter.NORMAL)
            self._cur_player = self.game.get_cur_player()

    def on_roll(self):
        self.button.configure(state=tkinter.DISABLED)
        self.spinner.configure(state=tkinter.DISABLED)
        self.game.roll(self.roll.get())


class RobberFrame(tkinter.Frame):

    def __init__(self, master, game):
        super(RobberFrame, self).__init__(master)
        self.master = master
        self.game = game
        self.game.observers.add(self)

        self.move_robber = tkinter.Button(self, text="Move Robber", state=tkinter.DISABLED, command=self.on_move_robber)
        self.steal = tkinter.Button(self, text="Steal", state=tkinter.DISABLED, command=self.on_steal)

        self.move_robber.pack(side=tkinter.LEFT, fill=tkinter.X, expand=True)
        self.steal.pack(side=tkinter.RIGHT, fill=tkinter.X, expand=True)

    def notify(self, observable):
        if self.game.state.can_move_robber():
            self.move_robber.configure(state=tkinter.NORMAL)
        else:
            self.move_robber.configure(state=tkinter.DISABLED)

        if self.game.state.can_steal():
            self.steal.configure(state=tkinter.NORMAL)
        else:
            self.steal.configure(state=tkinter.DISABLED)

    def on_move_robber(self):
        self.game.move_robber()

    def on_steal(self):
        self.game.steal()


class BuildFrame(tkinter.Frame):

    def __init__(self, master, game):
        super(BuildFrame, self).__init__(master)
        self.master = master
        self.game = game
        self.game.observers.add(self)

        self.label = tkinter.Label(self, text="Build", anchor=tkinter.W)
        self.road = tkinter.Button(self, text="Road", command=self.on_build_road)
        self.settlement = tkinter.Button(self, text="Settlement", command=self.on_build_settlement)
        self.city = tkinter.Button(self, text="City", command=self.on_build_city)
        self.dev_card = tkinter.Button(self, text="Dev Card", command=self.on_build_dev_card)

        self.set_states()

        self.label.pack(fill=tkinter.X)
        self.road.pack(fill=tkinter.X, expand=True)
        self.settlement.pack(fill=tkinter.X, expand=True)
        self.city.pack(fill=tkinter.X, expand=True)
        self.dev_card.pack(fill=tkinter.X, expand=True)

    def notify(self, observable):
        self.set_states()

    def set_states(self):
        """You must roll before building"""
        if not self.game.state.has_rolled():
            state = tkinter.DISABLED
        else:
            state = tkinter.NORMAL

        self.road.configure(state=state)
        self.settlement.configure(state=state)
        self.city.configure(state=state)
        self.dev_card.configure(state=state)

    def on_build_road(self):
        pass

    def on_build_settlement(self):
        pass

    def on_build_city(self):
        pass

    def on_build_dev_card(self):
        pass


class TradeFrame(tkinter.Frame):

    def __init__(self, master, game):
        super(TradeFrame, self).__init__(master)
        self.master = master
        self.game = game
        self._cur_player = self.game.get_cur_player()
        self.game.observers.add(self)

        self.label_player = tkinter.Label(self, text="Trade with Player")
        self.player_buttons = list()
        for p in self.game.players:
            button = tkinter.Button(self, text='{0} ({1})'.format(p.color, p.name), state=tkinter.DISABLED)
            self.player_buttons.append(button)

        self.set_states(self._cur_player)

        self.label_port = tkinter.Label(self, text="Trade with Port")
        self.port_buttons = list()
        for p in list(Port):
            button = tkinter.Button(self, text='{0}'.format(p.value), state=tkinter.DISABLED)
            self.port_buttons.append(button)

        ##
        # Place elements in frame
        #

        row = 0
        self.label_player.grid(row=row, sticky=tkinter.W)
        row += 1

        for i, button in enumerate(self.player_buttons):
            button.grid(row=row + i // 2, column=i % 2, sticky=tkinter.EW)
        row += 2

        self.label_port.grid(row=row, sticky=tkinter.W)
        row += 1

        for i, button in enumerate(self.port_buttons):
            button.grid(row=row + i // 2, column=i % 2, sticky=tkinter.EW)
        row += 2

    def notify(self, observable):
        # You can't trade with yourself
        self._cur_player = self.game.get_cur_player()
        self.set_states(self._cur_player)

    def set_states(self, current_player):
        """You can't trade with yourself, and you have to roll before trading"""
        for player, button in zip(self.game.players, self.player_buttons):
            if not self.game.state.has_rolled() or player == current_player:
                button.configure(state=tkinter.DISABLED)
            else:
                button.configure(state=tkinter.NORMAL)


class PlayDevCardFrame(tkinter.Frame):

    def __init__(self, master, game):
        super(PlayDevCardFrame, self).__init__(master)
        self.master = master
        self.game = game
        self.game.observers.add(self)

        self.label = tkinter.Label(self, text="Play Dev Card", anchor=tkinter.W)
        self.knight = tkinter.Button(self, text="Knight", command=self.on_knight)
        self.monopoly = tkinter.Button(self, text="Monopoly", command=self.on_monopoly)
        self.road_builder = tkinter.Button(self, text="Road Builder", command=self.on_road_builder)
        self.victory_point = tkinter.Button(self, text="Victory Point", command=self.on_victory_point)

        self.set_states()

        self.label.pack(fill=tkinter.X)
        self.knight.pack(fill=tkinter.X, expand=True)
        self.monopoly.pack(fill=tkinter.X, expand=True)
        self.road_builder.pack(fill=tkinter.X, expand=True)
        self.victory_point.pack(fill=tkinter.X, expand=True)

    def notify(self, observable):
        self.set_states()

    def set_states(self):
        self.victory_point.configure(state=tkinter.NORMAL)

        if self.game.state.can_play_knight_dev_card():
            self.knight.configure(state=tkinter.NORMAL)
        else:
            self.knight.configure(state=tkinter.DISABLED)

        if self.game.state.can_play_non_knight_dev_card():
            self.monopoly.configure(state=tkinter.NORMAL)
            self.road_builder.configure(state=tkinter.NORMAL)
        else:
            self.monopoly.configure(state=tkinter.DISABLED)
            self.road_builder.configure(state=tkinter.DISABLED)

    def on_knight(self):
        pass

    def on_monopoly(self):
        pass

    def on_road_builder(self):
        pass

    def on_victory_point(self):
        pass


class EndTurnFrame(tkinter.Frame):

    def __init__(self, master, game):
        super(EndTurnFrame, self).__init__(master)
        self.master = master
        self.game = game
        self.game.observers.add(self)

        self.label = tkinter.Label(self, text='--')
        self.end_turn = tkinter.Button(self, text='End Turn', state=tkinter.DISABLED, command=self.on_end_turn)

        self.label.pack()
        self.end_turn.pack(side=tkinter.TOP, fill=tkinter.X)

    def notify(self, observable):
        if self.game.state.end_turn_allowed():
            self.end_turn.configure(state=tkinter.NORMAL)
        else:
            self.end_turn.configure(state=tkinter.DISABLED)

    def on_end_turn(self):
        self.game.end_turn()


class EndGameFrame(tkinter.Frame):

    def __init__(self, master, game):
        super(EndGameFrame, self).__init__(master)
        self.master = master
        self.game = game

        self.end_game = tkinter.Button(self, text='End Game', state=tkinter.NORMAL, command=self.on_end_game)
        self.end_game.pack(side=tkinter.TOP, fill=tkinter.X)

    def on_end_game(self):
        title = 'End Game Confirmation'
        message = 'End Game? ({0} ({1}) wins)'.format(
            self.game.get_cur_player().color, self.game.get_cur_player().name
        )
        if messagebox.askyesno(title, message):
            self.game.end()


class TkinterOptionWrapper:
    """Dynamically hook up the board options to tkinter checkbuttons.

    Tkinter checkbuttons use a tkinter 'var' object to store the checkbutton
    value, so dynamically create those vars based on the board options and
    keep them here, along with callbacks to update the board options when the
    checkbutton is checked/unchecked.

    Also stores the option description text. That should probably belong to the
    board option 'class', but at the moment there's no reason not to keep that
    a simple dict.

    Parameters
    ----------

    options : A dict of option identifier (name) to option value

    The wrapper will dynamically update the value of the option in the
    option_dict when the user checks or unchecks the corresponding checkbutton
    in the UI.
    """

    Option = collections.namedtuple('_Option', ['text', 'var', 'callback'])
    _descriptions = {
        'hex_resource_selection': 'Cycle hex resource',
        'hex_number_selection': 'Cycle hex number'
    }

    def __init__(self, option_dict):
        self._opts = {}

        # Can't define this as a closure inside the following for loop as each
        # definition will become the value of cb which has a scope local to the
        # function, not to the for loop.  Use functools.partial in the loop to
        # create a specific callable instance.
        def cb_template(name, var):
            option_dict[name] = var.get()
        for name, value in option_dict.items():
            var = tkinter.BooleanVar()
            var.set(value)
            cb = functools.partial(cb_template, name, var)
            self._opts[name] = self.Option(self._descriptions.get(name) or name, var, cb)

    def __getattr__(self, name):
        attr = self.__dict__.get(name)
        if '_opts' in self.__dict__ and not attr:
            attr = self._opts.get(name)
        return attr

    def __iter__(self):
        for opt in sorted(self._opts.values()):
            yield opt

