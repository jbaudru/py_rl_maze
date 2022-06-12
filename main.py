from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtCore import QObject, QThread, pyqtSignal

from tile import Tile
from rl import QAgent

import pickle
import random
import time
import math
import numpy as np
from numpy import asarray
from tqdm import tqdm
import shutil
from asyncio import sleep

# ===============================================================================
# GLOBAL VARIABLES
# ===============================================================================
global SCORE, CURRENT_REVEALED, model, LEVEL
SCORE = 0
CURRENT_REVEALED = []
LEVELS = [
    (8, 10),
    (12, 10),
    (16, 10)
]
LEVEL = LEVELS[0]

COUNT = 0

STATUS_READY = 0
STATUS_PLAYING = 1
STATUS_FAILED = 2
STATUS_SUCCESS = 3

class MainWindow(QMainWindow):
    """
    Main class use for GUI and the AI managment
    """
    def __init__(self, *args, **kwargs):
        global LEVEL
        super(MainWindow, self).__init__(*args, **kwargs)

        self.setWindowTitle("RL Maze")
        self.setWindowFlags(Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self.setWindowIcon(QIcon("./images/icon2.png"))
        self.setWindowFlag(Qt.WindowMinimizeButtonHint, True)
        self.setWindowFlag(Qt.WindowMaximizeButtonHint, False)
        self.b_size, self.n_mines = LEVEL
        self.agent = None

        w = QWidget()
        vb = QVBoxLayout()
        hb = QHBoxLayout()
        hb0 = QHBoxLayout()
        hb1 = QHBoxLayout()

        self.cb = QComboBox()
        self.cb.addItems(["100 train", "200 train", "500 train", "1000 train"])
        self.cb.setCurrentIndex(1)
        self.cb.setToolTip("Number of games for the training phase.")
        self.button_reset = QPushButton("Reset")
        self.button_reset.pressed.connect(self.reset)
        self.button_ga_learn = QPushButton("RL learn")
        self.button_ga_learn.pressed.connect(self.ga_learn)
        self.button_ga_play = QPushButton("RL play")
        self.button_ga_play.pressed.connect(self.ga_play)
        self.winrate = QLabel()
        self.winrate.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        #f = self.winrate.font()
        #f.setPointSize(10)
        #f.setWeight(75)
        #self.winrate.setFont(f)
        #self.winrate.setText("0%")
        #self.winrate_text = QLabel("Win rate : ")
        self.pbar = QProgressBar()
        self.pbar.setValue(0)
        self.pbar.hide()

        #hb.addWidget(self.score_text)
        #hb.addWidget(self.score)
        #hb.addWidget(self.winrate_text)
        #hb.addWidget(self.winrate)
        hb0.addWidget(self.cb)
        hb0.addWidget(self.button_reset)
        hb1.addWidget(self.button_ga_learn)
        hb1.addWidget(self.button_ga_play)
        vb.addLayout(hb0)
        vb.addLayout(hb1)
        vb.addLayout(hb)
        self.grid = QGridLayout()
        self.grid.setSpacing(5)
        vb.addLayout(self.grid)
        w.setLayout(vb)
        vb.addWidget(self.pbar)
        self.setCentralWidget(w)

        self.init_map()
        self.update_status(STATUS_READY)
        self.reset_map()
        self.update_status(STATUS_READY)

        self.show()
        self.setFixedSize(self.size())
        self.status_solving = False

    def init_map(self):
        """
        Init the board and connect signal of each tile to the correct function
        """
        global LEVEL, CURRENT_REVEALED, SCORE
        # Add positions to the map
        for x in range(0, self.b_size):
            for y in range(0, self.b_size):
                tile = Tile(x, y, LEVEL)
                self.grid.addWidget(tile, y, x)
                # Connect signal to handle expansion.
                #tile.clicked.connect(self.trigger_start)
                tile.ohno.connect(self.game_over)
                #tile.score.connect(self.update_score)
                #tile.manual.connect(self.update_manual)

    def reset_map(self):
        """
        Reset all the board, choose random positions for mine and give new value to each tiles
        """
        global SCORE, CURRENT_REVEALED
        # Clear all mine positions
        i = 0
        for x in range(0, self.b_size):
            for y in range(0, self.b_size):
                tile = self.grid.itemAtPosition(y, x).widget()
                tile.reset()
                tile.set_value(-i)
                i+=1

        tile = self.grid.itemAtPosition(0, 0).widget()
        tile.mark(-1)
        tile.reveal()
        tile.is_start = True
        tile.set_value(0)

        tile = self.grid.itemAtPosition(self.b_size-1, self.b_size-1).widget()
        tile.mark(1)
        tile.reveal()
        tile.is_end = True
        tile.set_value(self.b_size*self.b_size*2)

    def get_tiles_value(self):
        """
        Return the matrix of all the tile's value on the board
        """
        value_mat = np.zeros((self.b_size, self.b_size))
        for x in range(0, self.b_size):
            for y in range(0, self.b_size):
                tile = self.grid.itemAtPosition(y, x).widget()
                value_mat[x, y] = tile.get_value()
        return value_mat

    def get_tiles_revealed_value(self):
        """
        Return the matrix of the tile's value known on the board
        """
        value_mat = np.zeros((self.b_size, self.b_size))
        for x in range(0, self.b_size):
            for y in range(0, self.b_size):
                tile = self.grid.itemAtPosition(y, x).widget()
                if(tile.is_revealed):
                    if(tile.get_value()==-2): # Si start position
                        value_mat[x,y]=0
                    else:
                        value_mat[x,y]= tile.get_value()
                else:
                    value_mat[x,y]= -1
        return value_mat

    def get_surrounding_revealed(self, x, y):
        lst = []
        for i in range(-1,2):
            for j in range(-1, 2):
                if((i,j)not in [(-1,1), (1,1), (1,-1), (-1,-1), (0,0)]):
                    if(self.grid.itemAtPosition(y+i, x+j) != None):
                        tile = self.grid.itemAtPosition(y+i, x+j).widget()
                    else:
                        tile = None
                    lst.append(tile)
        return lst

    def get_pos_of_revealed(self):
        """
        Return a list of all the tile's positions
        """
        lst_revealed = []
        for x in range(0, self.b_size):
            for y in range(0, self.b_size):
                tile = self.grid.itemAtPosition(y, x).widget()
                if(tile.is_revealed):
                    lst_revealed.append((x, y))
        return lst_revealed

    def get_revealed_tiles(self):
        """
        Return the matrix of all the tile's positions
        """
        lst_revealed = []
        for x in range(0, self.b_size):
            for y in range(0, self.b_size):
                tile = self.grid.itemAtPosition(y, x).widget()
                if tile.is_revealed:
                    lst_revealed.append(tile)
        return lst_revealed

    def reset(self):
        """
        Reset all the global value and the board
        """
        self.reset_map()
        self.show()

    def reveal_map(self):
        """
        Reveal all the tiles on the board
        """
        for x in range(0, self.b_size):
            for y in range(0, self.b_size):
                tile = self.grid.itemAtPosition(y, x).widget()
                tile.reveal()

    def trigger_start(self, *args):
        """
        Start the game and update the current status
        """
        if self.status != STATUS_PLAYING:
            self.update_status(STATUS_PLAYING)

    def update_status(self, status):
        """
        Update the current status of the player
        """
        self.status = status

    def get_status(self):
        """
        Return the current status
        """
        return self.status

    def game_over(self):
        """
        Code execute when a tile emit the 'ohno' signal which end the game and restart a new one
        """
        #self.reveal_map()
        #self.update_status(STATUS_FAILED)
        pass
        #self.reset_map()


    def get_number_of_play(self):
        """
        Get the number of games to play
        """
        index = self.cb.currentIndex()
        if(index==0):
                return 100
        elif(index==1):
                return 200
        elif(index==2):
                return 500
        elif(index==3):
                return 1000

    def update_pbar(self, value, reset=False):
        """
        Update the progress bar while doing training/playing

        Parameters
        ----------
        value : int
            value to add to the progress bar
        reset : bool
            if True reset the progress bar
        """
        if(not reset):
            self.pbar.show()
            self.pbar.setValue(int(value))
        else:
            self.pbar.setValue(0)
            self.pbar.hide()

    def reset_tiles(self, nb_episode):
        # Reset color
        for tiles in self.get_revealed_tiles():
            if(not tiles.is_end and not tiles.is_start):
                tiles.mark(4)
            if(tiles.is_food):
                tiles.mark(5)
            tiles.reset_gradient()
            tiles.set_nb_play(nb_episode)

    def color_tiles(self, already_visited, next_tile, train):
        for tiles in already_visited:
            if(not tiles.is_end and not tiles.is_start and not tiles.is_food):
                '''
                if(train):
                    tiles.mark(2)
                else:
                    tiles.mark(6)
                '''
                tiles.mark(2)
            if(tiles.is_end):
                tiles.mark(1)
            if(tiles.is_start):
                tiles.mark(20)
        if(not next_tile.is_end and not next_tile.is_start  and not next_tile.is_food):
            '''
            if(train):
                next_tile.mark(3)
            else:
                next_tile.mark(7)
            '''
            next_tile.mark(3)
        if(next_tile.is_end):
            next_tile.mark(0)
        if(next_tile.is_start):
            next_tile.mark(8)

# ===============================================================================
# REINFORCEMENT LEARNING
# ===============================================================================
    def ga_save(self):
        with open('model/q_agent.pickle', 'wb') as config_agent:
            pickle.dump(self.agent, config_agent)

    def ga_learn(self):
        """
        Create a new RL agent and train it
        """
        alpha = 0.1; epsilon_max = 0.95; epsilon_min = 0.1; epsilon_decay = 0.99; gamma = 0.9
        self.agent = QAgent(alpha, epsilon_max, epsilon_min, epsilon_decay, gamma)
        self.run_episode(True, self.get_number_of_play())
        self.ga_save()

    def ga_play(self):
        """
        if self.agent == None:
            with open('model/q_agent.pickle', 'rb') as config_agent:
                self.agent = pickle.load(config_agent)
        """
        self.run_episode(False, 1)

    def run_episode(self, train, episode):
        if(train):
            self.reset_tiles(episode)
        for i in range(0, episode):
            self.update_pbar(i/episode*100, False)
            already_visited = []
            cur_x, cur_y = 0, 0
            running = True
            while(running):
                QApplication.processEvents()
                cur_tile = self.grid.itemAtPosition(cur_y, cur_x).widget()
                lst_surrounding = self.get_surrounding_revealed(cur_x, cur_y)
                observation = []
                for j in range(0, len(lst_surrounding)):
                    if(lst_surrounding[j]==None):
                        observation.append(-10) # Out of the map
                    else:
                        observation.append(lst_surrounding[j].get_value())

                action = self.agent.act(observation, train)
                next_tile = lst_surrounding[action-1]

                if(next_tile != None and next_tile.is_revealed):
                    already_visited.append(next_tile)
                    cur_x, cur_y = next_tile.get_pos()
                    lst_surrounding = self.get_surrounding_revealed(cur_x, cur_y)
                    observation_next = []
                    for j in range(0, len(lst_surrounding)):
                        if(lst_surrounding[j]==None):
                            observation_next.append(-10) # Out of the map
                        else:
                            observation_next.append(lst_surrounding[j].get_value())
                    _ = self.agent.act(observation_next, train)
                    if(cur_tile.is_start):
                        rew = -10
                    else:
                        rew = cur_tile.get_value()
                    if(train):
                        if(rew==self.b_size*self.b_size*2):
                            self.agent.learn(observation, observation_next, action, rew, True)
                            running = False
                        else:
                            self.agent.learn(observation, observation_next, action, rew, False)
                    else:
                        time.sleep(0.1)
                        #print("Action")
                        if(self.grid.itemAtPosition(cur_y, cur_x).widget().is_end):
                            break
                    self.color_tiles(already_visited, next_tile, train)
        self.update_pbar(0, True)
        #print(self.agent.q_table)


# ===============================================================================
# INIT WINDOW AND STYLE
# ===============================================================================
if __name__ == '__main__':
    app = QApplication([])
    app.setStyle("Fusion")
    app.setFont(QFont('SansSerif', 8))
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
    palette.setColor(QPalette.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ToolTipBase, QColor(0, 0, 0))
    palette.setColor(QPalette.ToolTipText, QColor(255, 255, 255))
    palette.setColor(QPalette.Text, QColor(255, 255, 255))
    palette.setColor(QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ButtonText, QColor(255, 255, 255))
    palette.setColor(QPalette.BrightText, QColor(200, 50, 20))
    palette.setColor(QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Highlight, QColor(218, 218, 218))
    palette.setColor(QPalette.HighlightedText, QColor(0, 0, 0))
    app.setPalette(palette)
    window = MainWindow()
    app.exec_()
