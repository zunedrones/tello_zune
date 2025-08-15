import threading

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

def process_ai_command(tello: object, command: str):
     """
     Processa comandos da IA
     Args:
         tello (object): Objeto da classe TelloZune, que possui métodos para enviar comandos e obter estado.
         command (str): Comando a ser processado.
     """
     base_cmd = command.split()[0] if ' ' in command else command # Caso tenha espaço, pega apenas o comando
     if base_cmd in VALID_COMMANDS:
        tello.add_command(command) # type: ignore

