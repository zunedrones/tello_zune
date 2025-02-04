## **Utilização:**
### Instalação

```bash
# Clone o repositório
git clone https://github.com/heltonmaia/proj_drone_tello
```

```bash
# Instalar dependências
pip install opencv-python
pip install pyzbar
pip install tello_zune
```

### Funcionamento
O algoritmo detecta QR codes, envia comandos ao drone via Wi-Fi e processa os dados recebidos. Para usar, conecte-se ao drone e execute main.py. Um local bem iluminado é essencial para imagens nítidas.

Comandos como "down 20" executam movimentos com o passo definido pelo usuário. Sem detecção por um tempo pré-configurado, o drone rotaciona para buscar códigos. Com o comando "follow", ajusta sua posição conforme as coordenadas detectadas.

#### Exemplos de comandos válidos:

| Comando         | Descrição                    |
|-----------------|------------------------------|
| `takeoff`       | Decolar                      |
| `land`          | Pousar                       |
| `up x`          | Subir x cm                   |
| `down x`        | Descer x cm                  |
| `right x`       | Mover-se à direita x cm      |
| `left x`        | Mover-se à esquerda x cm     |
| `forward x`     | Mover-se para frente x cm    |
| `back x`        | Mover-se para trás x cm      |
| `follow`        | Seguir                       |
