import numpy as np
import cv2

Width = 960
Height = 720
#coordenadas do centro
CenterX = Width // 2
CenterY = Height // 2
#erro anterior
prevErrorX = 0
prevErrorY = 0
#coeficiente proporcional (obtido testando)
#determina o quanto a velocidade deve mudar em resposta ao erro atual
Kp = 0.2
#coeficiente derivativo (obtido testando)
#responsável por controlar a taxa de variação do erro
Kd = 0.2

width_detect = 0
text = ''

def follow(tello: object, frame: object, x1: int, y1: int, x2: int, y2: int, detections: int, text: str) -> object:
    '''
    Processa o frame para detectar QR codes e executa comandos no drone Tello com base no texto detectado.
    Args:
        tello: Objeto representando o drone Tello, que possui métodos para enviar comandos e obter estado.
        frame: Frame de vídeo a ser processado para detecção de QR codes.
        x1: Coordenada x do canto superior esquerdo do retângulo.
        y1: Coordenada y do canto superior esquerdo do retângulo.
        x2: Coordenada x do canto inferior direito do retângulo.
        y2: Coordenada y do canto inferior direito do retângulo.
        detections: Número de QR codes detectados no frame.
        text: Texto detectado nos QR codes.
    Returns:
        frame: Frame processado após a detecção e execução dos comandos.
    '''
    global prevErrorX, prevErrorY, CenterX, CenterY, Kp, Kd
    #_, x1, y1, x2, y2, detections, text = process(frame)
    speedFB = 0
    cxDetect = (x2 + x1) // 2
    cyDetect = (y2 + y1) // 2

    #PID - Speed Control
    area = (x2 - x1) * (y2 - y1)
    #print(f"Area: {area}")
    #print(f"DETECTIONS: {detections}")
    #se o centro da detecção encontrar-se na esquerda, o erro na horizontal será negativo
    #se o objeto estiver na direita, o erro será positivo
    if (detections > 0):
        errorX = cxDetect - CenterX
        #print(errorX)
        errorY = CenterY - cyDetect
        #print(errorY)
        cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 255), 2)
        cv2.circle(frame, (cxDetect, cyDetect), 5, (0, 0, 255), -1)
        cv2.putText(frame, text, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 2)
        cv2.circle(frame, (CenterX, CenterY), 5, (0, 255, 255), -1)
        cv2.line(frame, (CenterX, CenterY), (cxDetect, cyDetect), (255, 255, 0), 2)
        if area < 20000: 
            speedFB = 25
        elif area > 80000: # menor
            speedFB = -25
            #print(f"AREA: {area}")
    else:
        errorX = 0
        errorY = 0
        #print("0 DETECTIONS")
        #print(f"AREA: {area_land}")

    #velocidade de rotação em torno do próprio eixo é calculada em relação ao erro horizontal
    speedYaw = Kp*errorX + Kd*(errorX - prevErrorX)
    speedUD = Kp*errorY + Kd*(errorY - prevErrorY)
    #não permite que a velocidade 'vaze' o intervalo -100 / 100
    speedYaw = int(np.clip(speedYaw,-100,100))
    speedUD = int(np.clip(speedUD,-100,100))
    
    #print(f"FB: {speedFB}, UD: {speedUD}, YAW: {speedYaw}")
    tello.send_rc_control(0, speedFB, speedUD, speedYaw)
    print(f'FB: {speedFB}, UD: {speedUD}, Yaw: {speedYaw}')
    
    #o erro atual vira o erro anterior
    prevErrorX = errorX
    prevErrorY = errorY
    return frame

def draw(frame: object, x1: int, y1: int, x2: int, y2: int, text: str) -> object:
    '''
    Desenha um retângulo e o texto detectado no frame.
    Args:
        frame: Frame de vídeo a ser processado.
        x1: Coordenada x do canto superior esquerdo do retângulo.
        y1: Coordenada y do canto superior esquerdo do retângulo.
        x2: Coordenada x do canto inferior direito do retângulo.
        y2: Coordenada y do canto inferior direito do retângulo.
        text: Texto a ser exibido no frame.
    Returns:
        frame: Frame com o retângulo e o texto desenhados.
    '''
    cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 255), 2)
    cv2.putText(frame, text, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 2)
    return frame

