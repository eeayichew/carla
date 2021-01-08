"""
This module is how to setup a sample experiment.
"""
import numpy as np
from gym.spaces import Box
import cv2

from experiments.base_experiment import *
from helper.CarlaHelper import update_config
import carla
import matplotlib.pyplot as plt
import random
import gc

SERVER_VIEW_CONFIG = {
}

SENSOR_CONFIG = {
    "SENSOR": [SensorsEnum.CAMERA_RGB],
    "SENSOR_TRANSFORM": [SensorsTransformEnum.Transform_A],
    "CAMERA_X": 84,
    "CAMERA_Y": 84,
    "CAMERA_FOV": 60,
    "CAMERA_NORMALIZED": [True],
    "FRAMESTACK": 2,
}


OBSERVATION_CONFIG ={
    "CAMERA_OBSERVATION": [True]
}

EXPERIMENT_CONFIG = {
    "OBSERVATION_CONFIG": OBSERVATION_CONFIG,
    "Server_View": SERVER_VIEW_CONFIG,
    "SENSOR_CONFIG": SENSOR_CONFIG,
    "number_of_spawning_actors": 0,
    "server_map": "Town02",
    "start_pos_spawn_id": 95,
    "end_pos_spawn_id": 34,
    "Debug":False,
}


def preprocess_image(x_res,y_res,image):
    # This of course is just a sample. For more than one image, it must be changed accordingly.
    data = np.asarray(image[0])
    data = cv2.resize(data, (x_res, y_res), interpolation=cv2.INTER_AREA)
    data = (data.astype(np.float32) - 128) / 128
    return data


def plot_observation_space(obs):
    #https://stackoverflow.com/questions/279561/what-is-the-python-equivalent-of-static-variables-inside-a-function
    if not hasattr(plot_observation_space, "counter"):
        plot_observation_space.counter = 0  # it doesn't exist yet, so initialize it
    plot_observation_space.counter += 1

    plt.close()
    data = obs[:, :, 0:3]
    plt.subplot(211)
    plt.imshow(((data * 128) + 128).astype("uint8"))
    data = obs[:, :, 3:6]
    plt.subplot(212)
    plt.imshow(((data * 128) + 128).astype("uint8"))



class Experiment(BaseExperiment):
    def __init__(self):
        config=update_config(BASE_EXPERIMENT_CONFIG, EXPERIMENT_CONFIG)
        super().__init__(config)
        self.prev_image = None
        self.previous_distance = None
        self.start_location = None
        self.end_location = None


    def set_observation_space(self):
        num_of_channels = 3

        image_space = Box(
            low=-1.0,
            high=1.0,
            shape=(
                self.experiment_config["SENSOR_CONFIG"]["CAMERA_X"],
                self.experiment_config["SENSOR_CONFIG"]["CAMERA_Y"],
                num_of_channels * self.experiment_config["SENSOR_CONFIG"]["FRAMESTACK"],
            ),
            dtype=np.float32,
        )
        self.observation_space = image_space

    def process_observation(self, core, observation):
        """
        Process observations according to your experiment
        :param core:
        :param observation:
        :return:
        """
        self.set_server_view(core)
        image = preprocess_image(self.experiment_config["SENSOR_CONFIG"]["CAMERA_X"],
                                 self.experiment_config["SENSOR_CONFIG"]["CAMERA_Y"],
                                 observation['camera'])

        assert self.experiment_config["SENSOR_CONFIG"]["FRAMESTACK"] in [1, 2]

        prev_image = self.prev_image
        self.prev_image = image

        if prev_image is None:
            prev_image = image
        if self.experiment_config["SENSOR_CONFIG"]["FRAMESTACK"] == 2:
            image = np.concatenate([prev_image, image], axis=2)

        if self.experiment_config["Debug"] and 0:
            plot_observation_space(image)
        return image

    def initialize_reward(self, core):
        """
        Generic initialization of reward function
        :param core:
        :return:
        """
        self.previous_distance=0


    def compute_reward(self, core, observation):
        """
        Reward function
        :param observation:
        :param core:
        :return:
        """
        c = float(np.sqrt(np.square(self.hero.get_location().x - self.start_location_x) + \
                            np.square(self.hero.get_location().y - self.start_location_y)))
        # if c > self.previous_distance + 1e-2:
        #     reward = 1
        # else:
        #     reward = 0

        # # print("\n", self.previous_distance)
        # self.previous_distance = c
        # # print("\n", c)

        # if c > 20:
        #     self.base_x = self.hero.get_location().x
        #     self.base_y = self.hero.get_location().y
        #     print("Reached the milestone!")

        if self.observation["collision"]!=False:
            reward = -0.002*self.observation["collision"]
        elif self.observation["lane"]!=False:
            reward = -10*(self.observation["lane"])
        elif (self.get_speed() > self.hero.get_speed_limit()):
            reward = 0.1*(self.hero.get_speed_limit() - self.get_speed())
        elif c > self.previous_distance + 1e-2:
            reward = c - self.previous_distance
        else:
            reward = 0
        self.previous_distance = c
        return reward

    def spawn_hero(self, core, transform, autopilot=False):

        world = core.get_core_world()
        self.spawn_points = world.get_map().get_spawn_points()
        gc.collect()
        self.hero_blueprints = world.get_blueprint_library().find(self.hero_model)
        self.hero_blueprints.set_attribute("role_name", "hero")

        random.shuffle(self.spawn_points, random.random) #comment this for debugging
        next_spawn_point = self.spawn_points[0]

        super().spawn_hero(core, next_spawn_point, autopilot=False)
        world.tick()
        print("Hero spawned!")
        self.start_location_x = self.spawn_points[0].location.x
        self.start_location_y = self.spawn_points[0].location.y

    # def set_server_view(self, core):

    #     """
    #     Apply server view to be in the sky between camera between start and end positions
    #     :param core:
    #     :return:
    #     """
    #     # spectator pointing to the sky to reduce rendering impact

    #     server_view_x = (
    #             self.experiment_config["Server_View"]["server_view_x_offset"]
    #             + (self.start_location.location.x + self.end_location.location.x) / 2
    #     )
    #     server_view_y = (
    #             self.experiment_config["Server_View"]["server_view_y_offset"]
    #             + (self.start_location.location.y + self.end_location.location.y) / 2
    #     )
    #     server_view_z = self.experiment_config["Server_View"]["server_view_height"]
    #     server_view_pitch = self.experiment_config["Server_View"]["server_view_pitch"]

    #     world = core.get_core_world()
    #     self.spectator = world.get_spectator()
    #     self.spectator.set_transform(
    #         carla.Transform(
    #             carla.Location(x=server_view_x, y=server_view_y, z=server_view_z),
    #             carla.Rotation(pitch=server_view_pitch),
    #         )
    #     )