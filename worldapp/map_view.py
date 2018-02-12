import sys
import time
import random

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from map_objects import *
from world_app_utils import *
from worldengine.hdf5_serialization import *

class MapView(QGraphicsView):

  def __init__(self, map_height, map_width, world_file):
    super().__init__()
    self.red_dot = QImage("red-square-hi.png").scaled(3, 3)
    self.map_objects = MapObjects(map_height, map_width, world_file, self.red_dot)
    self.map_image = QImage(self.map_objects.generated_file_name)
    self.pixmap = QPixmap.fromImage(self.map_image)

    self.show_map()


  ############## ENTRY POINTS ##############

  '''  Performs one step of simulation  '''
  def simulation_step(self):
    self.show_map()
    self.show_populations()
    self.move_populations()

  ''' Should eventually have functionality for this to be called randomly OR from user action '''
  def place_initial_population(self, x, y):
    founder_pop = Population(x, y)
    self.map_objects.populations.append(founder_pop)
    self.map_objects.tile_matrix[x][y].current_inhabitant = founder_pop


  ############## LOCALLY REFERENCED ##############

  ''' Re-loads map of the selected world at every step of the simulation '''
  def show_map(self):
    self.map_scene = QGraphicsScene(self)
    self.map_graphics_item = self.map_scene.addPixmap(self.pixmap)
    self.setScene(self.map_scene)    

  ''' Loads all populations onto the map sequentially '''
  def show_populations(self):
    for pop in self.map_objects.populations:
      pop_pixmap = QPixmap(3, 3)
      pop_pixmap.fill(QColor(233, 33, 45))
      dot = QGraphicsPixmapItem(pop_pixmap, parent = self.map_graphics_item)
      dot.setPos(pop.x, pop.y)

  ''' Iterates through population list to perform simulation events '''
  def move_populations(self):
    num_populations = len(self.map_objects.populations)
    self.new_populations = []
    if (num_populations == 0):
      random_land = self.map_objects.engine_world.random_land()
      self.place_initial_population(random_land[0], random_land[1])
    else:
      for pop in self.map_objects.populations:
        ## Check if death
        if pop.death_likelihood > random.uniform(0, 1):
          self.map_objects.tile_matrix[pop.x][pop.y].current_inhabitant = None
          ## We don't add to new populations list, thus removing it from the simulation
        else:
          ## Check if timer has popped
          if pop.budding_frequency_timer == 0:
            if num_populations < self.map_objects.max_populations:
              (x, y) = self.map_objects.find_new_population(pop.x, pop.y)
              child_pop = Population(x, y)
              self.new_populations.append(child_pop)
              self.map_objects.tile_matrix[child_pop.x][child_pop.y].current_inhabitant = child_pop
              pop.budding_frequency_timer = pop.budding_frequency_default
          else:
            pop.budding_frequency_timer = pop.budding_frequency_timer - 1

          ## Updates adjacency values for both the old and new population positions
          self.map_objects.tile_matrix[pop.x][pop.y].current_inhabitant = None          
          self.update_adjacency_values(pop, is_increment=False)
          (pop.x, pop.y) = self.map_objects.find_new_population(pop.x, pop.y)
          self.update_adjacency_values(pop, is_increment=True)
          self.map_objects.tile_matrix[pop.x][pop.y].current_inhabitant = pop

          self.new_populations.append(pop)
      self.map_objects.populations = self.new_populations


  def update_adjacency_values(self, population, is_increment):
    influence_range = population.influence_range
    starting_x = population.x
    starting_y = population.y
    for x in range(influence_range * -1, influence_range):
      if (starting_x + x) >= 0 and (starting_x + x) <= self.map_objects.width:
        for y in range(influence_range * -1, influence_range):
          if (starting_y + y) >= 0 and (starting_y + y) <= self.map_objects.height:
            tile = self.map_objects.tile_matrix[starting_x + x, starting_y + y]

            ## We only want the crowdedness value of the population's "home" tile to reflect information about
            # other populations, not the population (that resides on that tile) itself
            if not (x == 0 and y == 0):
              if is_increment:
                tile.crowdedness += population.influence_grid[x + influence_range, y + influence_range]
              else:
                tile.crowdedness -= population.influence_grid[x + influence_range, y + influence_range]


  ## Don't know whether this will be used, or whether other graphics will simply be superimposed onto the main pic
  def switch_scene(self, scene):
    self.setScene(scene)

