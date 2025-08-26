# import pandas as pd
# from sumolib.net import readNet

# # Load CSV with CARLA positions (x, y in world coordinates)
# df = pd.read_csv("/home/remote-ops/Documents/carla-client/recordings/2025-08-26/2/position.csv", header=None)

# # Load SUMO network
# net = readNet("exported_map.net.xml")

# trajectory = []

# # Get network offset
# x_offset, y_offset = net.getLocationOffset()
# print("Network bounds:", net.getBoundary())
# print("Network offset:", (x_offset, y_offset))

# for idx, row in df.iterrows():
#     carla_x, carla_y = row[3], row[4]

#     x_sumo = carla_x - x_offset
#     y_sumo = -carla_y - y_offset 

#     # Get neighboring edges
#     edges = net.getNeighboringEdges(x_sumo, y_sumo, r=2)
#     if edges:
#         trajectory.append(edges[0].getID())
#     else:
#         print(f"No edge found for point ({carla_x}, {carla_y}) at row {idx}")

# # Remove consecutive duplicate edges
# route_edges = []
# prev_edge = None
# for e in trajectory:
#     if e != prev_edge:
#         route_edges.append(e)
#         prev_edge = e

# # Write SUMO route XML
# with open("human_driver.rou.xml", "w") as f:
#     f.write('<routes>\n')
#     f.write('    <vType id="car" accel="1.0" decel="4.5" length="5.0" minGap="2.5" maxSpeed="16.67"/>\n')
#     f.write('    <route id="human_route" edges="{}"/>\n'.format(' '.join(route_edges)))
#     f.write('    <vehicle id="driver1" type="car" route="human_route" depart="0"/>\n')
#     f.write('</routes>\n')

# print(f"Route written with {len(route_edges)} edges.")




import pandas as pd
from sumolib.net import readNet
import numpy as np

# Load CSV with CARLA positions
df = pd.read_csv("/home/remote-ops/Documents/carla-client/recordings/2025-08-26/2/position.csv", header=None)
print(f"Loaded {len(df)} data points")
print("First few rows of data:")
print(df.head())

# Load SUMO network
net = readNet("exported_map.net.xml")

# Get network information
bounds = net.getBoundary()
x_offset, y_offset = net.getLocationOffset()
print(f"Network bounds: {bounds}")
print(f"Network offset: ({x_offset}, {y_offset})")
print(f"Network size: {bounds[2]-bounds[0]:.2f} x {bounds[3]-bounds[1]:.2f}")

def try_coordinate_transformations(carla_x, carla_y, net, x_offset, y_offset):
    """Try different coordinate transformations to find edges"""
    transformations = [
        # Standard transformations to try
        (carla_x + x_offset, carla_y + y_offset, "carla_x + x_offset, carla_y + y_offset"),
        (carla_x - x_offset, carla_y - y_offset, "carla_x - x_offset, carla_y - y_offset"),
        (carla_x + x_offset, -carla_y + y_offset, "carla_x + x_offset, -carla_y + y_offset"),
        (carla_x - x_offset, -carla_y - y_offset, "carla_x - x_offset, -carla_y - y_offset"),
        (-carla_x + x_offset, carla_y + y_offset, "-carla_x + x_offset, carla_y + y_offset"),
        (-carla_x - x_offset, carla_y - y_offset, "-carla_x - x_offset, carla_y - y_offset"),
        (carla_y + x_offset, carla_x + y_offset, "carla_y + x_offset, carla_x + y_offset (swapped)"),
        (carla_y - x_offset, carla_x - y_offset, "carla_y - x_offset, carla_x - y_offset (swapped)"),
    ]
    
    for x_sumo, y_sumo, desc in transformations:
        # Check if within bounds
        if bounds[0] <= x_sumo <= bounds[2] and bounds[1] <= y_sumo <= bounds[3]:
            edges = net.getNeighboringEdges(x_sumo, y_sumo, r=5)
            if edges:
                return x_sumo, y_sumo, edges, desc
    
    return None, None, [], "No transformation worked"

trajectory = []
successful_transformations = {}

# Test first few points to find the right transformation
print("\nTesting coordinate transformations on first 5 points:")
for idx in range(min(5, len(df))):
    row = df.iloc[idx]
    carla_x, carla_y = row[3], row[4]
    x_sumo, y_sumo, edges, desc = try_coordinate_transformations(carla_x, carla_y, net, x_offset, y_offset)
    
    if edges:
        print(f"Point {idx}: CARLA({carla_x:.2f}, {carla_y:.2f}) -> SUMO({x_sumo:.2f}, {y_sumo:.2f}) using {desc}")
        successful_transformations[desc] = successful_transformations.get(desc, 0) + 1
    else:
        print(f"Point {idx}: No edges found for CARLA({carla_x:.2f}, {carla_y:.2f})")

# Use the most successful transformation
if successful_transformations:
    best_transform = max(successful_transformations.keys(), key=lambda x: successful_transformations[x])
    print(f"\nUsing transformation: {best_transform}")
    
    # Apply the best transformation to all points
    for idx, row in df.iterrows():
        carla_x, carla_y = row[3], row[4]
        
        # Apply the best transformation (you'll need to implement this based on the winning transformation)
        if "carla_x + x_offset, carla_y + y_offset" == best_transform:
            x_sumo, y_sumo = carla_x + x_offset, carla_y + y_offset
        elif "carla_x - x_offset, carla_y - y_offset" == best_transform:
            x_sumo, y_sumo = carla_x - x_offset, carla_y - y_offset
        elif "carla_x + x_offset, -carla_y + y_offset" == best_transform:
            x_sumo, y_sumo = carla_x + x_offset, -carla_y + y_offset
        elif "carla_x - x_offset, -carla_y - y_offset" == best_transform:
            x_sumo, y_sumo = carla_x - x_offset, -carla_y - y_offset
        # Add other transformations as needed
        
        edges = net.getNeighboringEdges(x_sumo, y_sumo, r=5)
        if edges:
            trajectory.append(edges[0][0].getID())
        else:
            print(f"No edge found for point ({carla_x:.2f}, {carla_y:.2f}) -> ({x_sumo:.2f}, {y_sumo:.2f}) at row {idx}")

    # Remove consecutive duplicate edges
    route_edges = []
    prev_edge = None
    for e in trajectory:
        if e != prev_edge:
            route_edges.append(e)
            prev_edge = e

    if route_edges:
        # Write SUMO route XML
        with open("human_driver.rou.xml", "w") as f:
            f.write('<routes>\n')
            f.write('    <vType id="car" accel="1.0" decel="4.5" length="5.0" minGap="2.5" maxSpeed="16.67"/>\n')
            f.write('    <route id="human_route" edges="{}"/>\n'.format(' '.join(route_edges)))
            f.write('    <vehicle id="driver1" type="car" route="human_route" depart="0"/>\n')
            f.write('</routes>\n')
        print(f"Route written with {len(route_edges)} edges: {route_edges[:10]}...")
    else:
        print("No valid route could be generated!")
else:
    print("No successful coordinate transformation found!")
    print("Possible issues:")
    print("1. CARLA and SUMO maps don't match")
    print("2. Wrong coordinate columns in CSV")
    print("3. Different map origins/scales")
    print("4. Network file doesn't contain roads where CARLA data was recorded")
