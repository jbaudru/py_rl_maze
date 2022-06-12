from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtCore import QObject, QThread, pyqtSignal

#===============================================================================
# GLOBAL VARIABLES
#===============================================================================
IMG_AGENT = QImage("./images/agent.png")

STATUS_READY = 0
STATUS_PLAYING = 1
STATUS_FAILED = 2
STATUS_SUCCESS = 3

COUNT = 1
COUNT_F = 10

#===============================================================================
# TILE OF BOARD AND ASSOCIATED FUNCTION
#===============================================================================
"""
Class use to represent title on the Minesweeper board
"""
class Tile(QWidget):
    expandable = pyqtSignal(int, int)
    clicked = pyqtSignal()
    ohno = pyqtSignal()
    score = pyqtSignal()
    manual = pyqtSignal()

    """
    Initialize the board, choose the size base on the LEVELS selected
    """
    def __init__(self, x, y, level, *args, **kwargs):
        super(Tile, self).__init__(*args, **kwargs)
        screen_size = QApplication.primaryScreen().availableSize()
        self.tilesize = screen_size.height() // (level[0]*2)
        self.setFixedSize(QSize(self.tilesize, self.tilesize))
        self.x = x
        self.y = y
        self.max = 0
        self.boardsize = level

    """
    Reset the boolean flag of a tile
    """
    def reset(self):
        global COUNT
        COUNT_F = 10
        COUNT = 1
        self.is_start = False
        self.is_end = False
        self.value = 0
        self.is_revealed = False
        self.count = 0
        self.marked = False
        self.is_food = False
        self.gradient = 1
        self.nb_play = 100
        self.update()

    def reset_gradient(self):
        self.gradient = 1


    def set_nb_play(self, nb):
        self.nb_play = nb
    """
    Drawing stuff about the tile
    """
    def paintEvent(self, event):
        global COUNT
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = event.rect()
        if self.is_revealed:
            color = self.palette().color(QPalette.Background)
            outer, inner = color, color
            if self.marked:
                if self.type == 1:
                    outer, inner = QColor('#1261b5'), QColor('#1261b5')
                elif self.type == 0:
                    outer, inner = QColor('white'), QColor('#1261b5')
                elif self.type == 2:
                    if(self.gradient<255):
                        self.gradient += (255/(self.nb_play*self.boardsize[0]*self.boardsize[0]))
                    outer, inner = QColor(70, 181, 18, self.gradient), QColor(70, 181, 18, self.gradient)
                elif self.type == 3:
                    if(self.gradient<255):
                        self.gradient += (255/(self.nb_play*self.boardsize[0]*self.boardsize[0]))
                    outer, inner = QColor('white'), QColor(70, 181, 18, self.gradient)
                elif self.type == 4:
                    outer, inner = QColor(53, 53, 53), QColor(53, 53, 53)
                elif self.type == 5:
                    outer, inner = QColor('#b57012'), QColor('#b57012')
                elif self.type == 6:
                    outer, inner = QColor(70, 181, 18), QColor(70, 181, 18)
                elif self.type == 7:
                    outer, inner = QColor('white'), QColor(70, 181, 18)
                elif self.type == 8:
                    outer, inner = QColor('white'), QColor('#b51248')
                else:
                    outer, inner = QColor('#b51248'), QColor('#b51248')
        else:
            outer, inner = QColor('#202020'), QColor('#202020')
        p.fillRect(r, QBrush(inner))
        pen = QPen(outer)
        pen.setWidth(7)
        p.setPen(pen)
        p.drawRect(r)
        if self.is_revealed:
            """
            if self.marked:
                if self.type == 3:
                    p.drawPixmap(r, QPixmap(IMG_AGENT))
            """
            pen = QPen(QColor('white'))
            pen.setWidth(1)
            p.setPen(pen)
            f = p.font()
            f.setBold(True)
            p.setFont(f)
            p.drawText(r, Qt.AlignHCenter | Qt.AlignVCenter, str(self.value))

    """
    Put a flag (=marker) on a tile to point out a mine (right click)
    """
    def flag(self):
        self.is_flagged = True
        self.update()
        #self.clicked.emit()

    """
    Return the value of the tile
    """
    def get_value(self):
        return self.value

    def set_value(self, val):
        self.value = val

    def get_pos(self):
        return self.x, self.y

    """
    Reveal the tiles
    """
    def reveal(self):
        self.is_revealed = True
        self.update()

    """
    Manage the actions caused by a click on a tile
    """
    def click(self):
        global COUNT
        if not self.is_revealed:
            self.reveal()
            self.set_value(0)
            #self.set_value(COUNT)
            #COUNT+=1

    def food(self):
        global COUNT_F
        self.is_food = True
        if not self.is_revealed:
            self.reveal()
            self.mark(5)
            #self.set_value(COUNT_F)
            self.set_value(-self.boardsize[0]*self.boardsize[0])
            #COUNT_F += 10

    """
    Handle the mouse action on a tile
    """
    def mouseReleaseEvent(self, e):
        self.manual.emit()
        if (e.button() == Qt.RightButton and not self.is_revealed):
            self.food()
        elif (e.button() == Qt.LeftButton):
            self.click()
            #if self.is_end:
            #    self.ohno.emit() # Win
        #self.score.emit()

    def get_mark(self):
        return self.type

    def is_marked(self):
        return self.marked

    def add_neighbors(self, neighbors):
        self.neighbors = set(neighbors)

    def mark(self, type):
        self.marked = True
        self.type = type
        self.update()

    def unmark(self):
        self.marked = False
        self.type = None
        self.update()

    def __hash__(self):
        return hash((self.x, self.y))

    def __eq__(self, other):
        if other is None:
            return False
        if isinstance(other, Tile):
            return (self.x, self.y) == (other.x, other.y)
        return (self.x, self.y) == (other[0], other[1])

    def __ne__(self, other):
        return not(self == other)

    def __str__(self):
        return"({0}, {1})".format(self.x, self.y)
