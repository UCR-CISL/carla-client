import carla
from carla import ColorConverter as cc
import weakref
import numpy as np
import pygame


class CameraManager(object):
    def __init__(self, parent_actor, hud):
        self.driver_view = None
        self.sensor_side_mirrors = []
        self.left_mirror = None
        self.right_mirror = None
        self.reverse_mirror = None

        self.surface = None
        self.surface_side_mirrors = [None, None]
        self.surface_reverse = None

        self._parent = parent_actor
        self.hud = hud
        self.recording = False
        self._camera_transforms = [
            carla.Transform(carla.Location(x=0.1, y=-0.2, z=1.3), carla.Rotation(pitch=0)),  # First person
            carla.Transform(carla.Location(x=0.1, y=-0.2, z=1.3), carla.Rotation(yaw=-60)),  # Left side view
            carla.Transform(carla.Location(x=0.1, y=-0.2, z=1.3), carla.Rotation(yaw=60)),  # Right side view

            # carla.Transform(carla.Location(x=-5.5, z=2.8), carla.Rotation(pitch=-15))  # Third person
        ]
        self._side_mirrors_transforms = [
            carla.Transform(carla.Location(x=0.2, y=-0.8, z=1.2), carla.Rotation(pitch=-10, yaw=-160)),
            carla.Transform(carla.Location(x=0.2, y=0.8, z=1.2), carla.Rotation(pitch=-10, yaw=160))
        ]
        self._reverse_mirror_transforms = [
            carla.Transform(carla.Location(x=-0.8, y=0.0, z=1.35), carla.Rotation(yaw=180)),
        ]

        self.transform_index = 0
        self.driver_view_info = [
            ['sensor.camera.rgb', cc.Raw, 'Camera RGB']
        ]
        self.sensors_side_mirrors_info = [
            ['sensor.camera.rgb', cc.Raw, 'Camera RGB Side Mirror Left'],
            ['sensor.camera.rgb', cc.Raw, 'Camera RGB Side Mirror Right']
        ]
        self.reverse_mirror_info = [
            ['sensor.camera.rgb', cc.Raw, 'Camera RGB']
        ]

        world = self._parent.get_world()
        bp_library = world.get_blueprint_library()
        for item in self.driver_view_info:
            bp = bp_library.find(item[0])
            bp.set_attribute('image_size_x', str(hud.dim[0]))
            bp.set_attribute('image_size_y', str(hud.dim[1]))
            item.append(bp)
        self.index = None

        for mirror_info in self.sensors_side_mirrors_info:
            bp = bp_library.find(mirror_info[0])
            bp.set_attribute('image_size_x', str(int(3 * hud.dim[0] / 16)))
            bp.set_attribute('image_size_y', str(int(3 * hud.dim[1] / 16)))
            bp.set_attribute('fov', str(45.0))
            mirror_info.append(bp)

        for item in self.reverse_mirror_info:
            bp = bp_library.find(item[0])
            bp.set_attribute('image_size_x', str(int(3 * hud.dim[0] / 12)))
            bp.set_attribute('image_size_y', str(int(3 * hud.dim[1] / 24)))
            item.append(bp)

    def set_sensor(self, index, notify=True):
        index = index % len(self.driver_view_info)
        needs_respawn = self.index is None
        self.index = index
        if needs_respawn:
            if self.driver_view is not None:
                self.driver_view.destroy()
                for mirror in self.sensor_side_mirrors:
                    mirror.destroy()
                self.reverse_mirror.destroy()
                self.sensor_side_mirrors = []
                self.surface = None
                self.surface_side_mirrors = [None, None]
                self.surface_reverse = None
            self.driver_view = self._parent.get_world().spawn_actor(
                self.driver_view_info[index][-1],
                self._camera_transforms[0],
                attach_to=self._parent)
            # for i in range(2):
            #     mirror = self._parent.get_world().spawn_actor(
            #         self.sensors_side_mirrors_info[i][-1],
            #         self._side_mirrors_transforms[i],
            #         attach_to=self._parent)
            #     self.sensor_side_mirrors.append(mirror)
            self.reverse_mirror = self._parent.get_world().spawn_actor(
                self.reverse_mirror_info[0][-1],
                self._reverse_mirror_transforms[0],
                attach_to=self._parent)
            # We need to pass the lambda a weak reference to self to avoid
            # circular reference.
            weak_self = weakref.ref(self)
            self.driver_view.listen(lambda image: CameraManager._parse_image(weak_self, image))
            # self.sensor_side_mirrors[0].listen(lambda image: CameraManager._parse_left_mirror_image(weak_self, image))
            # self.sensor_side_mirrors[1].listen(lambda image: CameraManager._parse_right_mirror_image(weak_self, image))
            self.reverse_mirror.listen(lambda image: CameraManager._parse_reverse_image(weak_self, image))
        if notify:
            self.hud.notification(self.driver_view_info[index][2])

    def _switch_side_view(self):
        self.driver_view.destroy()
        self.surface = None
        self.driver_view = self._parent.get_world().spawn_actor(
            self.driver_view_info[0][-1],
            self._camera_transforms[self.transform_index],
            attach_to=self._parent)
        if self.transform_index == 1:
            self.left_mirror = self._parent.get_world().spawn_actor(
                self.sensors_side_mirrors_info[0][-1],
                self._side_mirrors_transforms[0],
                attach_to=self._parent)
            self.left_mirror.listen(lambda image: CameraManager._parse_left_mirror_image(weak_self, image))
        elif self.transform_index == 2:
            self.right_mirror = self._parent.get_world().spawn_actor(
                self.sensors_side_mirrors_info[1][-1],
                self._side_mirrors_transforms[1],
                attach_to=self._parent)
            self.right_mirror.listen(lambda image: CameraManager._parse_right_mirror_image(weak_self, image))
        else:
            if self.left_mirror is not None:
                self.left_mirror.destroy()
                self.surface_side_mirrors[0] = None
                self.left_mirror = None
            if self.right_mirror is not None:
                self.right_mirror.destroy()
                self.surface_side_mirrors[1] = None
                self.right_mirror = None

        weak_self = weakref.ref(self)
        self.driver_view.listen(lambda image: CameraManager._parse_image(weak_self, image))

    def toggle_side_view(self, transform_index):
        self.transform_index = transform_index
        self._switch_side_view()

    def toggle_recording(self):
        self.recording = not self.recording
        self.hud.notification('Recording %s' % ('On' if self.recording else 'Off'))

    def render(self, display):
        if self.surface is not None:
            display.blit(self.surface, (0, 0))
        if self.surface_side_mirrors[0] is not None:
            display.blit(self.surface_side_mirrors[0], (int(self.hud.dim[0] / 16), int(12 * self.hud.dim[1] / 16)))
        if self.surface_side_mirrors[1] is not None:
            display.blit(self.surface_side_mirrors[1],
                         (int(14 * self.hud.dim[0] / 16 - self.hud.dim[0] / 8), int(12 * self.hud.dim[1] / 16)))
        if self.surface_reverse is not None:
            display.blit(self.surface_reverse, (int(6 * self.hud.dim[0] / 16), 0))

    @staticmethod
    def _parse_left_mirror_image(weak_self, image):
        self = weak_self()
        if not self:
            return
        image.convert(self.sensors_side_mirrors_info[0][1])
        array = np.frombuffer(image.raw_data, dtype=np.dtype("uint8"))
        array = np.reshape(array, (image.height, image.width, 4))
        array = array[:, :, :3]
        array = array[:, :, ::-1]
        self.surface_side_mirrors[0] = pygame.surfarray.make_surface(array.swapaxes(0, 1))

    @staticmethod
    def _parse_right_mirror_image(weak_self, image):
        self = weak_self()
        if not self:
            return
        image.convert(self.sensors_side_mirrors_info[1][1])
        array = np.frombuffer(image.raw_data, dtype=np.dtype("uint8"))
        array = np.reshape(array, (image.height, image.width, 4))
        array = array[:, :, :3]
        array = array[:, :, ::-1]
        self.surface_side_mirrors[1] = pygame.surfarray.make_surface(array.swapaxes(0, 1))

    @staticmethod
    def _parse_image(weak_self, image):
        self = weak_self()
        if not self:
            return
        image.convert(self.driver_view_info[self.index][1])
        array = np.frombuffer(image.raw_data, dtype=np.dtype("uint8"))
        array = np.reshape(array, (image.height, image.width, 4))
        array = array[:, :, :3]
        array = array[:, :, ::-1]
        self.surface = pygame.surfarray.make_surface(array.swapaxes(0, 1))

    @staticmethod
    def _parse_reverse_image(weak_self, image):
        self = weak_self()
        if not self:
            return
        image.convert(self.reverse_mirror_info[0][1])
        array = np.frombuffer(image.raw_data, dtype=np.dtype("uint8"))
        array = np.reshape(array, (image.height, image.width, 4))
        array = array[:, :, :3]
        array = array[:, :, ::-1]
        array = np.fliplr(array)
        self.surface_reverse = pygame.surfarray.make_surface(array.swapaxes(0, 1))
