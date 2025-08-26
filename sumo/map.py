import carla

client = carla.Client("192.168.88.96", 2000)
client.set_timeout(10.0)

world = client.get_world()
carla_map = world.get_map()

xodr = carla_map.to_opendrive()

with open("exported_map.xodr", "w") as f:
    f.write(xodr)

print("OpenDRIVE exported successfully as exported_map.xodr")
