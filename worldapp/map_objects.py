import sys
import numpy as np
import time
import random
import constants
import uuid

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from worldengine.cli.main import *
from world_app_utils import *

class Population(object):
  def __init__(self, x, y, budding_frequency_initial=12, influence_range=4,
    health_initial=7, max_health=10, growth_health_threshold=10, population_budding_timer=4,
    conflict_search_radius=2, conflict_health_discrepancy_threshold = 2, military_organization=1):
    self.unique_id = uuid.uuid4()

    self.x = x
    self.y = y
    self.name = ""

    self.influence_range = influence_range
    self.influence_grid = create_default_influence_grid(self.influence_range)

    self.budding_frequency_timer = budding_frequency_initial
    self.budding_frequency_default = budding_frequency_initial

    self.health = health_initial
    self.max_health = max_health
    self.growth_health_threshold = growth_health_threshold

    ## If the population is at full health for the number of turns reflected by the timer below, it buds a new pop
    self.full_health_timer = 0
    self.population_budding_timer = population_budding_timer

    self.conflict_search_radius = conflict_search_radius
    self.conflict_health_discrepancy_threshold = conflict_health_discrepancy_threshold

    self.military_organization = military_organization
    ####
    # Aggression impacts the likelihood of attacking other populations, of responding physically rather than diplomatically, and of forcibly expanding - even when the odds are not in your favor
    # Aggression is heightened initially by difficult environments and very scarce resources. Aggression also increases as inter-tribe conflict increases.
    # Aggression is lowered by the inverse of the above, but more rapidly when a society becomes organized, state-like, and peaceful
    #
    # Trusting impacts many advanced traits (like commerce), but in addition to that, if this trait successfully survives in populations, it much more easily results in sedentary populations and organization
    # Trusting is heightened by a history of peaceful exchange, by a relative lack in scarcity of resources and a more forgiving environment, and it experiences more growth the mor organization there is
    # Trusting is lowered when a population is outnumbered by enemies that are more advanced than they are
    #
    # Innovation has impacts in the early stages as well. It increases (somewhat) the carrying capacity of populations, decreases the rate at which they die, and can lead to the discovery of agriculture/fishing
    # Innovation requires relative peace and an easy environment
    # 
    # Honor is sort of a forerunner of later cultural class-based systems. Some academics will identify certain societies as more or less honor-driven (with the corollary being they are also shame-driven)
    # Honor 
    ####

    ## These can be viewed as 'tendencies towards' rather than as immutable characteristics
    self.basic_traits = {
      'aggression'    : 0.50,
      'trusting'      : 0.15,
      'innovation'    : 0.50,
      'honor'         : 0.50
    }

    ## These are traits that become relevant once we move towards sedentary communities
    self.advanced_traits = {
      'commerce'      : 0.50,
      'piety'         : 0.50
    }

  def __eq__(self, other):
    return self.unique_id == other.unique_id

  def update_influence_grid(self, new_radius):
    self.influence_grid = create_default_influence_grid(new_radius)
    self.influence_range = new_radius

  def update_growth_timer(self):
    if (self.health >= self.growth_health_threshold):
      self.full_health_timer += 1
    else:
      self.full_health_timer = 0

  def update_health_from_crowdedness(self, crowdedness, carrying_capacity):
    ## Crowdedness can take a negative value, in which case we decrement the population's health
    if (self.health + (carrying_capacity - crowdedness)) >= self.max_health:
      self.health = self.max_health
    else:
      self.health += (carrying_capacity - crowdedness)

  def update_health_from_random(self, health_hit):
    #print("Health hit is " + str(health_hit))
    self.health - health_hit

  def should_bud_new_pop(self):
    if self.full_health_timer >= self.population_budding_timer:
      self.full_health_timer = 0
      return True
    else:
      return False

  def is_healthy(self):
    return self.health > (constants.weak_cutoff * self.max_health)

  def is_weak(self): 
    if self.health <= (constants.weak_cutoff * self.max_health) and self.health > (constants.desperate_cutoff * self.max_health):
      #print("Population at X: " + str(self.x) + ", Y: " + str(self.y) + " is weak")
      return True
    else:
      return False

  def is_desperate(self):
    if self.health <= (constants.desperate_cutoff * self.max_health):
      #print("Population at X: " + str(self.x) + ", Y: " + str(self.y) + " is desperate")
      return True
    else:
      return False

  def is_dead(self):
    if self.health <= 0:
      #print("Population at X: " + str(self.x) + ", Y: " + str(self.y) + " has died")
      return True
    else:
      return False

###############################################################################################################
###############################################################################################################
###############################################################################################################

class Tile(object):
  def __init__(self, x, y, biome, width=1, height=1, carrying_capacity=2):
    self.x = x
    self.y = y
    self.x_diameter = width
    self.y_diameter = height

    self.biome = biome
    self.population_history = []

    ''' Measures how crowded this tile is for food, based on how adjacent various populations are to it '''
    self.crowdedness = 0

    self._carrying_capacity = carrying_capacity
    self._current_inhabitant = None


  ## Getters
  @property
  def current_inhabitant(self):
    return self._current_inhabitant

  @property
  def carrying_capacity(self):
    return self._carrying_capacity

  ## Setters
  @current_inhabitant.setter
  def current_inhabitant(self, val):
    self._current_inhabitant = val

  @carrying_capacity.setter
  def carrying_capacity(self, val):
    self._carrying_capacity = val

###############################################################################################################
###############################################################################################################
###############################################################################################################

class MapObjects():
  def __init__(self, map_width, map_height, world_file):
    self.populations = []
    self.max_populations = 1000
    self.width = map_width
    self.height = map_height

    ''' Loading world data and outputting relevant files '''
    self.engine_world = load_world(world_file)
    self.generated_file_name = "ancient_map_%s.png" % world_file[0:world_file.find(".world")]
    operation_ancient_map(self.engine_world, self.generated_file_name, 1, (142, 162, 179, 255), True, True, True, False)   
    biome_dict = {}

    ''' Simple matrix to keep track of the existence of populations within the map '''
    self.zero_one_matrix = np.zeros((self.width, self.height), dtype=int)

    ''' Matrix to keep track of more information related to the map tiles '''
    self.tile_matrix = np.empty((self.width, self.height), dtype=object)
    for x in range(0, map_width):
      for y in range(0, map_height):
        # biome_at = self.engine_world.layers['biome'].data[y, x]
        # if not biome_at in biome_dict:
        #   biome_dict[biome_at] = 1
        # else :
        #   biome_dict[biome_at] = biome_dict[biome_at] + 1
        self.tile_matrix[x, y] = Tile(x, y, self.engine_world.biome_at([x, y]))
    # for key, value in sorted(biome_dict.items()):
    #   print("Biome: " + str(key) + ", count: " + str(value))


  def num_existing_populations(self):
    return len(self.populations)


###############################################################################################################
###############################################################################################################
###############################################################################################################

# class SimulationConstants():
#     def __init__(self):
#       self.default_movement_radius = 2
#       self.weak_pop_movement_radius = 3
#       self.desperate_pop_movement_radius = 10

#       self.weak_pop_movement_samples = 5
#       self.desperate_pop_movement_samples = 20
