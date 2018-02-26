import sys
import random
import math
import numpy as np

from scipy.stats import gamma

def is_valid_world_file(filename):
  if filename.endswith(".world") or not filename:
    return True
  else:
    return False

def choose_random_coordinate_from_list(pop_list):
  return pop_list[np.random.randint(pop_list.shape[0], size=1), :]

def create_default_influence_grid(radius):
  side_length = (radius*2) + 1
  grid = np.ones((side_length, side_length), dtype=int)
  if radius < 3:
    return grid
  else:
    grid[radius-2:radius+2, radius-2:radius+2] = 3
    grid[radius-1:radius+1, radius-1:radius+1] = 5
    grid[radius, radius] = 0
    if not radius < 4:
      grid[radius-3:radius+3, radius-3:radius+3] = 2
    return grid

def generate_random_gammas(a, scale, size):
  return gamma.rvs(a=a, scale=scale, size=size)


''' Simulates the health impact of a conflict on two populations '''
def do_conflict(pop_1, pop_2, variance=2, average_conflict_total_hit_points=5):
  ## Initially will take the difference in health, divide by two, and set that to the mean
  ## Further iterations will take more variables into consideration when calculating strengths
  strength_1 = pop_1.health
  strength_2 = pop_2.health

  health_diff = pop_2.health - pop_1.health

  combat_result_differential = round(np.random.normal(health_diff, math.sqrt(variance)))
  combat_result_total = round(np.random.normal(average_conflict_total_hit_points, math.sqrt(variance)))

  ''' We don't want any population gaining health from combat '''
  pop_1_health_hit = max(0, (combat_result_total / 2.0) + combat_result_differential)
  pop_2_health_hit = max(0, (combat_result_total / 2.0) - combat_result_differential)
  print("Pop 1 health hit: " + str(pop_1_health_hit) + "; pop 2 health hit: " + str(pop_2_health_hit))

  pop_1.health -= pop_1_health_hit
  pop_2.health -= pop_2_health_hit



''' Gets the contribution of each trait to the RGB vector of the map image objects '''
def rgb_contributions(num_traits):
  ### RGB color scheme uses a 3-D vector with values in the range [0, 255]
  total_trait_contribution = 3.0 / num_traits
  contributions = np.zeros([num_traits, 3])
  r_filled, g_filled, b_filled = False, False, False
  for row in range(0, num_traits):
    u1 = random.uniform(0, total_trait_contribution)
    u2 = random.uniform(0, total_trait_contribution)
    r_contrib = (u1 - 0.0) if u1 < u2 else (u2 - 0.0)
    g_contrib = abs(u2 - u1)
    b_contrib = (total_trait_contribution - u1) if u1 > u2 else (total_trait_contribution - u2)
    print("R contrib: " + str(r_contrib)+ "; G contrib: " + str(g_contrib) + "; B contrib: " + str(b_contrib))
    if (sum(contributions[:, 0]) + r_contrib) > 1:
      overflow = (sum(contributions[:, 0]) + r_contrib) - 1
      r_contrib = r_contrib - overflow
      if not g_filled and not b_filled:
        g_contrib = g_contrib + (overflow / 2)
        b_contrib = b_contrib + (overflow / 2)
      elif not b_filled:
        b_contrib = b_contrib + overflow
      else:
        g_contrib = g_contrib + overflow
      r_filled = True

    if (sum(contributions[:, 1]) + g_contrib) > 1:
      overflow = (sum(contributions[:, 1]) + g_contrib) - 1
      g_contrib = g_contrib - overflow
      if not r_filled and not b_filled:
        r_contrib = r_contrib + (overflow / 2)
        b_contrib = b_contrib + (overflow / 2)
      elif not b_filled:
        b_contrib = b_contrib + overflow
      else:
        r_contrib = r_contrib + overflow
      g_filled = True

    if (sum(contributions[:, 2]) + b_contrib) > 1:
      overflow = (sum(contributions[:, 1]) + b_contrib) - 1
      b_contrib = b_contrib - overflow
      if not r_filled and not g_filled:
        g_contrib = g_contrib + (overflow / 2)
        r_contrib = r_contrib + (overflow / 2)
      elif not g_filled:
        g_contrib = g_contrib + overflow
      else:
        r_contrib = r_contrib + overflow
      b_filled = True

    print("R filled: " + str(r_filled)+ "; G filled: " + str(g_filled) + "; B filled: " + str(b_filled))
    contributions[row, 0] = r_contrib
    contributions[row, 1] = g_contrib
    contributions[row, 2] = b_contrib

  return contributions * 255