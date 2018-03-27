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
    self.random_gammas = generate_random_gammas(a=0.60, scale=2.5, size=1000)

    self.culture_colors = {}

    self.show_map()

    self.total_deaths = 0


  ############## MAP BUTTON EVENTS ##############

  def mousePressEvent(self, event):
    x = event.x()
    y = event.y()

    
  ############## ENTRY POINTS ##############

  '''  Performs one step of simulation  '''
  def simulation_step(self):
    self.show_map()
    self.show_populations()
    self.move_populations()

  ''' Should eventually have functionality for this to be called randomly OR from user action '''
  def place_initial_population(self, x, y):
    print("Population begins at: " + str(self.map_objects.tile_matrix[x][y].biome))
    self.original_x = x
    self.original_y = y
    founder_pop = Population(x, y, culture=Culture())
    self.culture_colors[founder_pop.culture.magic_word] = [random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)]
    self.map_objects.populations.append(founder_pop)
    self.map_objects.zero_one_matrix[x][y] = 1
    self.map_objects.tile_matrix[x][y].current_inhabitant = founder_pop
    self.update_crowdedness_values(founder_pop, is_increment=True)

  ''' Loads all populations onto the map sequentially '''
  def redraw_populations_from_culture(self):
    self.show_map()
    for pop in self.map_objects.populations:
      pop_pixmap = QPixmap(3, 3)
      culture_color = self.culture_colors[pop.culture.predominant_culture()]
      color = QColor(culture_color[0], culture_color[1], culture_color[2])
      pop_pixmap.fill(color)
      dot = QGraphicsPixmapItem(pop_pixmap, parent = self.map_graphics_item)
      dot.setPos(pop.x, pop.y)

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
      # color = QColor(51, 51, 204)
      # if (pop.is_weak()):
      #   color = QColor(255, 153, 0)
      # elif (pop.is_desperate()):
      #   color = QColor(233, 33, 45)
      color = QColor(0, 0, 0)
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
        ''' Handles a population death outside of its turn (by conflict) '''
        if (pop.is_dead()):
          self.handle_population_death(pop)
        else:
          ''' Simulates one turn of cultural evolution for the population '''
          self.one_turn_cultural_evolution(pop, self.return_pops_in_radius(pop.x, pop.y, constants.culture_diffusion_radius))

          ''' Updates adjacency values for both the old and new population positions '''
          self.remove_habitation_information(pop)
          (pop.x, pop.y) = self.find_new_population_location(pop)
          self.add_habitation_information(pop)
          self.update_health_for_pop(pop)

          ''' Handles a population death during its turn (by starvation, illness, chance, etc) '''
          if (pop.is_dead()):
            self.handle_population_death(pop)
          else:
            if pop.should_bud_new_pop():
              if num_populations < self.map_objects.max_populations:
                (x, y) = self.find_new_population_location(pop)

                if not (x, y) == (pop.x, pop.y):
                  child_culture = Culture(cultural_expressions=pop.culture.cultural_expressions)
                  self.culture_colors[child_culture.magic_word] = [random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)]
                  child_pop = Population(x, y, culture=child_culture)
                  self.map_objects.zero_one_matrix[child_pop.x][child_pop.y] = 1
                  self.map_objects.tile_matrix[child_pop.x][child_pop.y].current_inhabitant = child_pop
                  self.update_crowdedness_values(child_pop, is_increment=True)
                  self.new_populations.append(child_pop)
            self.new_populations.append(pop)

      self.map_objects.populations = self.new_populations


  def remove_habitation_information(self, pop):
    self.map_objects.zero_one_matrix[pop.x][pop.y] = 0
    self.map_objects.tile_matrix[pop.x][pop.y].current_inhabitant = None          
    self.update_crowdedness_values(pop, is_increment=False)

  def add_habitation_information(self, pop):
    self.update_crowdedness_values(pop, is_increment=True)
    self.map_objects.zero_one_matrix[pop.x][pop.y] = 1
    self.map_objects.tile_matrix[pop.x][pop.y].current_inhabitant = pop   

  ''' Logic to handle the death of a population '''
  def handle_population_death(self, pop):
    self.update_crowdedness_values(pop, is_increment=False)
    self.map_objects.zero_one_matrix[pop.x][pop.y] = 0
    self.map_objects.tile_matrix[pop.x][pop.y].current_inhabitant = None    
    self.total_deaths += 1


  def update_health_for_pop(self, pop):
    current_tile = self.map_objects.tile_matrix[pop.x, pop.y]
    pop.update_health_from_crowdedness(current_tile.crowdedness, current_tile.carrying_capacity)
    pop.update_health_from_random(np.floor(np.random.choice(self.random_gammas, 1)*2)[0])
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
      radius = constants.default_pop_movement_radius

      random_x = x + random.randint(radius * -1, radius)
      random_y = y + random.randint(radius * -1, radius)
      if not self.map_objects.engine_world.is_ocean([random_x, random_y]) and not self.map_objects.tile_matrix[random_x, random_y].current_inhabitant:
        (x, y) = (random_x, random_y)
    elif pop.is_weak():
      (x, y) = self.sample_from_vicinity(current_tile, constants.weak_pop_movement_samples, constants.weak_pop_movement_radius)
    elif pop.is_desperate():
      (x, y) = self.sample_from_vicinity(current_tile, constants.desperate_pop_movement_samples, constants.desperate_pop_movement_radius)
    return (x, y)


  def sample_from_vicinity(self, tile, num_samples, radius):
    x = tile.x; y = tile.y
    lowest_crowdedness = tile.crowdedness
    for i in range(0, num_samples):
      random_x = tile.x + random.randint(radius * -1, radius)
      random_y = tile.y + random.randint(radius * -1, radius)
      random_crowdedness = self.map_objects.tile_matrix[random_x][random_y].crowdedness
      if random_crowdedness <= lowest_crowdedness and self.check_bounds(random_x, random_y) and not self.map_objects.engine_world.is_ocean([random_x, random_y]):
        lowest_crowdedness = random_crowdedness
        (x, y) = (random_x, random_y)
    return (x, y)     


  ############## CONFLICT ##############

  def simulate_conflict(self, pop):
    ## Eventually, we will check traits/personalities/histories to determine conflict, but for now we will not
    if not pop.is_dead():
      x = pop.x; y = pop.y
      current_tile = self.map_objects.tile_matrix[x, y]
      carrying_capacity_overflow = current_tile.crowdedness - current_tile.carrying_capacity

      if (carrying_capacity_overflow > 0):
        radius = pop.conflict_search_radius
        nearby_pops = self.return_pops_in_radius(x, y, radius)
        conflict_partner = self.choose_pop_for_conflict(pop, nearby_pops)
        if (conflict_partner):
          ''' Here we simulate the actual conflict '''
          do_conflict(pop, conflict_partner)


  def choose_pop_for_conflict(self, pop, nearby_pops):
    if (nearby_pops.size == 0):
      return None
    else:
      lowest_health = pop.health + pop.conflict_health_discrepancy_threshold
      best_pop = pop
      ## For now, just choosing the one with the lowest health (easiest target)
      for nearby_pop in nearby_pops:
        candidate_pop = self.map_objects.tile_matrix[nearby_pop[0], nearby_pop[1]].current_inhabitant
        if (candidate_pop == pop):
          continue
        elif (candidate_pop.health < lowest_health):
          lowest_health = candidate_pop.health
          best_pop = candidate_pop

      if (best_pop == pop):
        ''' Did not find a suitable population for conflict '''
        return None
      else:
        return best_pop


  ############## CULTURE ##############

  ''' 1st iteration - populations at different distances are given different "sway" amounts, and existing cultural
  expressions decay at fixed rates per turn '''
  def one_turn_cultural_evolution(self, pop, nearby_pops):
    pop_culture = pop.culture
    decay_per_pop = constants.culture_decay_rate / len(pop_culture.cultural_expressions)

    ''' If, after calculating decay, certain culture objects fall below zero, then the sum of all such underflows is
    added to the total for the recalibration step (thus, the total delta in cultural expression from one turn to the
    next can be greater than 2 * culture_decay_rate) '''
    culture_decay_underflow = 0.0
    temp_cultural_expressions = {}
    ''' Determine the cultural expression map after decay, and before recalibration '''
    for exp in pop_culture.cultural_expressions:
      new_expression_amt = pop_culture.cultural_expressions[exp] - decay_per_pop
      if new_expression_amt < 0.0:
        culture_decay_underflow += abs(new_expression_amt)
      else:
        temp_cultural_expressions[exp] = new_expression_amt

    delta_uptake = constants.culture_decay_rate - culture_decay_underflow
    total_neighboring_expressions = 0.0

    ''' Creates a dict to hold the relative values of all weighted cultural objects in the vicinity, and 
    immediately adds self to this dict '''
    new_cultural_expressions = {}
    new_cultural_expressions[pop_culture.magic_word] = constants.culture_home_sway

    ''' Go through each nearby pop and sum up all of the cultural expression points '''
    for nearby_pop_coords in nearby_pops:
      nearby_pop = self.map_objects.tile_matrix[nearby_pop_coords[0], nearby_pop_coords[1]].current_inhabitant
      if nearby_pop != pop:
        nearby_pop_expressions = nearby_pop.culture.cultural_expressions
        distance = max(abs(nearby_pop.x - pop.x), abs(nearby_pop.y - pop.y))

        ''' Populations further away have less impact on the culture, and the weighting reflects this '''
        cultural_uptake_weight = constants.culture_foreign_sway * ((constants.culture_diffusion_radius - distance + 1) / constants.culture_diffusion_radius)
        for key, value in nearby_pop_expressions.items():
          weighted_cultural_impact = value * cultural_uptake_weight
          if key in new_cultural_expressions:
            new_cultural_expressions[key] += weighted_cultural_impact
          else:
            new_cultural_expressions[key] = weighted_cultural_impact
          total_neighboring_expressions += weighted_cultural_impact

    cultural_uptake_multiplier = (total_neighboring_expressions + constants.culture_home_sway) / delta_uptake

    for key, value in new_cultural_expressions.items():
      cultural_uptake = value / cultural_uptake_multiplier
      if key in temp_cultural_expressions:
        temp_cultural_expressions[key] += cultural_uptake
      else:
        temp_cultural_expressions[key] = cultural_uptake

    ## TODO: The next 2 steps are hacky
    ''' Sanitizes the expressions mapping, removing negligible cultural associations '''
    to_remove = [k for (k, v) in temp_cultural_expressions.items() if v < 0.005]
    amt_removed = 0
    for key in to_remove:
      amt_removed += temp_cultural_expressions[key]
      del temp_cultural_expressions[key]

    ''' Recalibrates expression map to sum to 1 '''
    recalibration_multiplier = 1.0 / (1.0 - amt_removed)
    for key, value in temp_cultural_expressions.items():
      temp_cultural_expressions[key] = value * recalibration_multiplier

    pop_culture.cultural_expressions = temp_cultural_expressions


  ############## MAP VIEW UTILITIES ##############
  def check_bounds(self, x, y):
    return x >= 0 and x < self.map_width and y >= 0 and y < self.map_height

  def in_bounds(self, index, axis):
    if (index == 0):
      return max(0, min(self.map_width-1, index))
    else:
      return max(0, min(self.map_height-1, index))

  ''' Gets a 2D array of all populations within a given radius '''
  def return_pops_in_radius(self, x, y, radius):
    min_x = self.in_bounds(x-radius, 0); max_x = self.in_bounds(x+radius, 0)
    min_y = self.in_bounds(y-radius, 0); max_y = self.in_bounds(y+radius, 0)
    nearby_pops = np.transpose(np.nonzero(self.map_objects.zero_one_matrix[min_x:max_x+1, min_y:max_y+1]))
    nearby_pops += [min_x, min_y]
    return nearby_pops


  ############## PRINT UTILITIES (FOR TESTING!) ##############
  def print_all_culture_dicts(self):
    for pop in self.map_objects.populations:
      print("Pop with ID" + str(pop.unique_id) + " has cultural expressions: " + str(pop.culture.cultural_expressions))
      print("----------")
      print("-----")
      print("----------")

