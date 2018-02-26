import sys
import time
import random

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from map_view import *
from world_app_utils import *

_MAP_AXIS_SIZE = 512
_MAP_SCALE_CONSTANT = 1

class WorldWindow(QMainWindow):

  def __init__(self):
    super().__init__()
    self.setWindowTitle("World Simulator")
    self.num_turns = 0
    ''' Widgets '''
    self.central_widget = QWidget()
    self.load_widget = QWidget()
    self.main_map_widget = QWidget()
    self.pause_continue_widget = QWidget()

    ''' High level layouts '''
    self.stacked_layout = QStackedLayout()
    self.stacked_layout.addWidget(self.load_widget)

    self.loadscreen_layout = QVBoxLayout()
    self.load_widget.setLayout(self.loadscreen_layout)

    self.simulation_grid = QGridLayout()
    self.pause_continue_grid = QGridLayout()

    ''' Input fields '''
    self.map_textbox = QLineEdit(self)

    ''' Buttons and shit '''
    self.load_map_button = QPushButton('Load this map', self)
    self.load_map_button.clicked.connect(self.load_map_on_click)

    ''' Other values '''
    self.simulation_state_paused = False

    self.central_widget.setLayout(self.stacked_layout)
    self.setCentralWidget(self.central_widget)
    self.load_map()



  ## Starting the main simulation loop ##
  def start_simulation(self):
    self.start_simulation_button.setParent(None)
    self.pause_continue_grid.addWidget(self.continue_simulation_button, 0, 0)
    self.pause_continue_grid.addWidget(self.pause_simulation_button, 0, 1)

    self.pause_continue_widget.setLayout(self.pause_continue_grid)
    self.simulation_grid.addWidget(self.pause_continue_widget, 1, 0)
    self.main_map_widget.setLayout(self.simulation_grid)

    random_land = self.map_view.map_objects.engine_world.random_land()
    self.map_view.place_initial_population(random_land[0], random_land[1])
    self.run_simulation()

  def run_simulation(self):
    while not self.simulation_state_paused:
      self.num_turns += 1
      self.map_view.simulation_step()
      loop = QEventLoop()
      QTimer.singleShot(250, loop.quit)
      loop.exec_()

  def continue_simulation(self):
    if self.simulation_state_paused:
      self.simulation_state_paused = False
      self.run_simulation()
    else:
      pass

  def pause_simulation(self):
    self.simulation_state_paused = True
    print(str(self.map_view.map_objects.num_existing_populations()) + " populations in " + str(self.num_turns) + " turns")


  def load_map(self):
    ''' All the widget elements for the main map load view '''
    self.map_textbox.move(20, 20)
    self.map_textbox.resize(280,40)

    self.load_map_button.move(20, 80)

    ''' Set up all elements on screen '''
    self.loadscreen_layout.addWidget(self.map_textbox)
    self.loadscreen_layout.addWidget(self.load_map_button)

    self.show()


  def view_map(self, world_file):
    ''' Temporary; to be removed '''
    world_file = "map2503.world"

    ''' Initialize map_view class '''
    self.map_view = MapView(_MAP_AXIS_SIZE * _MAP_SCALE_CONSTANT, _MAP_AXIS_SIZE * _MAP_SCALE_CONSTANT, world_file)

    ''' Map view buttons '''
    self.start_simulation_button = QPushButton('Start simulation', self)
    self.continue_simulation_button = QPushButton('Continue', self)
    self.pause_simulation_button = QPushButton('Pause', self)

    self.start_simulation_button.clicked.connect(self.start_simulation)
    self.continue_simulation_button.clicked.connect(self.continue_simulation)
    self.pause_simulation_button.clicked.connect(self.pause_simulation)

    ''' Initialize map view and its parameter settings '''
    self.map_view.setHorizontalScrollBarPolicy(1)
    self.map_view.setVerticalScrollBarPolicy(1)
    self.map_view.setFixedHeight(_MAP_AXIS_SIZE * _MAP_SCALE_CONSTANT)
    self.map_view.setFixedWidth(_MAP_AXIS_SIZE * _MAP_SCALE_CONSTANT)

    self.simulation_grid.addWidget(self.map_view, 0, 0)
    self.simulation_grid.addWidget(self.start_simulation_button, 1, 0)
    self.main_map_widget.setLayout(self.simulation_grid)

    self.map_view.show()


  ''' `Load this map` button connector '''
  def load_map_on_click(self):
    world_file = self.map_textbox.text()
    if is_valid_world_file(world_file):
      self.view_map(world_file)
      self.stacked_layout.addWidget(self.main_map_widget)
      self.stacked_layout.setCurrentIndex(1)
    else:
      self.map_textbox.setText("Input file must end in '.world' ")

#####################################################################################################################
def main():
  world_simulation = QApplication(sys.argv)
  world_window = WorldWindow()
  world_window.show()
  world_window.raise_()
  return world_simulation.exec_()

if __name__ == "__main__":
  main()
