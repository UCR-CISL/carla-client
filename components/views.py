import carla
from carla import ColorConverter as cc
import weakref
import numpy as np
import pygame
import imageio.v3 as iio
import multiprocessing
from multiprocessing import shared_memory
import ctypes


def decode_loop(bytes_q, shm_decoded, terminate):
    while not terminate.value:
        if bytes_q.empty():
            continue
        bytes_all = bytes_q.get()

        frames = iio.imread(
            bytes_all.tobytes(),
            thread_count=16,
            thread_type="SLICE",
            index=0,
            plugin="pyav",
            extension=".m4v",
        )

        b = np.ndarray(frames.shape, dtype=frames.dtype, buffer=shm_decoded.buf)
        b[:] = frames[:]


class Decoder:
    def __init__(self, sensor, width, height):
        self.sensor = sensor
        self.surface = None

        self.terminate = multiprocessing.Value(ctypes.c_bool, False)
        self.bytes_q = multiprocessing.Queue()
        self.shm_decoded = shared_memory.SharedMemory(create=True, size=width * height * 3)
        self.process = multiprocessing.Process(target=decode_loop,
                                               args=(self.bytes_q, self.shm_decoded, self.terminate))
        self.decoded_shape = (height, width, 3)

    def start(self):
        self.terminate.value = False
        # We need to pass the lambda a weak reference to self to avoid circular reference.
        weak_self = weakref.ref(self)
        self.sensor.listen(lambda byte_data: _decode(weak_self, byte_data))
        self.process.start()

    def stop(self):
        self.terminate.value = True
        self.process.join()
        self.sensor.stop()

    def destroy(self):
        if not self.terminate.value:
            self.stop()
        self.shm_decoded.close()
        self.shm_decoded.unlink()
        self.sensor.destroy()


class CameraManager(object):
    def __init__(self, parent_actor, hud):
        self.driver_camera_decoder = None
        self.reverse_camera_decoder = None
        self.side_mirror_camera_decoders = []

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
            ['sensor.camera.stream', cc.Raw, 'Camera RGB']
        ]

        self.reverse_mirror_info = [
            ['sensor.camera.stream', cc.Raw, 'Camera RGB']
        ]

        self.sensors_side_mirrors_info = [
            ['sensor.camera.stream', cc.Raw, 'Camera RGB Side Mirror Left'],
            ['sensor.camera.stream', cc.Raw, 'Camera RGB Side Mirror Right']
        ]

        world = self._parent.get_world()
        bp_library = world.get_blueprint_library()

        for item in self.driver_view_info:
            bp = bp_library.find(item[0])
            bp.set_attribute('image_size_x', str(hud.dim[0]))
            bp.set_attribute('image_size_y', str(hud.dim[1]))
            item.append(bp)
        self.index = None

        for item in self.reverse_mirror_info:
            bp = bp_library.find(item[0])
            bp.set_attribute('image_size_x', str(int(3 * hud.dim[0] / 12)))
            bp.set_attribute('image_size_y', str(int(3 * hud.dim[1] / 24)))
            item.append(bp)

        for mirror_info in self.sensors_side_mirrors_info:
            bp = bp_library.find(mirror_info[0])
            bp.set_attribute('image_size_x', str(int(3 * hud.dim[0] / 16)))
            bp.set_attribute('image_size_y', str(int(3 * hud.dim[1] / 16)))
            bp.set_attribute('fov', str(45.0))
            mirror_info.append(bp)

    def set_sensor(self, index, notify=True):
        index = index % len(self.driver_view_info)
        needs_respawn = self.index is None
        if needs_respawn:
            if self.driver_camera_decoder is not None:
                self.driver_camera_decoder.destroy()
                self.reverse_camera_decoder.destroy()

                self.driver_camera_decoder = None
                self.reverse_camera_decoder = None

            self.driver_camera_decoder = self._decoder_setup(self.driver_view_info[0][-1],
                                                             self._camera_transforms[0])
            self.driver_camera_decoder.start()

            self.reverse_camera_decoder = self._decoder_setup(self.reverse_mirror_info[0][-1],
                                                              self._reverse_mirror_transforms[0])
            self.reverse_camera_decoder.start()

            # for i in range(2):
            #     side_mirror_decoder = self._decoder_setup(self.sensors_side_mirrors_info[i][-1],
            #                                               self._side_mirrors_transforms[i])
            #     self.side_mirror_camera_decoders.append(side_mirror_decoder)
            #     side_mirror_decoder.start()

        if notify:
            self.hud.notification(self.driver_view_info[index][2])
        self.index = index

    def _decoder_setup(self, bp, transform):
        camera = self._parent.get_world().spawn_actor(bp, transform, attach_to=self._parent)
        decoder = Decoder(camera, bp.get_attribute('image_size_x').as_int(), bp.get_attribute('image_size_y').as_int())
        return decoder

    def _switch_side_view(self):
        prev_decoder = self.driver_camera_decoder
        self.driver_camera_decoder = self._decoder_setup(self.driver_view_info[0][-1],
                                                         self._camera_transforms[self.transform_index])
        self.driver_camera_decoder.start()
        prev_decoder.destroy()

    def toggle_side_view(self, transform_index):
        self.transform_index = transform_index
        self._switch_side_view()

    def toggle_recording(self):
        self.recording = not self.recording
        self.hud.notification('Recording %s' % ('On' if self.recording else 'Off'))

    def render(self, display):
        if self.driver_camera_decoder.surface is not None:
            display.blit(self.driver_camera_decoder.surface, (0, 0))
        if self.reverse_camera_decoder.surface is not None:
            display.blit(self.reverse_camera_decoder.surface, (int(6 * self.hud.dim[0] / 16), 0))
        # if self.side_mirror_camera_decoders[0].surface is not None:
        #     display.blit(self.side_mirror_camera_decoders[0].surface,
        #                  (int(self.hud.dim[0] / 16), int(12 * self.hud.dim[1] / 16)))
        # if self.side_mirror_camera_decoders[1].surface is not None:
        #     display.blit(self.side_mirror_camera_decoders[1].surface,
        #                  (int(14 * self.hud.dim[0] / 16 - self.hud.dim[0] / 8), int(12 * self.hud.dim[1] / 16)))


def _decode(weak_self, byte_data):
    self = weak_self()
    if not self or self.terminate.value:
        return

    array = np.frombuffer(byte_data.raw_data, dtype=np.dtype("uint8"))
    self.bytes_q.put(array)

    data = np.ndarray(self.decoded_shape, dtype=np.uint8, buffer=self.shm_decoded.buf)
    self.surface = pygame.surfarray.make_surface(data.swapaxes(0, 1))
