import cv2
from tello_zune import TelloZune

tello = TelloZune(simulate=False)
tello.start_tello()

while True:
    img = tello.get_frame()

    tello.write_info(img, fps=True, bat=True, height=True, temph=True, pres=True, time_elapsed=True)

    cv2.imshow('Tello', img)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

tello.end_tello()
cv2.destroyAllWindows()
