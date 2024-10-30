import cv2
from tello_zune import TelloZune
import time

# inicializa e conecta com o Tello
tello = TelloZune()
tello.start_tello()
count = 0

while True: 
    #obtem o frame do video
    frame = tello.get_frame() 
    #exibe na tela 'Video' cada frame obtido no laço de repeticao
    cv2.imshow('Video', frame) 
    # salva fotos da transmissao
    cv2.imwrite(f"takeoff{count}.jpeg", frame)
    count += 1
    if cv2.waitKey(1) & 0xFF == ord('q'): 
        break
    # pequeno delay de 0.5 segundos entre cada laço de repeticao
    # time.sleep(0.5)
# desliga a transmissao de video
tello.end_tello()
cv2.destroyAllWindows()
