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

import pygame
import pygame_menu
import os
import carla
import math
import datetime
from components.utils import get_actor_display_name
from components.recorder import recorder


class FadingText(object):
    def __init__(self, font, dim, pos):
        self.font = font
        self.dim = dim
        self.pos = pos
        self.seconds_left = 0
        self.surface = pygame.Surface(self.dim)

    def set_text(self, text, color=(255, 255, 255), seconds=2.0):
        text_texture = self.font.render(text, True, color)
        self.surface = pygame.Surface(self.dim)
        self.seconds_left = seconds
        self.surface.fill((0, 0, 0, 0))
        self.surface.blit(text_texture, (10, 11))

    def tick(self, _, clock):
        delta_seconds = 1e-3 * clock.get_time()
        self.seconds_left = max(0.0, self.seconds_left - delta_seconds)
        self.surface.set_alpha(500.0 * self.seconds_left)

    def render(self, display):
        display.blit(self.surface, self.pos)


class HelpText(object):
    def __init__(self, font, width, height):
        lines = __doc__.split('\n')
        self.font = font
        self.dim = (680, len(lines) * 22 + 12)
        self.pos = (0.5 * width - 0.5 * self.dim[0], 0.5 * height - 0.5 * self.dim[1])
        self.seconds_left = 0
        self.surface = pygame.Surface(self.dim)
        self.surface.fill((0, 0, 0, 0))
        for n, line in enumerate(lines):
            text_texture = self.font.render(line, True, (255, 255, 255))
            self.surface.blit(text_texture, (22, n * 22))
            self._render = False
        self.surface.set_alpha(220)

    def toggle(self):
        self._render = not self._render

    def render(self, display):
        if self._render:
            display.blit(self.surface, self.pos)


class SettingsButton(object):
    def __init__(self, width, height):
        self.font = pygame.font.SysFont('Corbel', 40)
        self.dim = (width, height)
        self.text_width = int(width / 10)
        self.text_height = int(height / 20)
        self.pos = (0, height - self.text_height)

        self.clickable = True

    def get_region(self):
        return self.pos[0], self.pos[1], self.text_width, self.text_height

    def render(self, display):
        # stores the (x,y) coordinates into
        # the variable as a tuple
        mouse = pygame.mouse.get_pos()

        # white color
        text_color = (255, 255, 255)

        # light shade of the button
        bg_color_light = (170, 170, 170)

        # dark shade of the button
        bg_color_dark = (100, 100, 100)

        x, y, w, h = self.get_region()

        # if mouse is hovered on a button it
        # changes to lighter shade
        # if width / 2 <= mouse[0] <= width / 2 + text_width and height / 2 <= mouse[1] <= height / 2 + text_height:
        if self.clickable and x <= mouse[0] <= x + w and y <= mouse[1] <= y + h:
            pygame.draw.rect(display, bg_color_light, [x, y, w, h], border_radius=int(h / 2))

        else:
            pygame.draw.rect(display, bg_color_dark, [x, y, w, h], border_radius=int(h / 2))

            # superimposing the text onto our button
        text = self.font.render('Settings', True, text_color)

        text_rect = text.get_rect(center=(x + w / 2, y + h / 2))

        display.blit(text, text_rect)


class SettingsMenu(object):
    def __init__(self, display, steering_config):
        self.display = display
        width, height = pygame.display.get_surface().get_size()
        self.settings_button = SettingsButton(width, height)
        self.menu = pygame_menu.Menu('Welcome', 400, 300,
                                     theme=pygame_menu.themes.THEME_BLUE)
        self.menu.add.toggle_switch('Steering Mode: ', default=steering_config[0], state_text=('Fixed', 'Adaptive'),
                                    onchange=self.mode_change)

        fixed_slider = self.menu.add.range_slider('Sensitivity: ', default=steering_config[1],
                                                  range_values=(0.2, 0.8), increment=0.05,
                                                  onchange=self.sensitivity_change)
        upper = 0.8 if steering_config[1] == steering_config[2] else steering_config[2]
        adaptive_slider = self.menu.add.range_slider('Sensitivity: ', default=(steering_config[1], upper),
                                                     range_values=(0.2, 0.8), increment=0.05,
                                                     onchange=self.sensitivity_change)
        self.sliders = [fixed_slider, adaptive_slider]
        self.sliders[1 - steering_config[0]].hide()
        self.menu.add.vertical_fill()
        self.menu.add.button('SAVE', self.toggle_menu, True)
        self.menu.add.button('CLOSE', self.toggle_menu, False)
        self.menu.disable()

        self.steering_config = list(steering_config)
        self.config_changed = False
        self.config_save = False

    def render(self, display):
        self.settings_button.render(display)
        if self.menu.is_enabled():
            self.menu.draw(display)

    def update_events(self, events):
        if self.menu.is_enabled():
            self.menu.update(events)

    def is_enabled(self):
        return self.menu.is_enabled()

    def toggle_menu(self, save):
        self.settings_button.clickable = not self.settings_button.clickable
        self.menu.toggle()
        self.config_save = save

    def mode_change(self, mode):
        self.steering_config[0] = 1 if mode else 0
        self.sliders[mode].show()
        self.sliders[1 - mode].hide()
        self.config_changed = True

    def sensitivity_change(self, values):
        if isinstance(values, tuple):
            self.steering_config[1] = values[0]
            self.steering_config[2] = values[1]
        else:
            self.steering_config[1] = values
            self.steering_config[2] = values
        self.config_changed = True

    def get_steering_config(self):
        return self.steering_config


