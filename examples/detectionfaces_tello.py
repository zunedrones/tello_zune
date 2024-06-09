import cv2
from tello_zune import TelloZune

# inicializa e conecta com o Tello
tello = TelloZune()
tello.start_tello()
# cria o objeto face_detector para fazer a deteccao de faces
face_detector = cv2.CascadeClassifier('cascades\haarcascade_frontalface_default.xml')

while True:
    # captura cada frame do objeto frame do tello
    frame = tello.get_frame()
    # converte a imagem de frame BGR para escala de cinza para a deteccao
    image_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    # faz a deteccao a cada frame
    detections = face_detector.detectMultiScale(image_gray, minSize=(130, 130), minNeighbors=9, maxSize=(290, 290), scaleFactor=1.05)

    #exibe o numero de rostos detectados
    if len(detections) >= 1:
        print(f"Rostos detectados: {len(detections)}")
    else:
        print(f"Rostos detectados: 0")

    # desenha a bounding box no frame 
    for x, y, w, h in detections:
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 255), 2)
    # exibe o frame 
    cv2.imshow("Video", frame)

    # quebra o laco de repeticao ao apertar a tecla 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
# desliga a transmissao do video
tello.end_tello()
cv2.destroyAllWindows()
