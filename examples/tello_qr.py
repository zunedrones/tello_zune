import cv2
from pyzbar.pyzbar import decode
from tello_zune import TelloZune

#cap = cv2.VideoCapture(0)
data = []

tello = TelloZune()
tello.start_tello()

def process(frame: cv2.Mat) -> cv2.Mat:
    """
    Recebe um frame, detecta os códigos desenhando as bordas e o texto,
    armazena o texto em uma lista e retorna o frame
    Args:
        frame: frame capturado da câmera
    Returns:
        frame: frame processado com os códigos desenhados
    """
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

while True:
    #ret, frame = cap.read()
    ret, frame = tello.get_frame()
    battery, height, temperature, pressure, time = tello.get_info()
    cv2.putText(frame, f'Battery: {battery}%', (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    cv2.putText(frame, f'Height: {height}cm', (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    cv2.putText(frame, f'Temperature: {temperature}C', (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    cv2.putText(frame, f'Pressure: {pressure}Pa', (10, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    cv2.putText(frame, f'Time: {time}s', (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
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