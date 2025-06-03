import pygame
from datetime import datetime

def main():
    pygame.init()
    pygame.joystick.init()

    joystick = pygame.joystick.Joystick(0)
    joystick.init()

    numAxes = joystick.get_numaxes()

    

    while True:
        pygame.event.pump()

        jsInputs = [float(joystick.get_axis(i)) for i in range(numAxes)]

        now = datetime.now()
        timestamp = now.timestamp()
        
        print(f"{timestamp}:\t{jsInputs}")

main()