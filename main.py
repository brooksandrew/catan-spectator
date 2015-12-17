"""Record a game of Settlers of Catan.

TODO: Allow ports to be selected during pregame
TODO: Control size adjustment with resizing of window
TODO: Simplify the algorithm for red placement now there is a connected path through
      the graph that visits every node.
TODO: Docstrings and unittests.
"""

import tkinter
import collections

import views
import models
import states
import recording


class CatanGameRecorder(tkinter.Frame):

    def __init__(self, options=None, *args, **kwargs):
        super(CatanGameRecorder, self).__init__()
        self.options = options or {
            'hex_resource_selection': True,
            'hex_number_selection': False
        }
        self.game = models.Game(list(), models.Board(), recording.GameRecord())
        self.game.observers.add(self)
        self._in_game = self.game.state.is_in_game()

        self._setup_game_toolbar_frame = views.SetupGameToolbarFrame(self, self.game, options=self.options)
        self._game_toolbar_frame = None
        board_frame = views.BoardFrame(self, self.game, options=self.options)

        board_frame.redraw()

        self._board_frame = board_frame
        self._toolbar_frame = self._setup_game_toolbar_frame

        self._board_frame.pack(side=tkinter.LEFT, fill=tkinter.Y)
        self._toolbar_frame.pack(side=tkinter.RIGHT, fill=tkinter.Y)

        self.lift()

    def notify(self, observable):
        was_in_game = self._in_game
        self._in_game = self.game.state.is_in_game()
        if was_in_game and not self.game.state.is_in_game():
            # we were in game, now we're not
            self._toolbar_frame.pack_forget()
            self._toolbar_frame = self._setup_game_toolbar_frame
            self._toolbar_frame.pack(side=tkinter.RIGHT, fill=tkinter.Y)
        elif not was_in_game and self.game.state.is_in_game():
            # we were not in game, now we are
            self._toolbar_frame.pack_forget()
            self._toolbar_frame = self._game_toolbar_frame or views.GameToolbarFrame(self, self.game)
            self._toolbar_frame.pack(side=tkinter.RIGHT, fill=tkinter.Y)


def main():
    app = CatanGameRecorder()
    app.mainloop()


if __name__ == "__main__":
    main()
