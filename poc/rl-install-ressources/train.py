#####################################################################################
#                            @Author: Tim Simon                                     #
#                            @Date: 22.01.26                                        #
#                            @Description:                                          #
#       The sweep.yaml is used for the parameter sweep agent by wandb               #
#       It includes the method of sweeping and what the goal of the sweep           #
#       In the command part we have to adjust the flags for training and            #
#       With all the parameters at the buttom.                                      #
#       NOTE: adding parameters here also needs to be done in train.py              #
#                                                                                   #
#####################################################################################

program: train.py
method: bayes
metric:
  name: reward
  goal: maximize

command:
  - ${env}
  - python
  - ${program}
  - ${args}
  - "--task=K1/ParameterWalk"
  - "--headless=true"
  - "--num_envs=4096"
  - "--sim_device=cuda:0"
  - "--rl_device=cuda:0"
  - "--max_iterations=2000"

parameters:
  learning_rate:
    min: 0.0001
    max: 0.005
    distribution: log_uniform_values

  tracking_lin_vel_x:
    min: 2.0
    max: 6.0
    distribution: uniform

  feet_slip_scale:
    min: -2.0
    max: -0.1
    distribution: uniform

  feet_air_time_scale:
    min: 1.0
    max: 5.0
    distribution: uniform
