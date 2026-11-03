import unittest
from unittest.mock import patch, MagicMock
import threading
import time
import numpy as np

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

    def _feed_frames(self, frames):
        """Simula o stream de vídeo entregando os frames dados, um por chamada de _video()."""
        self.tello.video = MagicMock()
        self.tello.video.read.side_effect = [(True, f) for f in frames]
        for _ in frames:
            self.tello._video()

    def test_get_frame_returns_latest(self):
        """get_frame() deve entregar o frame mais recente, não o primeiro que entrou na fila."""
        frames = [np.full((720, 960, 3), i, dtype=np.uint8) for i in range(3)]
        self._feed_frames(frames)
        self.assertEqual(self.tello.get_frame()[0, 0, 0], 2)

    def test_get_frame_stamped(self):
        """get_frame_stamped() devolve frame novo com timestamp e None quando não há frame novo."""
        self._feed_frames([np.zeros((720, 960, 3), dtype=np.uint8)])
        result = self.tello.get_frame_stamped(timeout=0.1)
        self.assertIsNotNone(result)
        frame, stamp = result
        self.assertEqual(frame.shape, (720, 960, 3))
        self.assertAlmostEqual(stamp, time.time(), delta=1.0)
        # O mesmo frame não é entregue duas vezes
        self.assertIsNone(self.tello.get_frame_stamped(timeout=0.05))

    def test_video_resizes_frames(self):
        """Frames de tamanho diferente de image_size são redimensionados."""
        self._feed_frames([np.zeros((360, 480, 3), dtype=np.uint8)])
        frame, _ = self.tello.get_frame_stamped(timeout=0.1)
        self.assertEqual(frame.shape, (720, 960, 3))

    def test_get_state(self):
        """get_state() converte todos os campos numéricos e marca o instante de chegada."""
        self.tello.sock_state.recvfrom.return_value = (
            b'pitch:1;roll:-2;yaw:90;vgx:3;tof:85;mpry:0,0,0;bat:77;\r\n', None)
        self.tello._state_receive()
        state = self.tello.get_state()
        self.assertEqual(state['pitch'], 1.0)
        self.assertEqual(state['roll'], -2.0)
        self.assertEqual(state['yaw'], 90.0)
        self.assertEqual(state['tof'], 85.0)
        self.assertEqual(state['bat'], 77.0)
        self.assertNotIn('mpry', state)
        self.assertAlmostEqual(self.tello.state_stamp, time.time(), delta=1.0)

    def test_get_state_field_last_key(self):
        """get_state_field() não quebra se a chave for o último elemento."""
        self.tello.state_value = ['bat', '80', 'tof']
        self.assertEqual(self.tello.get_state_field('tof'), '')

    def test_send_rc_control_saturates(self):
        """Valores de rc são arredondados e saturados em -100~100."""
        self.tello.send_rc_control(150, -150, 10.6, 0)
        self.mock_sock_cmd.sendto.assert_called_once_with(b'rc 100 -100 11 0', ('192.168.10.1', 8889))

    def test_rc_watchdog(self):
        """Com watchdog ativo, envia 'rc 0 0 0 0' quando o último rc em movimento fica velho."""
        self.tello.send_rc_control(0, 20, 0, 0)
        self.mock_sock_cmd.sendto.reset_mock()

        self.tello._check_rc_watchdog() # Desativado: não faz nada
        self.mock_sock_cmd.sendto.assert_not_called()

        self.tello.set_rc_watchdog(0.3)
        self.tello._check_rc_watchdog() # rc recente: não faz nada
        self.mock_sock_cmd.sendto.assert_not_called()

        self.tello.last_rc_control_timestamp -= 1.0
        self.tello._check_rc_watchdog()
        self.mock_sock_cmd.sendto.assert_called_once_with(b'rc 0 0 0 0', ('192.168.10.1', 8889))

        # Já parado: não reenvia
        self.mock_sock_cmd.sendto.reset_mock()
        self.tello.last_rc_control_timestamp -= 1.0
        self.tello._check_rc_watchdog()
        self.mock_sock_cmd.sendto.assert_not_called()

if __name__ == '__main__':
    unittest.main()