class HUD(object):
    def __init__(self, width, height):
        self.dim = (width, height)
        # font = pygame.font.Font(pygame.font.get_default_font(), 20)
        font_name = 'courier' if os.name == 'nt' else 'mono'
        fonts = [x for x in pygame.font.get_fonts() if font_name in x]
        default_font = 'ubuntumono'
        mono = default_font if default_font in fonts else fonts[0]
        mono = pygame.font.match_font(mono)
        self._font_mono = pygame.font.Font(mono, 12 if os.name == 'nt' else 34)
        self._font_mono2 = pygame.font.Font(mono, 12 if os.name == 'nt' else 18)
        self._font_mono3 = pygame.font.Font(mono, 40 if os.name == 'nt' else 18)
        # self._notifications = FadingText(font, (width, 40), (0, height - 40))
        # self.help = HelpText(pygame.font.Font(mono, 24), width, height)
        self.server_fps = 0
        self.frame = 0
        self.simulation_time = 0
        self._info = dict()
        self._info_text = []
        self._server_clock = pygame.time.Clock()
        self.reverse = False

        self.display = None
        self.settings_button = SettingsButton(width, height)

    def on_world_tick(self, timestamp):
        self._server_clock.tick()
        self.server_fps = self._server_clock.get_fps()
        self.frame = timestamp.frame
        self.simulation_time = timestamp.elapsed_seconds

    def tick(self, world, clock):
        # self._notifications.tick(world, clock)
        t = world.player.get_transform()
        v = world.player.get_velocity()
        c = world.player.get_control()
        ang_v = world.player.get_angular_velocity()
        heading = 'N' if abs(t.rotation.yaw) < 89.5 else ''
        heading += 'S' if abs(t.rotation.yaw) > 90.5 else ''
        heading += 'E' if 179.5 > t.rotation.yaw > 0.5 else ''
        heading += 'W' if -0.5 > t.rotation.yaw > -179.5 else ''
        # colhist = world.collision_sensor.get_collision_history()
        # collision = [colhist[x + self.frame - 200] for x in range(0, 200)]
        # max_col = max(1.0, max(collision))
        # collision = [x / max_col for x in collision]
        vehicles = world.world.get_actors().filter('vehicle.*')
        self._info = dict()
        self._info['speed'] = '% 1.0f mph' % (0.621371 * 3.6 * math.sqrt(v.x ** 2 + v.y ** 2 + v.z ** 2))
        self._info['heading'] = u'%16s %8.0f\N{DEGREE SIGN}' % (heading, t.rotation.yaw)
        self._info['client_fps'] = '  Client:  % 1.0f FPS' % clock.get_fps()
        self._info['server_fps'] = '  Server:  % 1.0f FPS' % self.server_fps
        self._info['angular_velocity'] = '%15s %4.0f deg/s' % (
            heading, math.sqrt(ang_v.x ** 2 + ang_v.y ** 2 + ang_v.z ** 2))

        self._info_text = [
            'Server:  % 16.0f FPS' % self.server_fps,
            'Client:  % 16.0f FPS' % clock.get_fps(),
            '',
            'Vehicle: % 20s' % get_actor_display_name(world.player, truncate=20),
            'Map:     % 20s' % world.world.get_map().name.split('/')[-1],
            'Simulation time: % 12s' % datetime.timedelta(seconds=int(self.simulation_time)),
            '',
            'Speed:   % 15.0f km/h' % (3.6 * math.sqrt(v.x ** 2 + v.y ** 2 + v.z ** 2)),  # TODO: Change to mph
            u'Heading:% 16.0f\N{DEGREE SIGN} % 2s' % (t.rotation.yaw, heading),
            'Location:% 20s' % ('(% 5.1f, % 5.1f)' % (t.location.x, t.location.y)),
            # 'GNSS:% 24s' % ('(% 2.6f, % 3.6f)' % (world.gnss_sensor.lat, world.gnss_sensor.lon)),
            'Height:  % 18.0f m' % t.location.z,
            '']
        if isinstance(c, carla.VehicleControl):
            self._info_text += [
                ('Throttle:', c.throttle, 0.0, 1.0),
                ('Steer:', c.steer, -1.0, 1.0),
                ('Brake:', c.brake, 0.0, 1.0),
                ('Reverse:', c.reverse),
                ('Hand brake:', c.hand_brake),
                ('Manual:', c.manual_gear_shift),
                'Gear:        %s' % {-1: 'R', 0: 'N'}.get(c.gear, c.gear)]
            self.reverse = c.reverse
        elif isinstance(c, carla.WalkerControl):
            self._info_text += [
                ('Speed:', c.speed, 0.0, 5.556),
                ('Jump:', c.jump)]
        # self._info_text += [
        #     '',
        #     'Collision:',
        #     collision,
        #     '',
        #     'Number of vehicles: % 8d' % len(vehicles)]
        # if len(vehicles) > 1:
        #     self._info_text += ['Nearby vehicles:']
        #     distance = lambda l: math.sqrt(
        #         (l.x - t.location.x) ** 2 + (l.y - t.location.y) ** 2 + (l.z - t.location.z) ** 2)
        #     vehicles = [(distance(x.get_location()), x) for x in vehicles if x.id != world.player.id]
        #     for d, vehicle in sorted(vehicles):
        #         if d > 200.0:
        #             break
        #         vehicle_type = get_actor_display_name(vehicle, truncate=22)
        #         self._info_text.append('% 4dm %s' % (d, vehicle_type))

    def toggle_info(self):
        pass
        # self._show_info = not self._show_info

    def notification(self, text, seconds=2.0):
        # self._notifications.set_text(text, seconds=seconds)
        pass

    def error(self, text):
        # self._notifications.set_text('Error: %s' % text, (255, 0, 0))
        pass

    def render(self, display):
        info_surface = pygame.Surface((400, 200))
        info_surface.set_alpha(100)
        display.blit(info_surface, (int(self.dim[0] / 2 - 200), int(self.dim[1] / 1.2 - 100)))  # TODO: don't hard code
        v_offset = 4
        bar_h_offset = 100
        bar_width = 106

        if not self._info:
            return

        surface = self._font_mono.render(self._info['speed'], True, (255, 255, 255))
        display.blit(surface, (int(self.dim[0] / 2 - 200), int(self.dim[1] / 1.2 - 90)))

        # surface = self._font_mono.render(self._info['heading'], True, (255, 255, 255))
        # display.blit(surface, (int(self.dim[0] / 2 - 260), int(self.dim[1] / 1.2 - 90)))

        surface = self._font_mono.render(self._info['angular_velocity'], True, (255, 255, 255))
        display.blit(surface, (int(self.dim[0] / 2 - 260), int(self.dim[1] / 1.2 - 90)))

        surface = self._font_mono2.render(self._info['client_fps'], True, (255, 255, 255))
        display.blit(surface, (int(self.dim[0] / 2 - 200), int(self.dim[1] / 1.2 - 40)))

        surface = self._font_mono2.render(self._info['server_fps'], True, (255, 255, 255))
        display.blit(surface, (int(self.dim[0] / 2 - 200), int(self.dim[1] / 1.2 - 20)))

        if self.reverse:
            surface = self._font_mono3.render(str("REVERSING"), True, (255, 0, 0))
            display.blit(surface, (int(self.dim[0] / 2 - 50), int(self.dim[1] / 1.2 + 60)))

        if recorder.is_recording():
            surface = self._font_mono3.render(str("RECORDING"), True, (255, 0, 0))
            display.blit(surface, (int(self.dim[0] / 2 - 50), int(self.dim[1] / 1.2 + 20)))


        # for item in self._info_text:
        #     if v_offset + 18 > self.dim[1]:
        #         break
        #     if isinstance(item, list):
        #         if len(item) > 1:
        #             points = [(x + 8, v_offset + 8 + (1.0 - y) * 30) for x, y in enumerate(item)]
        #             pygame.draw.lines(display, (255, 136, 0), False, points, 2)
        #         item = None
        #         v_offset += 18
        #     elif isinstance(item, tuple):
        #         if isinstance(item[1], bool):
        #             rect = pygame.Rect((bar_h_offset, v_offset + 8), (6, 6))
        #             pygame.draw.rect(display, (255, 255, 255), rect, 0 if item[1] else 1)
        #         else:
        #             rect_border = pygame.Rect((bar_h_offset, v_offset + 8), (bar_width, 6))
        #             pygame.draw.rect(display, (255, 255, 255), rect_border, 1)
        #             f = (item[1] - item[2]) / (item[3] - item[2])
        #             if item[2] < 0.0:
        #                 rect = pygame.Rect((bar_h_offset + f * (bar_width - 6), v_offset + 8), (6, 6))
        #             else:
        #                 rect = pygame.Rect((bar_h_offset, v_offset + 8), (f * bar_width, 6))
        #             pygame.draw.rect(display, (255, 255, 255), rect)
        #         item = item[0]
        #     if item:  # At this point has to be a str.
        #         surface = self._font_mono.render(item, True, (255, 255, 255))
        #         display.blit(surface, (8, v_offset))
        #     v_offset += 18

        # self._notifications.render(display)
        # self.help.render(display)
