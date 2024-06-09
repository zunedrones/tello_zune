import cv2
from tello_zune import TelloZune

tello = TelloZune()
tello.start_tello()

while True:
    img = tello.get_frame()
    tello.calc_fps(img)

    # para fazer o drone realizar movimentos:
    # tello.send_rc_control(0, 0, 0, 0)

    cv2.imshow('Tello', img)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

tello.end_tello()
cv2.destroyAllWindows()