import time
import threading
from tracking_base import follow, draw
from qr_processing import process

old_move = ''
pace = ' 50'
VALID_COMMANDS = [
    'takeoff', 'land', 'up', 'down', 'left', 'right', 'forward', 'back', 'cw', 'ccw'
]
searching = False
enable_search = False
stop_searching = threading.Event()
response = ''
log_messages = []
last_command_time = {} # Dicionário para armazenar o tempo do último envio de cada comando

def search(tello: object):
    """
    Procura por QR codes rotacionando o drone Tello em 20 graus para a direita e 40 graus para a esquerda.
    Args:
        tello: Objeto da classe TelloZune, que possui métodos para enviar comandos e obter estado.
    """
    timer = time.time()
    i = 0
    commands = ['ccw 20', 'cw 50']
    while not stop_searching.is_set() and not tello.stop_receiving.is_set() and enable_search:
        if time.time() - timer >= 10:                # 10 segundos
            tello.add_command(commands[i])          # Rotaciona
            time.sleep(0.1)                          # Testar se resposta é exibida
            print(f"{commands[i]}, {response}")
            log_messages.append(f"{commands[i]}, {response}\n")
            timer = time.time()
            i = (i + 1) % 2                          # Alterna entre 0 e 1
            time.sleep(0.01)
        #print((time.time() - timer).__round__(2)) # Ver contagem regressiva

def moves(tello: object, frame: object) -> object:
    """
    Executa movimentos do drone
    Args:
        tello (object): Objeto da classe TelloZune, que possui métodos para enviar comandos e obter estado.
        frame (object): Frame atual da câmera.
    Returns:
        object: Frame atualizado.
    """
    global old_move, pace, searching, stop_searching

    frame, x1, y1, x2, y2, detections, text = process(frame)

    if detections == 0 and old_move != 'land' and enable_search:
        if not searching:
            stop_searching.clear()
            search_thread = threading.Thread(target=search, args=(tello,))
            search_thread.daemon = True
            search_thread.start()
            searching = True

    elif detections == 1:
        if searching:
            stop_searching.set()
            searching = False

        if text == 'follow':
            frame = follow(tello, frame, x1, y1, x2, y2, detections, text)

        else:
            frame = draw(frame, x1, y1, x2, y2, text)

            if text in ['land', 'takeoff'] and old_move != text:
                tello.add_command(text)
                log_messages.append(text)

            current_time = time.time()
            if text in VALID_COMMANDS[2:]:
                last = last_command_time.get(text, 0)
                if old_move != text or (current_time - last > 10):
                    tello.add_command(f"{text}{pace}")
                    log_messages.append(f"{text}{pace}")
                    last_command_time[text] = current_time

    old_move = text
    return frame