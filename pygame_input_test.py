import pygame

pygame.init()
pygame.joystick.init()

joystick = pygame.joystick.Joystick(0)

joystick.init()

joy_name = joystick.get_name()
print(joy_name)  # <----detected and correct name

print("Num Axis:", joystick.get_numaxes())  # <---- this returns zero
print("Num Hats:", joystick.get_numhats())  # <---- this returns zero
print("Num Buttons:", joystick.get_numbuttons())

# Axis 0: Steering wheel angle
# Axis 1: Thrust pedal
# Axis 2: Brake pedal
# Axis 3: CLUTCH pedal

while True:
    for event in pygame.event.get():
        if event.type == pygame.JOYAXISMOTION:
            print(event.dict, event.joy, event.axis, event.value)
        elif event.type == pygame.JOYBALLMOTION:
            print(event.dict, event.joy, event.ball, event.rel)
        elif event.type == pygame.JOYBUTTONDOWN:
            print(event.dict, event.joy, event.button, 'pressed')
        elif event.type == pygame.JOYBUTTONUP:
            print(event.dict, event.joy, event.button, 'released')
        elif event.type == pygame.JOYHATMOTION:
            print(event.dict, event.joy, event.hat, event.value)

    # for event in pygame.event.get():
    #     if event.type == pygame.JOYBUTTONUP:
    #         print(event.button)
    #     elif event.type == pygame.KEYUP:
    #         print(event)
