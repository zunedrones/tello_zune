from tello_zune import TelloZune
import cv2
import centralize1

tello = TelloZune()
tello.start_tello()

while True:
    tello.start_video(yolo_detect_base=True)
    centralize1.centralize(tello.tello, tello.values_detect)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
tello.end_video()
tello.end_tello()

