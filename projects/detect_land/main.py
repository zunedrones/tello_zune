from tello_zune import TelloZune
import cv2
import centralize1

tello = TelloZune(simulate=False)
tello.start_tello()

while True:
    tello.start_video(yolo_detect_base=True)
    still_video = centralize1.centralize(tello.tello, tello.values_detect, only_tracking=True)
    if cv2.waitKey(1) & 0xFF == ord('q') or not still_video:
        break
tello.end_video()
tello.end_tello()

