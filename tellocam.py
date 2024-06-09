import cv2
from tello_zune import TelloZune

tello = TelloZune()
tello.start_tello()

while True:
    img = tello.get_frame()

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

tello.end_tello()
cv2.destroyAllWindows()