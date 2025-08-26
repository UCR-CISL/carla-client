import carla
import pygame
import math
import joystick_lookup as js
from configparser import ConfigParser
from components.recorder import recorder


try:
    import pygame
    from pygame.locals import KMOD_CTRL
    from pygame.locals import KMOD_SHIFT
    from pygame.locals import K_0
    from pygame.locals import K_9
    from pygame.locals import K_BACKQUOTE
    from pygame.locals import K_BACKSPACE
    from pygame.locals import K_COMMA
    from pygame.locals import K_DOWN
    from pygame.locals import K_ESCAPE
    from pygame.locals import K_F1
    from pygame.locals import K_LEFT
    from pygame.locals import K_PERIOD
    from pygame.locals import K_RIGHT
    from pygame.locals import K_SLASH
    from pygame.locals import K_SPACE
    from pygame.locals import K_TAB
    from pygame.locals import K_UP
    from pygame.locals import K_a
    from pygame.locals import K_b
    from pygame.locals import K_c
    from pygame.locals import K_d
    from pygame.locals import K_f
    from pygame.locals import K_g
    from pygame.locals import K_h
    from pygame.locals import K_i
    from pygame.locals import K_l
    from pygame.locals import K_m
    from pygame.locals import K_n
    from pygame.locals import K_o
    from pygame.locals import K_p
    from pygame.locals import K_q
    from pygame.locals import K_r
    from pygame.locals import K_s
    from pygame.locals import K_t
    from pygame.locals import K_v
    from pygame.locals import K_w
    from pygame.locals import K_x
    from pygame.locals import K_z
    from pygame.locals import K_MINUS
    from pygame.locals import K_EQUALS
except ImportError:
    raise RuntimeError('cannot import pygame, make sure pygame package is installed')

