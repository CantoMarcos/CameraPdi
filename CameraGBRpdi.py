import cv2
import numpy as np
from datetime import datetime, timedelta
import base64
#from pyzbar.pyzbar import decode
import requests
import time
import os
import socketio
from collections import deque

time.sleep(10)

# Caminho para o seu arquivo txt
file_path = 'dados_recebidos.txt'
config_path = 'config.txt'

# Função para ler o arquivo e retornar os dados
def ler_dados_do_arquivo(file_path):
    dados = {}
    with open(file_path, 'r') as file:
        for line in file:
            key, value = line.strip().split(' = ')
            dados[key] = value
    return dados

def escrever_dados_no_arquivo(file_path, dados):
    try:
        with open(file_path, 'w') as file:
            for key, value in dados.items():
                file.write(f"{key} = {value}\n")
    except Exception as e:
        print(f"Erro ao escrever no arquivo: {e}")

def editar_parametro(file_path, parametro, novo_valor):
    dados = ler_dados_do_arquivo(file_path)
    if parametro in dados:
        dados[parametro] = novo_valor
        escrever_dados_no_arquivo(file_path, dados)
    else:
        print(f"Parâmetro '{parametro}' não encontrado no arquivo.")

# Função para verificar e atualizar os dados
def verificar_e_atualizar_dados():
    global dados_atuais,op, produto, subplacas, quantidade, url_send, cadastroAtivo
    novos_dados = ler_dados_do_arquivo(file_path)
    if novos_dados != dados_atuais:
        sio.disconnect()
        print("Dados alterados. Atualizando variaveis...")
        op = novos_dados['op']
        produto = novos_dados['produto']
        subplacas = novos_dados['subplacas']
        quantidade = int(novos_dados['quantidade'])
        cadastroAtivo = novos_dados['cadastroAtivo'].strip().lower() == 'true'


        # Atualizar os dados atuais
        dados_atuais = novos_dados
        return True
    return False

def limpar_dados(url_send, url_send2):
    dados_parada = {
        'mac': "mac_address",
        'is_parada': '',
        'duracao_parada': ''
    }
    print("Dados de parada enviados:", dados_parada)
    try:
        response = requests.post(url_send2, json=dados_parada)
        # Enviar solicitação GET
        response2 = requests.get(url_send2)

        # Verificar se a solicitação foi bem-sucedida
        if response2.status_code == 200:
            # Converter a resposta de JSON para um dicionário Python
            data = response2.json()
            print("Dados recebidos:", data)
        else:
            print("Falha na solicitacao, Status Code:", response2.status_code)
    except Exception as e:
        print("Erro ao enviar os dados de parada:", e)

    dados_para_enviar = {
            'mac': 'mac_address',
            'velocidade_linha': '',
            'quantidade_placas': '',
            'faltam': '',
            'quantidade_subplacas': '',
            'is_parada': '',
            'tempo_producao': '',
            'amplitude_movel': '',
            'media_amplitude_movel':'',
            'media': '',
            'mediana': '',
            'desvio_padrao': ''
        }
    print(dados_para_enviar)

    try:
        # Envia os dados para o servidor
        response = requests.post(url_send, json=dados_para_enviar)
        controle = False
        frequencia_envio = 0
    except:
        print("falha ao enviar os parametros para o servidor")

# Função para inicializar a câmera
def inicializar_camera():
    # Abrindo o vídeo
    video = cv2.VideoCapture('output4.avi')
    video.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    video.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    if not video.isOpened():
        print("Erro ao abrir a camera")
    return video

def check_position(mask, l1, l2, l3, l4):
    recorte = mask[l2:l2 + l4, l1: l1 + l3]
    brancos = cv2.countNonZero(recorte)
    return brancos != 0, brancos

def draw_inclined_line(frame, start_point, length, angle, color, thickness, point_number):
    angle_rad = np.radians(angle)
    end_point = (
        int(start_point[0] + length * np.cos(angle_rad)),
        int(start_point[1] - length * np.sin(angle_rad))
    )
    return end_point

# Cria uma instância do cliente SocketIO
sio = socketio.Client()

# Define o evento de conexão
@sio.event
def connect():
    print("Conectado ao servidor")

# Define o evento de desconexão
@sio.event
def disconnect():
    print("Desconectado do servidor")

