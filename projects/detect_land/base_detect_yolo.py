from ultralytics import YOLO
import cv2

FONT = cv2.FONT_HERSHEY_SIMPLEX
FONTSCALE = 1
COLOR = (255, 0, 0)
THICKNESS = 2

model = YOLO("tello_2.pt")
classNames = ["movel", "takeoff"]

def baseDetect(frame):
    '''
    Faz a deteccao da base e takeoff, utilzando modelo pre-treinado do yolov8n.
    Recebe como argumento o frame atual do video.
    '''
    results = model(frame, conf = 0.5)

    for r in results:
        boxes = r.boxes
        for box in boxes:
            x1, y1, x2, y2 = box.xyxy[0]
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2) 
            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 255), 3)

            cls = int(box.cls[0])
            org = [x1, y1]

            cv2.putText(frame, classNames[cls], org, FONT, FONTSCALE, COLOR, THICKNESS)

    if len(boxes) != 0:
        return [frame, x1, y1, x2, y2, len(boxes)]
    else:
        return [frame, 0, 0, 0, 0, len(boxes)]
