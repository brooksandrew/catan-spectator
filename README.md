catan-spectator
---------------

Transcribe games of Settlers of Catan for research purposes, replay purposes, broadcast purposes, etc.

The UI is feature-complete, and can be used to log games.

Packages written for this project: [`catanlog`](https://github.com/rosshamish/catanlog), [`hexgrid`](https://github.com/rosshamish/hexgrid), [`undoredo`](https://github.com/rosshamish/undoredo).

Todos are listed below.

> Author: Ross Anderson ([rosshamish](https://github.com/rosshamish))

### Installation

```
$ git clone https://github.com/rosshamish/catan-spectator
$ cd catan-spectator
$ pip install -r requirements.txt
```

### Usage

```
$ python3 main.py --help
usage: main.py [-h] [--terrain TERRAIN] [--numbers NUMBERS] [--ports PORTS]
               [--pieces PIECES] [--players PLAYERS] [--pregame PREGAME]

log a game of catan

optional arguments:
  -h, --help         show this help message and exit
  --terrain TERRAIN  random|preset|empty|debug, default empty
  --numbers NUMBERS  random|preset|empty|debug, default empty
  --ports PORTS      random|preset|empty|debug, default preset
  --pieces PIECES    random|preset|empty|debug, default empty
  --players PLAYERS  random|preset|empty|debug, default preset
  --pregame PREGAME  on|off, default on
```

Make targets:
- `make relaunch`: launch (or relaunch) the GUI
- `make logs`: cat the python logs
- `make tail`: tail the python logs
- `make`: alias for relaunch && tail

### Demo
![Demo](/doc/gifs/demo4.gif)

### File Format

catan-spectator writes game logs in the `.catan` format described by package [`catanlog`](https://github.com/rosshamish/catanlog).

### Todo

Need to have
- [ ] views documented
- [x] piece placing should be cancellable (via undo)
- [x] all actions should be undoable

Nice to have
- [ ] board: random number setup obeys red number rule
- [ ] ui+board+hexgrid: during piece placement, use little red x’s (at least in debug mode) on “killed spots”
- [ ] ui+game+player+states: dev cards, i.e. keep a count of how many dev cards a player has played and enable Play Dev Card buttons if num > 0
- [x] ui+game+port+hexgrid: port trading, disable buttons if the current player doesn’t have the port. 4:1 is always enabled.
- [x] ui+port+hexgrid: port trading, don't allow getting or giving more or less than defined by the port type (3:1, 2:1).
- [ ] ui+port: port trading, don’t allow n for 0 trades
- [ ] ui: large indicator off what the current player is (and what the order is)
- [x] ui: cancelling of roads/settlements/cities while placing
- [ ] ui+catanlog: save log file to custom location on End Game
- [ ] ui: images, colors in UI buttons (eg dice for roll, )
- [ ] ui: city-shaped polygon for cities
- [attempted, might be worse] ui: tile images instead of colored hexagons
- [ ] ui: port images instead of colored triangles
- [ ] ui: piece images instead of colored polygons
- [x] ui: number images instead of text (or avoid contrast issues otherwise)
- [ ] ui: roll frame: up on 12 goes to 2
- [ ] ui+game+states+robber: steal dropdown has “nil” option always, for in case it goes on a person with no cards and no steal happens. Name it something obvious, don’t use an empty string.

### Attribution

Codebase originally forked from [fruitnuke/catan](https://github.com/fruitnuke/catan), a catan board generator

### License

GPLv3
