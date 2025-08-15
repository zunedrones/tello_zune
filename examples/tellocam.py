import cv2
from tello_zune import TelloZune
from ui.display_utils import write_info

tello = TelloZune(simulate=False)
tello.start_tello()

stats = {
    "fps": True,
    "battery": True,
    "height": True,
    "temperature": True,
    "pressure": True,
    "time_elapsed": True
}
while True:
    img = tello.get_frame()

    write_info(img, tello, stats)

    cv2.imshow('Tello', img)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

tello.end_tello()
cv2.destroyAllWindows()
