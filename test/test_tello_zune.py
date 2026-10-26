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

    @patch.object(TelloZune, 'send_cmd_return', return_value='ok')
    def test_route_active_until_executed(self, mock_send_cmd_return):
        """is_route_active só volta a False quando a fila executa o último comando da rota."""
        self.tello._execute_route(["forward 50", "cw 90"], interval=0)
        self.assertTrue(self.tello.is_route_active)
        self.assertEqual(list(self.tello.command_queue.queue),
                         ["forward 50", "cw 90", TelloZune.ROUTE_END_CMD])

        self.tello._read_queue() # forward 50
        self.tello._read_queue() # cw 90
        self.assertTrue(self.tello.is_route_active)
        self.tello._read_queue() # marcador de fim
        self.assertFalse(self.tello.is_route_active)
        # O marcador não é enviado ao drone
        self.assertEqual([c.args[0] for c in mock_send_cmd_return.call_args_list], ["forward 50", "cw 90"])

    def test_clear_command_queue_releases_route(self):
        """Limpar a fila descarta o marcador de fim, então libera a rota."""
        self.tello._execute_route(["forward 50", "cw 90"], interval=0)
        self.tello.clear_command_queue()
        self.assertFalse(self.tello.is_route_active)

    @patch('tello_zune.tello_zune.threading.Thread')
    def test_periodic_route_with_zero_interval(self, mock_thread):
        """Rota periódica com interval=0 dispara, e não dispara de novo enquanto estiver ativa."""
        self.tello.event_list = [] # Sem keep alive, para isolar o teste
        self.tello.add_periodic_event("forward 50 e cw 90", 1, "Rota", interval=0)

        self.tello._periodic_cmd()
        mock_thread.assert_called_once()
        self.assertEqual(mock_thread.call_args.kwargs['args'], (['forward 50', 'cw 90'], 0))
        self.assertTrue(self.tello.is_route_active)

        self.tello._periodic_cmd() # Rota ainda ativa: não dispara outra
        mock_thread.assert_called_once()

    def test_remove_periodic_event(self):
        """remove_periodic_event aceita string ou lista e nunca remove o keep alive."""
        self.tello.add_periodic_event("forward 50 e cw 90", 100, "Rota")
        self.tello.add_periodic_event("battery?", 100, "Bateria")

        self.tello.remove_periodic_event("forward 50 e cw 90")
        self.assertEqual([ev['commands'] for ev in self.tello.event_list], [['command'], ['battery?']])

        self.tello.remove_periodic_event(["battery?"])
        self.tello.remove_periodic_event("command")
        self.assertEqual([ev['commands'] for ev in self.tello.event_list], [['command']])

    @patch.object(TelloZune, 'send_cmd_return', return_value='ok')
    def test_takeoff_long_timeout(self, mock_send_cmd_return):
        """takeoff na fila espera a resposta por 8 s, como os movimentos."""
        self.tello.add_command("takeoff")
        self.tello._read_queue()
        mock_send_cmd_return.assert_called_once_with("takeoff", timeout=8.0)

    def test_text_emergency_skips_queue(self):
        """'emergency' no modo texto é enviado na hora e esvazia a fila."""
        self.tello.add_command("forward 100")
        self.tello._process_text_command("emergency")
        self.mock_sock_cmd.sendto.assert_called_once_with(b'emergency', ('192.168.10.1', 8889))
        self.assertEqual(self.tello.command_queue.qsize(), 0)

    @patch.object(TelloZune, 'stop_video')
    @patch.object(TelloZune, 'land')
    def test_end_tello_lands(self, mock_land, mock_stop_video):
        """end_tello pousa se o drone estiver no ar ou sem telemetria, e não pousa se estiver no chão."""
        casos = [
            # (ready, state_value, land, deve_pousar)
            (True, ['h', '50'], True, True),     # no ar
            (True, [], True, True),              # sem telemetria: pousa por segurança
            (True, ['h', '0'], True, False),     # no chão
            (False, ['h', '50'], True, False),   # nunca conectou
            (True, ['h', '50'], False, False),   # land=False
        ]
        for ready, state, land, deve_pousar in casos:
            with self.subTest(ready=ready, state=state, land=land):
                mock_land.reset_mock()
                self.tello.ready = ready
                self.tello.state_value = state
                self.tello.end_tello(land=land)
                self.assertEqual(mock_land.called, deve_pousar)

    def test_is_flying(self):
        """is_flying usa a altura 'h' da telemetria."""
        self.tello.state_value = ['h', '30']
        self.assertTrue(self.tello.is_flying())
        self.tello.state_value = ['h', '0']
        self.assertFalse(self.tello.is_flying())
        self.tello.state_value = []
        self.assertIsNone(self.tello.is_flying())

if __name__ == '__main__':
    unittest.main()