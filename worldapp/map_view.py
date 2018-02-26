import sys
import time
import random
import constants

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from map_objects import *
from world_app_utils import *
from worldengine.hdf5_serialization import *

class MapView(QGraphicsView):

  def __init__(self, map_height, map_width, world_file):
    super().__init__()
    self.map_width = map_width
    self.map_height = map_height
    self.map_objects = MapObjects(map_height, map_width, world_file)
    self.map_image = QImage(self.map_objects.generated_file_name)
    self.pixmap = QPixmap.fromImage(self.map_image)

    ## Pre-generates a set of gammas rv's for 
    self.random_gammas = generate_random_gammas(a=0.75, scale=1.33, size=1000)

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
    self.map_objects.zero_one_matrix[x][y] = 1
    self.map_objects.tile_matrix[x][y].current_inhabitant = founder_pop
    self.update_crowdedness_values(founder_pop, is_increment=True)


  ############## LOCALLY REFERENCED ONLY ##############

  ''' Re-loads map of the selected world at every step of the simulation '''
  def show_map(self):
    self.map_scene = QGraphicsScene(self)
    self.map_graphics_item = self.map_scene.addPixmap(self.pixmap)
    self.setScene(self.map_scene)    

  ''' Loads all populations onto the map sequentially '''
  def show_populations(self):
    for pop in self.map_objects.populations:
      pop_pixmap = QPixmap(3, 3)
      color = QColor(51, 51, 204)
      if (pop.is_weak()):
        color = QColor(255, 153, 0)
      elif (pop.is_desperate()):
        color = QColor(233, 33, 45)
      pop_pixmap.fill(color)
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
        #print("Pop health is: " + str(pop.health))
        ''' Will handle if pop was killed outside of its turn'''
        if (pop.is_dead()):
          self.handle_population_death(pop)
        else:
          ## Updates adjacency values for both the old and new population positions
          self.map_objects.zero_one_matrix[pop.x][pop.y] = 0
          self.map_objects.tile_matrix[pop.x][pop.y].current_inhabitant = None          
          self.update_crowdedness_values(pop, is_increment=False)
          (pop.x, pop.y) = self.find_new_population_location(pop)
          self.update_crowdedness_values(pop, is_increment=True)
          self.map_objects.zero_one_matrix[pop.x][pop.y] = 1
          self.map_objects.tile_matrix[pop.x][pop.y].current_inhabitant = pop

          self.update_health_for_pop(pop)

          ''' Will handle if pop was killed during its turn '''
          if (pop.is_dead()):
            self.handle_population_death(pop)
          else:
            if pop.should_bud_new_pop():
              # print("Budding new pop")
              if num_populations < self.map_objects.max_populations:
                (x, y) = self.find_new_population_location(pop)
                child_pop = Population(x, y)
                self.new_populations.append(child_pop)
                self.map_objects.zero_one_matrix[child_pop.x][child_pop.y] = 1
                self.map_objects.tile_matrix[child_pop.x][child_pop.y].current_inhabitant = child_pop
                self.update_crowdedness_values(child_pop, is_increment=True)
            self.new_populations.append(pop)

      self.map_objects.populations = self.new_populations

  ''' Logic to handle the death of a population '''
  def handle_population_death(self, pop):
    print("Population died")
    self.update_crowdedness_values(pop, is_increment=False)
    self.map_objects.zero_one_matrix[pop.x][pop.y] = 0
    self.map_objects.tile_matrix[pop.x][pop.y].current_inhabitant = None    


  def update_health_for_pop(self, pop):
    current_tile = self.map_objects.tile_matrix[pop.x, pop.y]
    #print("Crowdedness: " + str(current_tile.crowdedness) + "; capacity: " + str(current_tile.carrying_capacity))
    pop.update_health_from_crowdedness(current_tile.crowdedness, current_tile.carrying_capacity)
    pop.update_health_from_random(np.floor(np.random.choice(self.random_gammas, 1))[0])
    pop.update_growth_timer()
    self.simulate_conflict(pop)

  def update_crowdedness_values(self, population, is_increment):
    influence_range = population.influence_range
    starting_x = population.x
    starting_y = population.y
    for x in range(influence_range * -1, influence_range):
      if (starting_x + x) >= 0 and (starting_x + x) <= self.map_objects.width:
        for y in range(influence_range * -1, influence_range):
          if (starting_y + y) >= 0 and (starting_y + y) <= self.map_objects.height:
            tile = self.map_objects.tile_matrix[starting_x + x, starting_y + y]

            ## We only want the crowdedness value of the population's "home" tile to reflect information about
            # other populations, not about the population that resides on that tile itself
            if not (x == 0 and y == 0):
              if is_increment:
                tile.crowdedness += population.influence_grid[x + influence_range, y + influence_range]
              else:
                tile.crowdedness -= population.influence_grid[x + influence_range, y + influence_range]


  def find_new_population_location(self, pop):
    x = pop.x; y = pop.y
    current_tile = self.map_objects.tile_matrix[x, y]
    carrying_capacity_overflow = current_tile.crowdedness - current_tile.carrying_capacity

    if carrying_capacity_overflow < 0 or pop.is_healthy():
      radius = constants.default_movement_radius
      random_x = x + random.randint(radius * -1, radius)
      random_y = y + random.randint(radius * -1, radius)
      if not self.map_objects.engine_world.is_ocean([random_x, random_y]) and not self.map_objects.tile_matrix[random_x, random_y].current_inhabitant:
        (x, y) = (random_x, random_y)
    elif pop.is_weak():
      (x, y) = self.sample_from_vicinity(current_tile, constants.weak_pop_movement_samples, constants.weak_pop_movement_radius)
    elif pop.is_desperate():
      (x, y) = self.sample_from_vicinity(current_tile, constants.desperate_pop_movement_samples, constants.desperate_pop_movement_radius)
    #print("New X: " + str(x) + ", new Y: " + str(y))
    return (x, y)


  def sample_from_vicinity(self, tile, num_samples, radius):
    x = tile.x; y = tile.y
    lowest_crowdedness = tile.crowdedness
    for i in range(0, num_samples):
      random_x = tile.x + random.randint(radius * -1, radius)
      random_y = tile.y + random.randint(radius * -1, radius)
      random_crowdedness = self.map_objects.tile_matrix[random_x][random_y].crowdedness
      if random_crowdedness < lowest_crowdedness and self.check_bounds(random_x, random_y) and not self.map_objects.engine_world.is_ocean([random_x, random_y]):
        lowest_crowdedness = random_crowdedness
        (x, y) = (random_x, random_y)
    return (x, y)     


  ############## CONFLICT ##############

  def simulate_conflict(self, pop):
    ## Eventually, we will check traits/personalities/histories to determine conflict, but for now we will not
    x = pop.x; y = pop.y
    current_tile = self.map_objects.tile_matrix[x, y]
    carrying_capacity_overflow = current_tile.crowdedness - current_tile.carrying_capacity

    if (carrying_capacity_overflow > 0):
      radius = pop.conflict_search_radius

      ''' Gets a 2D array of all populations within a given radius '''
      nearby_pops = np.transpose(np.nonzero(self.map_objects.zero_one_matrix[self.in_bounds(x-radius, 0):self.in_bounds(x+radius, 0),
        self.in_bounds(y-radius, 1):self.in_bounds(y+radius, 1)]))

      conflict_partner = self.choose_pop_for_conflict(pop, nearby_pops)
      if (conflict_partner):
        ''' Here we simulate the actual conflict '''
        do_conflict(pop, conflict_partner)
        if (pop.is_dead()):
          handle_population_death(pop)
        if (conflict_partner.is_dead()):
          handle_population_death(conflict_partner)


  def choose_pop_for_conflict(self, pop, nearby_pops):
    if (nearby_pops.size == 0):
      # print("No nearby pops")
      return None
    else:
      lowest_health = pop.health + pop.conflict_health_discrepancy_threshold
      best_pop = pop
      ## For now, just choosing the one with the lowest health (easiest target)
      for nearby_pop in nearby_pops:
        candidate_pop = self.map_objects.tile_matrix[nearby_pop[0], nearby_pop[1]].current_inhabitant
        print("Zero one matrix has: " + str(self.map_objects.zero_one_matrix[nearby_pop[0], nearby_pop[1]]))
        if (candidate_pop.health < lowest_health):
          lowest_health = candidate_pop.health
          best_pop = candidate_pop

      if (best_pop == pop):
        # print("Could not find suitable pop")
        ''' Did not find a suitable population for conflict '''
        return None
      else:
        # print("Found suitable pop")
        return best_pop




  ############## MAP VIEW UTILITIES ##############
  def check_bounds(self, x, y):
    return x >= 0 and x < self.map_width and y >= 0 and y < self.map_height

  def in_bounds(self, index, axis):
    if (index == 0):
      return max(0, min(self.map_width-1, index))
    else:
      return max(0, min(self.map_height-1, index))

