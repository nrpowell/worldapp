### Any and all constants used for the project

### Movement constants ###
default_pop_movement_radius = 2
weak_pop_movement_radius = 6
desperate_pop_movement_radius = 9

default_pop_movement_samples = 3
weak_pop_movement_samples = 5
desperate_pop_movement_samples = 15

weak_cutoff = 0.66
desperate_cutoff = 0.33


### Culture constants ###
''' These are initial rates, and eventually more important groups will have stronger sway than less important ones '''
culture_home_sway = 1
culture_foreign_sway = 0.5

culture_decay_rate = 0.05
culture_diffusion_radius = 7