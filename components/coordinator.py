import zmq
import carla

NUM_EXPECTED_CLIENTS = 3

context = zmq.Context()
socket = context.socket(zmq.ROUTER)
socket.bind("tcp://192.168.88.97:5555")

#!/usr/bin/env python

# Copyright (c) 2019 Intel Labs
#
# This work is licensed under the terms of the MIT license.
# For a copy, see <https://opensource.org/licenses/MIT>.

# Allows controlling a vehicle with a keyboard. For a simpler and more
# documented example, please take a look at tutorial.py.

"""
Welcome to CARLA manual control with steering wheel Logitech G29.

To drive start by preshing the brake pedal.
Change your wheel_config.ini according to your steering wheel.

To find out the values of your steering wheel use jstest-gtk in Ubuntu.

"""

from __future__ import print_function

import pygame

from components.display import HUD, SettingsMenu
from components.controller import SteeringwheelController, KeyboardController
from components.world import World
from components.communication import Client

import carla

import argparse
import logging
from components.recorder import recorder
import socket


# ==============================================================================
# -- game_loop() ---------------------------------------------------------------
# ==============================================================================


def game_loop(args):
    pygame.init()
    pygame.font.init()
    world = None
    try:
        client = carla.Client(args.host, args.port)
        client.set_timeout(5.0)

        display = pygame.display.set_mode(
            (args.width, args.height),
            pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.RESIZABLE | pygame.SCALED)

        # initialize steering wheel
        pygame.joystick.init()
        joystick_count = pygame.joystick.get_count()

        if joystick_count >= 1:
            joystick = pygame.joystick.Joystick(0)
            joystick.init()
            controller = SteeringwheelController(joystick, args)
            steering_config = (
                controller.steering_mode, controller.steering_sensitivity_min, controller.steering_sensitivity_max)
            if joystick_count > 1:
                raise ValueError("More than one joystick connected. Using joystick 0 as default.")
        else:
            controller = KeyboardController(False)
            steering_config = (0, 0.5, 0.5)  # Dummy config for keyboard controller

        original_settings = None
        
        
        sim_world = client.get_world()
        hud = HUD(args.width, args.height)
        settings_menu = SettingsMenu(display, steering_config)
        
        weather = carla.WeatherParameters(sun_altitude_angle=70.0)
        sim_world.set_weather(weather)

        if args.sync:
            original_settings = sim_world.get_settings()
            settings = sim_world.get_settings()

            if not settings.synchronous_mode:
                settings.synchronous_mode = True
                settings.fixed_delta_seconds = 1.0 / 20.0
            sim_world.apply_settings(settings)

        world = World(sim_world, hud, settings_menu, args)

        if args.sync:
            sim_world.tick()

        while True:
            ready_clients = {}
            ids = []
            while len(ready_clients) < NUM_EXPECTED_CLIENTS:
                ident, _, msg = socket.recv_multipart()
                if msg == b"READY":
                    ready_clients[ident] = True
                    ids.append(ident)
            
            for id in ids:
                socket.send_multipart([id, b"", b"OK"])

            world.tick()
            print(f"Ticked world @ frame {world.get_snapshot().frame}")

    finally:

        if original_settings:
            sim_world.apply_settings(original_settings)

        if world is not None:
            world.destroy()
        
        pygame.quit()
        print('\nCancelled by user. Bye!')

def main():
    argparser = argparse.ArgumentParser(
        description='CARLA Manual Control Client')
    argparser.add_argument(
        '-v', '--verbose',
        action='store_true',
        dest='debug',
        help='print debug information')
    argparser.add_argument(
        '--host',
        metavar='H',
        default='127.0.0.1',
        help='IP of the host server (default: 127.0.0.1)')
    argparser.add_argument(
        '-p', '--port',
        metavar='P',
        default=2000,
        type=int,
        help='TCP port to listen to (default: 2000)')
    argparser.add_argument(
        '-a', '--autopilot',
        action='store_true',
        help='enable autopilot')
    argparser.add_argument(
        '--res',
        metavar='WIDTHxHEIGHT',
        default='1920x1080',
        help='window resolution (default: 1920x1080)')
    argparser.add_argument(
        '--filter',
        metavar='PATTERN',
        default='vehicle.dodge.charger_2020',
        help='actor filter (default: "vehicle.*")')
    argparser.add_argument(
        '--save_folder',
        default='recordings',
        help='Folder path to save latency results and recordings')
    argparser.add_argument(
        '--sync',
        action="store_true",
        help='Enable sync to utilize multi GPU Carla setup')
    args = argparser.parse_args()

    args.width, args.height = [int(x) for x in args.res.split('x')]

    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(format='%(levelname)s: %(message)s', level=log_level)

    logging.info('listening to server %s:%s', args.host, args.port)

    game_loop(args)


if __name__ == '__main__':
    main()