class SteeringwheelController(object):
    def __init__(self, joystick, args):
        self._control = carla.VehicleControl()
        self._steer_cache = 0.0
        self.args = args
        # world.hud.notification("Press 'H' or '?' for help.", seconds=4.0)

        self._joystick = joystick

        self._parser = ConfigParser()
        self._parser.read('wheel_config.ini')
        self._steer_idx = int(
            self._parser.get('G920 Racing Wheel', 'steering_wheel'))
        self._throttle_idx = int(
            self._parser.get('G920 Racing Wheel', 'throttle'))
        self._brake_idx = int(self._parser.get('G920 Racing Wheel', 'brake'))
        self._reverse_idx = int(self._parser.get('G920 Racing Wheel', 'reverse'))
        self._handbrake_idx = int(self._parser.get('G920 Racing Wheel', 'handbrake'))

        self.steering_mode = int(self._parser.get('Sensitivity', 'mode'))
        self.steering_sensitivity_min = float(self._parser.get('Sensitivity', 'min'))
        self.steering_sensitivity_max = float(self._parser.get('Sensitivity', 'max'))

        self._mph = 0

        self._lights = carla.VehicleLightState.NONE

    def parse_events(self, world, clock, frame):
        events = pygame.event.get()
        world.menu.update_events(events)

        v = world.player.get_velocity()
        self._mph = 0.621371 * 3.6 * math.sqrt(v.x ** 2 + v.y ** 2 + v.z ** 2)

        if world.menu.is_enabled():
            return
        for event in events:
            timestamp = pygame.time.get_ticks()
            if event.type == pygame.QUIT:
                return True
            elif event.type == pygame.MOUSEBUTTONDOWN:
                x, y, w, h = world.hud.settings_button.get_region()
                mouse = pygame.mouse.get_pos()
                if world.menu.settings_button.clickable and x <= mouse[0] <= x + w and y <= mouse[1] <= y + h:
                    world.menu.toggle_menu(False)
            elif event.type == pygame.JOYBUTTONDOWN:
                recorder.save_button("JOYBUTTONDOWN", event.button, frame, timestamp)
                if event.button == js.BUTTON_A:
                    world.restart()
                elif event.button == js.BUTTON_Y:
                    world.next_weather()
                elif event.button == js.BUTTON_X:
                    recorder.turn_recorder_off() if recorder.is_recording() else recorder.turn_recorder_on()
                elif event.button == self._reverse_idx:
                    self._control.gear = 1 if self._control.reverse else -1
                # Buttons for intent :
                elif event.button == js.BUTTON_GEAR_DOWN:
                    self._lights ^= carla.VehicleLightState.LeftBlinker
                    world.player.set_light_state(carla.VehicleLightState(self._lights))
                    world.intent = "Left Lane"
                elif event.button == js.BUTTON_GEAR_UP:
                    self._lights ^= carla.VehicleLightState.RightBlinker
                    world.player.set_light_state(carla.VehicleLightState(self._lights))
                    world.intent = "Right Lane"
                elif event.button == js.BUTTON_CNTRCLKWISE:
                    world.intent = "Left Turn"
                elif event.button == js.BUTTON__CLKWISE:
                    world.intent = "Right Turn"
                elif event.button == js.BUTTON_L2 :
                    world.intent = "U-Turn"
                elif event.button == js.BUTTON_R2 :
                    world.intent = "Straight"
                
                

            elif event.type == pygame.JOYHATMOTION:
                recorder.save_hat("JOYHATMOTION", event.value, frame, timestamp)
                if event.value == js.HAT_LEFT:
                    world.camera_manager.toggle_side_view(1)
                elif event.value == js.HAT_RIGHT:
                    world.camera_manager.toggle_side_view(2)
                elif event.value == js.HAT_DOWN:
                    self._control.gear = 1 if self._control.reverse else -1
                elif event.value == js.HAT_RELEASE:
                    world.camera_manager.toggle_side_view(0)

            elif event.type == pygame.KEYUP:
                recorder.save_key("KEYUP", pygame.key.name(event.key), frame, timestamp)
                if self._is_quit_shortcut(event.key):
                    return True
                elif event.key == K_BACKSPACE:
                    world.restart()
                elif event.key == K_F1:
                    world.hud.toggle_info()
                # elif event.key == K_h or (event.key == K_SLASH and pygame.key.get_mods() & KMOD_SHIFT):
                #     world.hud.help.toggle()
                elif event.key == K_c and pygame.key.get_mods() & KMOD_SHIFT:
                    world.next_weather(reverse=True)
                elif event.key == K_c:
                    world.next_weather()
                # elif event.key == K_r:
                #     world.camera_manager.toggle_recording()
                if isinstance(self._control, carla.VehicleControl):
                    if event.key == K_q:
                        self._control.gear = 1 if self._control.reverse else -1
                    elif event.key == K_m:
                        self._control.manual_gear_shift = not self._control.manual_gear_shift
                        self._control.gear = world.player.get_control().gear
                        world.hud.notification('%s Transmission' %
                                               ('Manual' if self._control.manual_gear_shift else 'Automatic'))


        self._parse_vehicle_keys(pygame.key.get_pressed(), clock.get_time())
        self._parse_vehicle_wheel(frame)
        self._control.reverse = self._control.gear < 0
        world.player.apply_control(self._control)

    def _parse_vehicle_keys(self, keys, milliseconds):
        self._control.throttle = 1.0 if keys[K_UP] or keys[K_w] else 0.0
        steer_increment = 5e-4 * milliseconds
        if keys[K_LEFT] or keys[K_a]:
            self._steer_cache -= steer_increment
        elif keys[K_RIGHT] or keys[K_d]:
            self._steer_cache += steer_increment
        else:
            self._steer_cache = 0.0
        self._steer_cache = min(0.7, max(-0.7, self._steer_cache))
        self._control.steer = round(self._steer_cache, 1)
        self._control.brake = 1.0 if keys[K_DOWN] or keys[K_s] else 0.0
        self._control.hand_brake = keys[K_SPACE]

    def _parse_vehicle_wheel(self, frame):
        numAxes = self._joystick.get_numaxes()
        jsInputs = [float(self._joystick.get_axis(i)) for i in range(numAxes)]
        jsButtons = [float(self._joystick.get_button(i)) for i in
                     range(self._joystick.get_numbuttons())]

        steerCmd = jsInputs[self._steer_idx] * 0.5


        K2 = 1.6
        x = jsInputs[self._throttle_idx]

        # Original nonlinear computation
        y = K2 + (2.05 * math.log10(-0.7 * x + 1.4) - 1.2) / 0.92

        # Determine original output range (can be computed from min/max of x)
        y_min =-0.049509802142144954
        y_max = 1.0136408197875375

        # Scale to 0-0.75
        throttleCmd = (y - y_min) * 0.75 / (y_max - y_min)

        #Speed limit
        if self._mph >=45 :
            throttleCmd = 0 

        brakeCmd = 1.6 + (2.05 * math.log10(

            -0.7 * jsInputs[self._brake_idx] + 1.4) - 1.2) / 0.92
        if brakeCmd <= 0:
            brakeCmd = 0
        elif brakeCmd > 1:
            brakeCmd = 1

        self._control.steer = steerCmd
        self._control.brake = brakeCmd
        self._control.throttle = throttleCmd

        timestamp = pygame.time.get_ticks()

        recorder.save_joystick(jsInputs[self._throttle_idx], throttleCmd, jsInputs[self._brake_idx], brakeCmd, jsInputs[self._steer_idx], steerCmd, frame, timestamp)

        self._control.hand_brake = bool(jsButtons[self._handbrake_idx])

    def update_steering_config(self, steering_config):
        self.steering_mode = steering_config[0]
        self.steering_sensitivity_min = steering_config[1]
        self.steering_sensitivity_max = steering_config[2]
        self._parser.set('Sensitivity', 'mode', str(self.steering_mode))
        self._parser.set('Sensitivity', 'min', str(self.steering_sensitivity_min))
        self._parser.set('Sensitivity', 'max', str(self.steering_sensitivity_max))

    def save_config_file(self):
        with open('wheel_config.ini', 'w') as config_file:  # save
            self._parser.write(config_file)

    @staticmethod
    def _is_quit_shortcut(key):
        return (key == K_ESCAPE) or (key == K_q and pygame.key.get_mods() & KMOD_CTRL)
    

