import pygame

def main():
    pygame.joystick.init()

    joystick = pygame.joystick.Joystick(0)
    joystick.init()

    numAxes = joystick.get_numaxes()

    while True:
        jsInputs = [float(joystick.get_axis(i)) for i in range(numAxes)]
        print(jsInputs)

main()