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
import evdev
from evdev import ecodes, InputDevice

from components.display import HUD, SettingsMenu
from components.controller import SteeringwheelController, KeyboardController
from components.game import World

import carla

import argparse
import logging


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

        # display = pygame.display.set_mode(
        #     (args.width, args.height),
        #     pygame.HWSURFACE | pygame.FULLSCREEN )

        # initialize steering wheel
        pygame.joystick.init()
        joystick_count = pygame.joystick.get_count()

        if joystick_count >= 1:
            joystick = pygame.joystick.Joystick(0)
            joystick.init()
            controller = SteeringwheelController(joystick)
            steering_config = (
                controller.steering_mode, controller.steering_sensitivity_min, controller.steering_sensitivity_max)
            if joystick_count > 1:
                raise ValueError("More than one joystick connected. Using joystick 0 as default.")
        else:
            controller = KeyboardController(False)
            steering_config = (0, 0.5, 0.5)  # Dummy config for keyboard controller

        hud = HUD(args.width, args.height)
        settings_menu = SettingsMenu(display, steering_config)
        world = World(client.get_world(), hud, settings_menu, args.filter)
        weather = carla.WeatherParameters(sun_altitude_angle=70.0)
        world.world.set_weather(weather)

        # TODO: force feedback adjust. Not working on G923.
        # device = evdev.list_devices()[0]
        # evtdev = InputDevice(device)
        # val = 20000  # val \in [0,65535]
        # evtdev.write(ecodes.EV_FF, ecodes.FF_AUTOCENTER, val)

        clock = pygame.time.Clock()
        while True:
            clock.tick_busy_loop(60)
            if controller.parse_events(world, clock):
                break
            if settings_menu.config_changed:
                controller.update_steering_config(settings_menu.get_steering_config())
                settings_menu.config_changed = False
            if settings_menu.config_save:
                controller.save_config_file()
                settings_menu.config_save = False
            world.tick(clock)
            world.render(display)
            pygame.display.flip()

    finally:
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
    args = argparser.parse_args()

    args.width, args.height = [int(x) for x in args.res.split('x')]

    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(format='%(levelname)s: %(message)s', level=log_level)

    logging.info('listening to server %s:%s', args.host, args.port)

    game_loop(args)


if __name__ == '__main__':
    main()