class KeyboardController(object):
    """Class that handles keyboard input."""

    def __init__(self, start_in_autopilot ):
        self._control = carla.VehicleControl()
        self._lights = carla.VehicleLightState.NONE
        self._steer_cache = 0.0

    def parse_events(self, world, clock, frame):
        if isinstance(self._control, carla.VehicleControl):
            current_lights = self._lights
        for event in pygame.event.get():
            timestamp = pygame.time.get_ticks()
            if event.type == pygame.QUIT:
                return True
            elif event.type == pygame.KEYUP:
                recorder.save_key("KEYUP", pygame.key.name(event.key), frame, timestamp)
                if self._is_quit_shortcut(event.key):
                    return True
                elif event.key == K_BACKSPACE:
                    world.restart()
                elif event.key == K_F1:
                    world.hud.toggle_info()
                elif event.key == K_v and pygame.key.get_mods() & KMOD_SHIFT:
                    world.next_map_layer(reverse=True)
                elif event.key == K_v:
                    world.next_map_layer()
                elif event.key == K_b and pygame.key.get_mods() & KMOD_SHIFT:
                    world.load_map_layer(unload=True)
                elif event.key == K_b:
                    world.load_map_layer()
                # elif event.key == K_h or (event.key == K_SLASH and pygame.key.get_mods() & KMOD_SHIFT):
                #     world.hud.help.toggle()
                elif event.key == K_c and pygame.key.get_mods() & KMOD_SHIFT:
                    world.next_weather(reverse=True)
                elif event.key == K_c:
                    world.next_weather()
                elif event.key == K_g:
                    world.toggle_radar()
                elif event.key == K_BACKQUOTE:
                    world.camera_manager.next_sensor()
                elif event.key == K_n:
                    world.camera_manager.next_sensor()
                elif event.key == K_w and (pygame.key.get_mods() & KMOD_CTRL):
                    if world.constant_velocity_enabled:
                        world.player.disable_constant_velocity()
                        world.constant_velocity_enabled = False
                        world.hud.notification("Disabled Constant Velocity Mode")
                    else:
                        world.player.enable_constant_velocity(carla.Vector3D(17, 0, 0))
                        world.constant_velocity_enabled = True
                        world.hud.notification("Enabled Constant Velocity Mode at 60 km/h")
                elif event.key == K_o:
                    try:
                        if world.doors_are_open:
                            world.hud.notification("Closing Doors")
                            world.doors_are_open = False
                            world.player.close_door(carla.VehicleDoor.All)
                        else:
                            world.hud.notification("Opening doors")
                            world.doors_are_open = True
                            world.player.open_door(carla.VehicleDoor.All)
                    except Exception:
                        pass
                elif event.key == K_t:
                    if world.show_vehicle_telemetry:
                        world.player.show_debug_telemetry(False)
                        world.show_vehicle_telemetry = False
                        world.hud.notification("Disabled Vehicle Telemetry")
                    else:
                        try:
                            world.player.show_debug_telemetry(True)
                            world.show_vehicle_telemetry = True
                            world.hud.notification("Enabled Vehicle Telemetry")
                        except Exception:
                            pass
                elif event.key > K_0 and event.key <= K_9:
                    index_ctrl = 0
                    if pygame.key.get_mods() & KMOD_CTRL:
                        index_ctrl = 9
                    world.camera_manager.set_sensor(event.key - 1 - K_0 + index_ctrl)
                # elif event.key == K_r and not (pygame.key.get_mods() & KMOD_CTRL):
                #     world.camera_manager.toggle_recording()
                if event.key == K_q:
                    self._control.gear = 1 if self._control.reverse else -1
                elif event.key == K_m:
                    self._control.manual_gear_shift = not self._control.manual_gear_shift
                    self._control.gear = world.player.get_control().gear
                    world.hud.notification('%s Transmission' %
                                           ('Manual' if self._control.manual_gear_shift else 'Automatic'))
                elif self._control.manual_gear_shift and event.key == K_COMMA:
                    self._control.gear = max(-1, self._control.gear - 1)
                elif self._control.manual_gear_shift and event.key == K_PERIOD:
                    self._control.gear = self._control.gear + 1
                elif event.key == K_l and pygame.key.get_mods() & KMOD_CTRL:
                    current_lights ^= carla.VehicleLightState.Special1
                elif event.key == K_l and pygame.key.get_mods() & KMOD_SHIFT:
                    current_lights ^= carla.VehicleLightState.HighBeam
                elif event.key == K_l:
                    # Use 'L' key to switch between lights:
                    # closed -> position -> low beam -> fog
                    if not self._lights & carla.VehicleLightState.Position:
                        world.hud.notification("Position lights")
                        current_lights |= carla.VehicleLightState.Position
                    else:
                        world.hud.notification("Low beam lights")
                        current_lights |= carla.VehicleLightState.LowBeam
                    if self._inputs_log_keyboard.jsonlights & carla.VehicleLightState.LowBeam:
                        world.hud.notification("Fog lights")
                        current_lights |= carla.VehicleLightState.Fog
                    if self._lights & carla.VehicleLightState.Fog:
                        world.hud.notification("Lights off")
                        current_lights ^= carla.VehicleLightState.Position
                        current_lights ^= carla.VehicleLightState.LowBeam
                        current_lights ^= carla.VehicleLightState.Fog
                elif event.key == K_i:
                    current_lights ^= carla.VehicleLightState.Interior
                elif event.key == K_z:
                    current_lights ^= carla.VehicleLightState.LeftBlinker
                elif event.key == K_x:
                    current_lights ^= carla.VehicleLightState.RightBlinker

        self._parse_vehicle_keys(pygame.key.get_pressed(), clock.get_time())
        self._control.reverse = self._control.gear < 0
        # Set automatic control-related vehicle lights
        if self._control.brake:
            current_lights |= carla.VehicleLightState.Brake
        else:  # Remove the Brake flag
            current_lights &= ~carla.VehicleLightState.Brake
        if self._control.reverse:
            current_lights |= carla.VehicleLightState.Reverse
        else:  # Remove the Reverse flag
            current_lights &= ~carla.VehicleLightState.Reverse
        if current_lights != self._lights:  # Change the light state only if necessary
            self._lights = current_lights
            world.player.set_light_state(carla.VehicleLightState(self._lights))
        world.player.apply_control(self._control)

    def _parse_vehicle_keys(self, keys, milliseconds):
        if keys[K_UP] or keys[K_w]:
            self._control.throttle = min(self._control.throttle + 0.1, 1.00)

        else:
            self._control.throttle = 0.0

        if keys[K_DOWN] or keys[K_s]:
            self._control.brake = min(self._control.brake + 0.2, 1)

        else:
            self._control.brake = 0

        steer_increment = 5e-4 * milliseconds
        if keys[K_LEFT] or keys[K_a]:
            if self._steer_cache > 0:
                self._steer_cache = 0
            else:
                self._steer_cache -= steer_increment
        elif keys[K_RIGHT] or keys[K_d]:
            if self._steer_cache < 0:
                self._steer_cache = 0
            else:
                self._steer_cache += steer_increment
        else:
            self._steer_cache = 0.0
        self._steer_cache = min(0.7, max(-0.7, self._steer_cache))
        self._control.steer = round(self._steer_cache, 1)
        self._control.hand_brake = keys[K_SPACE]

    @staticmethod
    def _is_quit_shortcut(key):
        return (key == K_ESCAPE) or (key == K_q and pygame.key.get_mods() & KMOD_CTRL)
