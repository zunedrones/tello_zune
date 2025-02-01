import logging
import time
import threading
from .tracking_base import follow, draw
from .qr_processing import process

old_move = ''
pace = ' 70'
pace_moves = ['up', 'down', 'left', 'right', 'forward', 'back', 'cw', 'ccw']
searching = False
stop_searching = threading.Event()
response = ''

def search(tello: object):
    '''
    Procura por QR codes rotacionando o drone Tello em 20 graus para a direita e 40 graus para a esquerda.
    Args:
        tello: Objeto da classe TelloZune, que possui métodos para enviar comandos e obter estado.
    '''
    timer = time.time()
    i = 0
    commands = ['ccw 20', 'cw 50']
    while not stop_searching.is_set() and not tello.stop_receiving.is_set():
        if time.time() - timer >= 5:                 # 10 segundos
            response = tello.send_cmd(commands[i])   # Rotaciona 20 graus
            time.sleep(0.1)                          # Testar se resposta é exibida
            print(f"{commands[i]}, {response}")
            #logging.info(response)
            timer = time.time()
            i = (i + 1) % 2                          # Alterna entre 0 e 1
            time.sleep(0.01)
        #print((time.time() - timer).__round__(2)) # Ver contagem regressiva

def moves(tello: object, frame: object) -> object:
    '''
    Processa o frame para detectar QR codes e executa comandos no drone Tello com base no texto detectado.
    Args:
        tello: Objeto da classe TelloZune, que possui métodos para enviar comandos e obter estado.
        frame: Frame de vídeo a ser processado para detecção de QR codes.
    Returns:
        frame: Frame processado após a detecção e execução dos comandos.
    '''
    global old_move, pace, pace_moves, searching, response
    frame, x1, y1, x2, y2, detections, text = process(frame) # Agora process() retorna os valores de x1, y1, x2, y2, para ser chamada apenas uma vez

    if detections == 0 and old_move != 'land': # Se pousou, não deve rotacionar
        if not searching:
            stop_searching.clear()                                         # Reseta o evento de parada
            search_thread = threading.Thread(target=search, args=(tello,)) # Cria a thread de busca
            search_thread.start()                                          # Inicia a thread
            searching = True

        elif old_move == 'follow': # Necessário para que o drone não continue a se movimentar sem detecção de follow
            tello.send_rc_control(0, 0, 0, 0)

    elif detections == 1:
        if searching:
            stop_searching.set() # Setar evento de parada
            searching = False    # Parar busca

        if text == 'follow':
            frame = follow(tello, frame, x1, y1, x2, y2, detections, text)
            logging.info(text)

        elif text == 'land' and old_move != 'land':
            while float(tello.get_state_field('h')) >= 13:
                tello.send_rc_control(0, 0, -70, 0)
            tello.send_cmd(str(text))
            logging.info(f"{text}+' '{response}")

        elif text == 'takeoff' and old_move != 'takeoff':
            tello.send_cmd(text)
            time.sleep(0.1)
            print(text)
            logging.info(text)

        elif text in pace_moves:
            frame = draw(frame, x1, y1, x2, y2, text)
            if old_move != text: # Não deve fazer comandos repetidos
                with tello.queue_lock:
                    tello.command_queue.append(f"{text}{pace}")
                    #print(command_queue)
                logging.info(f"{text}{pace}, {response}")

    old_move = text
    #print(f"Old move: {old_move}")
    return frame