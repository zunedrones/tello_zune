import cv2
from pyzbar.pyzbar import decode
from tello_zune import TelloZune
from ui.display_utils import write_info

#cap = cv2.VideoCapture(0)
data = []

tello = TelloZune()
tello.start_tello()

"""
Recebe um frame, detecta os códigos desenhando as bordas e o texto,
armazena o texto em uma lista e retorna o frame
"""
def process(frame):
    decoded_objects = decode(frame)
    for obj in decoded_objects:
        (x, y, w, h) = obj.rect
        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
        qr_text = obj.data.decode('utf-8')
        cv2.putText(frame, qr_text, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        #print(qr_text)
        if qr_text not in data:
            data.append(qr_text)
    #print(data)
    return frame

stats = {
    "fps": True,
    "battery": True,
    "height": True,
    "temperature": True,
    "pressure": True,
    "time_elapsed": True
}
while True:
    #ret, frame = cap.read()
    ret, frame = tello.get_frame()
    write_info(frame, tello, stats)
    if not ret:
        print('erro na captura do frame')
        break
    processed_frame = process(frame)
    cv2.imshow('QR Code', processed_frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
print(data)
#cap.release()
tello.end_tello()
cv2.destroyAllWindows()