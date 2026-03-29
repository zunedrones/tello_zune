import unittest
from unittest.mock import patch, MagicMock
import threading
import time

# Importa a sua classe (certifique-se de que o arquivo principal se chama tello_zune.py)
from tello_zune.tello_zune import TelloZune

class TestTelloZune(unittest.TestCase):

    @patch('tello_zune.tello_zune.socket.socket')
    def setUp(self, mock_socket):
        """
        Configuração inicial antes de cada teste.
        Mockamos o socket para evitar que a classe tente abrir portas UDP reais no PC.
        """
        # Cria a instância sem habilitar o input de texto para não travar os testes
        self.tello = TelloZune(text_input=False)
        
        # Facilita o acesso aos mocks dos sockets
        self.mock_sock_cmd = self.tello.sock_cmd
        self.mock_sock_state = self.tello.sock_state

    def tearDown(self):
        """Limpeza após cada teste."""
        self.tello.stop_communication()

    def test_send_cmd(self):
        """Testa se o envio assíncrono de comandos formata e envia os bytes corretamente."""
        comando = "forward 50"
        self.tello.send_cmd(comando)
        
        # Verifica se o socket enviou os bytes corretos para o IP/Porta do Tello
        self.mock_sock_cmd.sendto.assert_called_once_with(
            b'forward 50', 
            ('192.168.10.1', 8889)
        )

    @patch('tello_zune.tello_zune.threading.Event.wait')
    def test_send_cmd_return(self, mock_wait):
        """Testa o envio síncrono simulando uma resposta do drone."""
        comando = "battery?"
        resposta_simulada = "85"
        
        # Simulamos que a thread recebedora preencheu a variável de retorno
        # antes do 'wait' ser liberado
        def side_effect(*args, **kwargs):
            self.tello.udp_cmd_ret = resposta_simulada
            return True
        mock_wait.side_effect = side_effect

        resultado = self.tello.send_cmd_return(comando)
        
        self.assertEqual(resultado, "85")
        self.mock_sock_cmd.sendto.assert_called_once_with(b'battery?', ('192.168.10.1', 8889))

    def test_get_speed_parsing(self):
        """Testa se a extração de velocidade funciona e lida com erros."""
        # Cenário 1: Estado populado corretamente
        self.tello.state_value = ['vgx', '15', 'vgy', '-10', 'vgz', '0']
        vx, vy, vz = self.tello.get_speed()
        self.assertEqual(vx, 15.0)
        self.assertEqual(vy, -10.0)
        self.assertEqual(vz, 0.0)

        # Cenário 2: Estado vazio ou corrompido (deve retornar 0,0,0 sem quebrar)
        self.tello.state_value = []
        vx, vy, vz = self.tello.get_speed()
        self.assertEqual((vx, vy, vz), (0.0, 0.0, 0.0))

    @patch.object(TelloZune, 'send_cmd_return')
    @patch('time.sleep') # Evita que o teste fique lento por causa do sleep
    def test_land_timeout_loop(self, mock_sleep, mock_send_cmd_return):
        """Garante que a função land não entra em loop infinito se o drone não responder 'ok'."""
        # Simulamos o drone retornando 'error' continuamente
        mock_send_cmd_return.return_value = 'error'
        
        # Executa o land
        self.tello.land()
        
        # Verifica se tentou exatamente o número máximo de vezes (1 chamada inicial + 3 retentativas = 4)
        self.assertEqual(mock_send_cmd_return.call_count, 4)

    def test_add_command_and_clear_queue(self):
        """Testa se a fila de comandos enfileira e limpa corretamente."""
        self.tello.add_command("takeoff")
        self.tello.add_command("forward 100")
        
        self.assertEqual(self.tello.command_queue.qsize(), 2)
        
        self.tello.clear_command_queue()
        self.assertEqual(self.tello.command_queue.qsize(), 0)

    @patch.object(TelloZune, 'add_command')
    def test_execute_route(self, mock_add_command):
        """Testa se as rotas inserem comandos e delays adequadamente."""
        comandos = ["takeoff", "forward 50", "land"]
        
        self.tello._execute_route(comandos, interval=2)
        
        # Verifica as chamadas exatas que deveriam ir para a fila
        expected_calls = [
            unittest.mock.call("takeoff"),
            unittest.mock.call("delay 2"),
            unittest.mock.call("forward 50"),
            unittest.mock.call("delay 2"),
            unittest.mock.call("land")
        ]
        mock_add_command.assert_has_calls(expected_calls, any_order=False)

if __name__ == '__main__':
    unittest.main()