# Inicializar os dados
dados_atuais = ler_dados_do_arquivo(file_path)
config = ler_dados_do_arquivo(config_path)

# Atribuir os valores às variáveis
ip = config['ip']
porta = int(config['port'])
op = dados_atuais['op']
produto = dados_atuais['produto']
subplacas = int(dados_atuais['subplacas'])
quantidade = int(dados_atuais['quantidade'])
cadastroAtivo = False

wsConect = False
CameraRun = True

# Loop para verificar alterações no arquivo periodicamente
try:
    while True:
        # Declaração de variáveis
        contador = 0
        contador_envio = 0
        cont = 0
        falt = 1
        contsubplac = 0
        liberado = False
        estadoParada = False
        estadoParadaAnterior = False
        tempo_parada = datetime.now()
        ultimaDeteccao = datetime.now()
        velocidade_linha = 0.0
        controle = None
        dados_para_enviar = None
        inicioParada = None
        duracaoParada = None
        contando = None
        data_atual = datetime.now().day
        blank = 0
        anteriorBrancos = 0
        isLiberado = False
        max_size = 30
        deque_tempos_entre_deteccoes = deque(maxlen=max_size)
        tempos_entre_deteccoes = []
        tempo_producao = datetime.now()
        media = 0
        mediana = 0
        moda = 0
        desvio_padrao = 0
        amplitude_movel = {0}
        media_amplitude_movel = 0

        # Inicializando sliders com valores padrão
        lower_bound = [0, 0, 180]
        upper_bound = [255, 255, 255]

        placas = 0

        url_send = f'http://{ip}:{porta}/placas'  # Ip do servidor
        url_send2 = f'http://{ip}:{porta}/parada'  # Ip do servidor
        url_send3 = f'http://{ip}:{porta}/camera'  # Ip do servidor

        if CameraRun:
            limpar_dados(url_send,url_send2)

            try:
                # Envia os dados para o servidor
                response = requests.post(url_send, json=dados_para_enviar)
                controle = False
                frequencia_envio = 0
            except:
                print("falha ao enviar os parametros para o servidor")

        # Conecta ao servidor SocketIO
        try:
            sio.connect(f'http://{ip}:{porta}')
            wsConect = True
        except Exception as e:
            print(f'ERRO COM WEBSOCKET {e}')
            wsConect = False

        # Inicializar a câmera
        video = inicializar_camera()

        print('Iniciando nova contagem em 5 segundos')
        time.sleep(5)

        while True:
            if not cadastroAtivo:
                ret, img = video.read()

                if not ret or img is None or img.size == 0:
                    print("Erro ao capturar a imagem ou imagem vazia. Tentando novamente...")
                    time.sleep(1)
                    video = inicializar_camera()
                    continue
                cv2.putText(img, f'Aguardando Envio de Cadastro', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA)
                if wsConect == True:
                    try:
                        frame = img
                        frame = cv2.resize(frame, (300, 300))
                        _, buffer = cv2.imencode('.jpg', frame)
                        frame_bytes = base64.b64encode(buffer).decode('utf-8')
                        sio.emit('frames', {'data': frame_bytes})
                    except Exception as e:
                        print('Erro3: ', e)
                        time.sleep(1)
 

                alterado = verificar_e_atualizar_dados()
                if alterado == True:
                            # Conecta ao servidor SocketIO
                    try:
                        sio.connect(f'http://{ip}:{porta}')
                        wsConect = True
                    except Exception as e:
                        print(f'ERRO COM WEBSOCKET {e}')
                        wsConect = False
                continue

            if verificar_e_atualizar_dados():
                print(f"IP: {ip}")
                print(f"Porta: {porta}")
                print(f"OP: {op}")
                print(f"Produto: {produto}")
                print(f"Subplacas: {subplacas}")
                print(f"Quantidade: {quantidade}")
                print(url_send)
                dados_parada = {
                    'mac': "mac_address",
                    'is_parada': '',
                    'duracao_parada': ''
                }
                print("Dados de parada enviados:", dados_parada)
                try:
                    response = requests.post(url_send2, json=dados_parada)
                    # Enviar solicitação GET
                    response2 = requests.get(url_send2)

                    # Verificar se a solicitação foi bem-sucedida
                    if response2.status_code == 200:
                        # Converter a resposta de JSON para um dicionário Python
                        data = response2.json()
                        print("Dados recebidos:", data)
                    else:
                        print("Falha na solicitacao, Status Code:", response2.status_code)
                except:
                    print("erro ao enviar os dados de parada")

                dados_para_enviar = {
                    'mac': 'mac_address',
                    'velocidade_linha': '',
                    'quantidade_placas': '',
                    'faltam': '',
                    'quantidade_subplacas': '',
                    'is_parada': '',
                    'tempo_producao': '',
                    'amplitude_movel': '',
                    'media_amplitude_movel':'',
                    'media': '',
                    'mediana': '',
                    'desvio_padrao': ''
                }
                print(dados_para_enviar)

                try:
                    # Envia os dados para o servidor
                    response = requests.post(url_send, json=dados_para_enviar)
                    controle = False
                    frequencia_envio = 0
                except:
                    print("falha ao enviar os parametros para o servidor")

                # Reiniciar o loop externo

                
                break

            ret, img = video.read()

            if not ret or img is None or img.size == 0:
                print("Erro ao capturar a imagem ou imagem vazia. Tentando novamente...")
                time.sleep(1)
                video = inicializar_camera()
                continue

            # Define a linha de detecção
            height, width = img.shape[:2]

            # Coordenadas da região de interesse (ROI)
            linha_y = int(height * 0.2)
            linha_y2 = int(height * 0.48)
            coluna_x = int(width // 7)

            end_point1 = draw_inclined_line(img, (0, 200), width - 50, 15, (0, 0, 255), 2, 1)  # Linha superior
            end_point2 = draw_inclined_line(img, (0, 295), width - 50 , 17, (0, 0, 255), 2, 3)  # Linha inferior
            end_point3 = draw_inclined_line(img, (0, 100), height, -60, (0, 255, 0), 2, 5)  # Linha vertical

            # Define os pontos da ROI inclinada
            roi_points = np.array([[0, 200], [end_point1[0], end_point1[1]], [end_point2[0], end_point2[1]], [0, 295]], dtype=np.int32)

            # Cria uma máscara para a ROI inclinada
            mask = np.zeros_like(img)
            cv2.fillPoly(mask, [roi_points], (255, 255, 255))

            # Aplica a máscara ao frame para obter a ROI inclinada
            roi = cv2.bitwise_and(img, mask)

            # Converte a ROI para o espaço de cor HSV
            hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

            # Criando uma máscara usando a faixa de cores especificada
            mascara = cv2.inRange(hsv, np.array(lower_bound), np.array(upper_bound))

            # Encontra os contornos na máscara
            contornos, _ = cv2.findContours(mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for contorno in contornos:
                area = cv2.contourArea(contorno)
                if 500 < area < 6000:  # Filtro para evitar contornos muito pequenos
                    x, y, w, h = cv2.boundingRect(contorno)
                    # Desenha o retângulo no frame, ajustando para as coordenadas da ROI
                    cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)

            # Fim do Processamento de Imagem
            agora = datetime.now()

            # Quadrado para detectar se chegou na posicao
            l1, l2, l3, l4 = 100, 10, 20, 200
            liberado, brancos = check_position(mascara, l1, l2, l3, l4)

            if anteriorBrancos == 0 and brancos != 0:
                count = 0
                for contorno in contornos:
                    area = cv2.contourArea(contorno)
                    if 500 < area < 6000:  # Filtro para evitar contornos muito pequenos
                        x, y, w, h = cv2.boundingRect(contorno)
                        cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
                        count += 1 
                        if count > 0:
                            isLiberado = True
                if isLiberado:
                    contsubplac += count
                    blank += 1
                    falt = quantidade - blank
                    agora = datetime.now()

                                        # Adicione o tempo entre detecções à lista
                    if ultimaDeteccao:
                        tempo_producao = round((agora - ultimaDeteccao).total_seconds(), 2)
                        deque_tempos_entre_deteccoes.append(tempo_producao)
                        tempos_entre_deteccoes = list(deque_tempos_entre_deteccoes)

                        # Calculando a média, mediana e moda
                        media = round(np.mean(tempos_entre_deteccoes), 3)

                        # Calcula a amplitude móvel
                        amplitude_movel = np.abs(np.diff(tempos_entre_deteccoes)),
                        amplitude_movel2 = np.round(amplitude_movel, 3).tolist()
                        print(f'amplitude movel:  {amplitude_movel2}')

                        # Calcula a média das amplitudes móveis
                        media_amplitude_movel = np.round(np.mean(amplitude_movel), 3)
                        print(f'media_amplitude_movel {media_amplitude_movel}')

                        mediana = round(np.median(tempos_entre_deteccoes), 3)
                        desvio_padrao = round(np.std(tempos_entre_deteccoes), 3)



                    print(tempos_entre_deteccoes)
                    print(f'media: {media}')
                    print(f'mediana: {mediana}')
                    print(f'desvio padrao: {desvio_padrao}')


                    ultimaDeteccao = agora
                    if estadoParada and cadastroAtivo:
                        duracaoParada = agora - inicioParada
                        dados_parada = {
                            'mac': "mac_address",
                            'is_parada': True,
                            'duracao_parada': int(duracaoParada.total_seconds())
                        }
                        print("Dados de parada enviados:", dados_parada)
                        try:
                            response = requests.post(url_send2, json=dados_parada)
                            response2 = requests.get(url_send2)
                            if response2.status_code == 200:
                                data = response2.json()
                                print("Dados recebidos:", data)
                            else:
                                print("Falha na solicitacao, Status Code:", response2.status_code)
                        except:
                            print("erro ao enviar os dados de parada")
                        time.sleep(1)
                        estadoParada = False
                    isLiberado = False

            anteriorBrancos = brancos

            # Critério de parada
            if agora - ultimaDeteccao > timedelta(seconds=120) and not estadoParada:
                estadoParada = True
                inicioParada = ultimaDeteccao  # Usa o tempo da última detecção como início da parada
                print("Linha Parada.")

            # Calcula a velocidade da linha
            segundos_passados = (datetime.now() - tempo_parada).total_seconds()
            if segundos_passados > 0:
                velocidade_linha = contador / segundos_passados * 60
            else:
                velocidade_linha = 0

            # Condição que acumula os dados para enviá-los para o servidor a cada minuto
            current_second = datetime.now().second
            if current_second % 30 == 0 and blank > 0:
                frequencia_envio = round(blank / 10, 3)
                dados_para_enviar = {
                    'mac': 'mac_address',
                    'velocidade_linha': frequencia_envio,
                    'quantidade_placas': blank,
                    'faltam': falt,
                    'quantidade_subplacas': contsubplac,
                    'is_parada': estadoParada,
                    'tempo_producao': tempos_entre_deteccoes,
                    'amplitude_movel': amplitude_movel2,
                    'media_amplitude_movel':media_amplitude_movel,
                    'media': media,
                    'mediana': mediana,
                    'desvio_padrao': desvio_padrao
                }
                controle = True

            try:
                if datetime.now().second % 30 == 1 and controle == True:
                    print(dados_para_enviar)
                    response = requests.post(url_send, json=dados_para_enviar)
                    controle = False
                    frequencia_envio = 0
                    time.sleep(1)
            except:
                print("falha ao enviar os parametros para o servidor")
                time.sleep(1)

            # Fim de desenhos e texto

            cv2.putText(img, f'Quantidade blank: {blank}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA)
            cv2.putText(img, f'Quantidade subplac: {contsubplac}', (10, 55), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA)

            if wsConect == True:
                try:
                    frame = img
                    frame = cv2.resize(frame, (300, 300))
                    _, buffer = cv2.imencode('.jpg', frame)
                    frame_bytes = base64.b64encode(buffer).decode('utf-8')
                    sio.emit('frames', {'data': frame_bytes})
                except Exception as e:
                    print('Erro3: ', e)
                    time.sleep(1)

            if falt <= 0:
                dados_para_enviar = {
                    'mac': 'mac_address',
                    'velocidade_linha': frequencia_envio,
                    'quantidade_placas': blank,
                    'faltam': falt,
                    'quantidade_subplacas': contsubplac,
                    'is_parada': estadoParada,
                }
                requests.post(url_send, json=dados_para_enviar)
                # Editar o valor de 'cadastroAtivo'
                editar_parametro(file_path, 'cadastroAtivo', 'False')
                falt = 1



            key = cv2.waitKey(20)
            if key == 27:
                break
            time.sleep(0.01)

except KeyboardInterrupt:
    print("Interrupção manual. Saindo do programa.")
    video.release()
    cv2.destroyAllWindows()
