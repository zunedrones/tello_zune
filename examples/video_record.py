import cv2 
from tello_zune import TelloZune

tello = TelloZune()
tello.start_tello() 
fourcc = cv2.VideoWriter_fourcc(*'XVID') 
video = cv2.VideoWriter('output.avi', fourcc, 30.0, (544, 306)) 

while True: 
    frame = tello.get_frame()

    video.write(frame)  
    cv2.imshow('Video tello', frame) 

    if cv2.waitKey(1) & 0xFF == ord('q'): 
        break
 
video.release()
tello.end_tello()
cv2.destroyAllWindows() 