import numpy as np

Width = 544
Height = 306
#coordenadas do centro
CenterX = Width // 2
CenterY = Height // 2
#erro anterior
prevErrorX = 0
prevErrorY = 0
#coeficiente proporcional (obtido testando)
#determina o quanto a velocidade deve mudar em resposta ao erro atual
Kp = 0.35
#coeficiente derivativo (obtido testando)
#responsável por controlar a taxa de variação do erro
Kd = 0.35

width_detect = 0

def centralize(tello, values_detect):
    global prevErrorX, prevErrorY, CenterX, CenterY, Kp, Kd, width_detect
    frame, x1, y1, x2, y2, detections = values_detect
    speedFB = 0
    # detectWidth = x2 - x1
    cxDetect = (x2 + x1) // 2
    cyDetect = (y2 + y1) // 2

    #PID - Speed Control
    width_detect = x2 - x1
    width_land = 0
    
    #se o centro da detecção encontrar-se na esquerda, o erro  na horizontal será negativo
    #se o objeto estiver na direita, o erro será positivo
    if (detections > 0):
        errorX = cxDetect - CenterX
        errorY = CenterY - cyDetect
        if width_detect < 270:
            speedFB = 33
            print(f"WIDTH: {width_detect}")
        if width_detect > 150:
            width_land = width_detect
    else:
        errorX = 0
        errorY = 0
        print("0 DETECTIONS")

        if tello.get_height() <= 30:
            print("TENTEI POUSAR")
            tello.send_rc_control(0, 0, 0, 0)
            tello.move_forward(25)
            tello.land()
    
    print(f"ALTURA: {tello.get_height()}")
    #velocidade de rotação em torno do próprio eixo é calculada em relação ao erro horizontal
    speedYaw = Kp*errorX + Kd*(errorX - prevErrorX)
    speedUD = Kp*errorY + Kd*(errorY - prevErrorY)
    #não permite que a velocidade 'vaze' o intervalo -100 / 100
    speedYaw = int(np.clip(speedYaw,-100,100))
    speedUD = int(np.clip(speedUD,-100,100))
    
    if(detections != 0):
        tello.send_rc_control(0, speedFB, speedUD, speedYaw)
    else:
        tello.send_rc_control(0, 0, 0, 0)
    #o erro atual vira o erro anterior
    prevErrorX = errorX
    prevErrorY = errorY

