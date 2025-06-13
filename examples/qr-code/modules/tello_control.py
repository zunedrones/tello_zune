import time
import threading
from .tracking_base import follow, draw
from .qr_processing import process

old_move = ''
following_qr = False
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

def process_ai_command(tello: object, command: str):
     """
     Processa comandos da IA
     Args:
         tello (object): Objeto da classe TelloZune, que possui métodos para enviar comandos e obter estado.
         command (str): Comando a ser processado.
     """
     base_cmd = command.split()[0] if ' ' in command else command # Caso tenha espaço, pega apenas o comando
     if base_cmd in VALID_COMMANDS:
        tello.add_command(command)

def moves(tello: object, frame: object) -> object:
    """
    Executa movimentos do drone
    Args:
        tello (object): Objeto da classe TelloZune, que possui métodos para enviar comandos e obter estado.
        frame (object): Frame atual da câmera.
    Returns:
        object: Frame atualizado.
    """
    global old_move, pace, searching, stop_searching, following_qr
    
    frame, x1, y1, x2, y2, detections, text = process(frame)
    
    if following_qr and (detections != 1 or text != 'follow'):
        # Para o drone se perder o QR code de follow
        tello.send_rc_control(0, 0, 0, 0)
        following_qr = False

    if detections == 1:
        if text == 'follow':
            frame = follow(tello, frame, x1, y1, x2, y2, detections, text)
            following_qr = True  # Ativa estado de seguimento

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