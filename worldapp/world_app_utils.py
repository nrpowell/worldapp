import sys
import random
import numpy as np

def is_valid_world_file(filename):
  if filename.endswith(".world") or not filename:
    return True
  else:
    return False

def create_default_influence_grid(radius):
  side_length = (radius*2) + 1
  grid = np.ones((side_length, side_length), dtype=int)
  if radius < 3:
    return grid
  else:
    grid[radius-2:radius+2, radius-2:radius+2] = 2
    grid[radius-1:radius+1, radius-1:radius+1] = 3
    grid[radius, radius] = 0
    return grid

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