import cv2 
from djitellopy import Tello

# inicializa e conecta com o Tello
tello = Tello()
tello.connect()
# exibe a bateria do drone
print(f"Bateria: {tello.get_battery()}%")
# comeca a transmissao de video
tello.streamon()

while True: 
    # captura cada frame do objeto frame do tello
    frame = tello.get_frame_read().frame
    # converte o frame em RGB para BGR
    frame2 = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

    #exibe na tela 'Video' cada frame obtido no laço de repeticao
    cv2.imshow('Video', frame2) 
    # quebra o laco de repeticao ao apertar a tecla 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'): 
        break
# desliga a transmissao de video
tello.streamoff()
cv2.destroyAllWindows()
