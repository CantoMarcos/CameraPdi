# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify,render_template, render_template_string, redirect, url_for, session
import socketio
import time
import psutil
import socket
import os
import numpy as np


app = Flask(__name__)
app.secret_key = 'your_secret_key'
sio = socketio.Server(cors_allowed_origins='*')
app.wsgi_app = socketio.WSGIApp(sio, app.wsgi_app)

data_store = {}
data_cadastro = {}
data_parada = {}
data_camera = {}
data_store = {}

# Configurações globais de IP e Porta
app.config['IP'] = 'default_ip'
app.config['PORTA'] = 'default_porta'

def has_ethernet_ip(interface_name="eth0"):
    addrs = psutil.net_if_addrs()
    if interface_name in addrs:
        for addr in addrs[interface_name]:
            if addr.family == socket.AF_INET:  # Verifica se é um endereço IPv4
                return True
    return False

def wait_for_ethernet_ip(interface_name="eth0"):
    print(f"Aguardando endereço IP na interface {interface_name}...")
    while not has_ethernet_ip(interface_name):
        time.sleep(5)  # Espera 5 segundos antes de tentar novamente
    print(f"Endereço IP detectado na interface {interface_name}. Iniciando o servidor...")


@app.route('/placas', methods=['POST', 'GET'])
def parametros_reais():
    if request.method == 'POST':
        dados = request.json
        data_store.update(dados)
        return jsonify({'message': 'Dados recebidos com sucesso'}), 200
    elif request.method == 'GET':
        if 'tempo_producao' in data_store:
            tempos_entre_deteccoes = data_store['tempo_producao']
            media = data_store['media']
            desvio_padrao = data_store['desvio_padrao']
            
            # Limites de Especificação
            LSE = 70  # Exemplo de valor, você deve usar os valores reais
            LIE = 50  # Exemplo de valor, você deve usar os valores reais
            
            # Calcular os índices de capacidade
            Cp = round((LSE - LIE) / (6 * desvio_padrao), 3)
            Cps = round(Cp - (abs(media - (LSE + LIE) / 2) / (3 * desvio_padrao)), 3)
            Cpk = round(min((LSE - media) / (3 * desvio_padrao), (media - LIE) / (3 * desvio_padrao)), 3)
            sigma_total = desvio_padrao  # Se você tem uma medida separada de sigma total, use-a aqui
            Cpi = round(min((LSE - media) / (3 * sigma_total), (media - LIE) / (3 * sigma_total)), 3)
            
            # Calcular os limites de controle
            E2 = 0.5477  # Constante para n = 2
            amplitudes_moveis = np.abs(np.diff(tempos_entre_deteccoes))
            media_amplitude_movel = np.mean(amplitudes_moveis)
            LCS_X = media + E2 * media_amplitude_movel
            LCI_X = media - E2 * media_amplitude_movel
            LC = media

            # Gerar valores para a curva de Gauss
            x = np.linspace(media - 3 * desvio_padrao, media + 3 * desvio_padrao, 100)
            y = (1 / (desvio_padrao * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((x - media) / desvio_padrao) ** 2)
            data_store['x'] = x.tolist()
            data_store['y'] = y.tolist()
            
            data_store['Cp'] = Cp
            data_store['Cps'] = Cps
            data_store['Cpk'] = Cpk
            data_store['Cpi'] = Cpi
            data_store['LCS_X'] = LCS_X
            data_store['LCI_X'] = LCI_X
            data_store['LC'] = LC

        return jsonify(data_store), 200

@app.route('/cadastro', methods=['POST', 'GET'])
def cadastro():
    if request.method == 'POST':
        dados = request.json
        data_cadastro.update(dados)
        op = dados.get('op', '')
        produto = dados.get('produto', '')
        subplacas = dados.get('subplacas', '')
        quantidade = dados.get('quantidade', '')
        cadastroAtivo = dados.get('cadastroAtivo', False)  # Pega o valor de cadastroAtivo
        
        #ip = app.config['IP']
        #porta = app.config['PORTA']
        
        with open('dados_recebidos.txt', 'w') as f:
            #f.write(f"ip = {ip}\n")
            #f.write(f"porta = {porta}\n")
            f.write(f"op = {op}\n")
            f.write(f"produto = {produto}\n")
            f.write(f"subplacas = {subplacas}\n")
            f.write(f"quantidade = {quantidade}\n")
            f.write(f"cadastroAtivo = {cadastroAtivo}\n")  # Adiciona cadastroAtivo ao arquivo
        
        return jsonify({'message': 'Dados recebidos com sucesso.'}), 200
    elif request.method == 'GET':
        return jsonify(data_cadastro), 200


@app.route('/parada', methods=['POST', 'GET'])
def parada():
    if request.method == 'POST':
        dados = request.json
        data_parada.update(dados)
        return jsonify({'message': 'Dados de parada recebidos com sucesso'}), 200
    elif request.method == 'GET':
        return jsonify(data_parada), 200

@app.route('/camera', methods=['POST', 'GET'])
def camera():
    if request.method == 'POST':
        dados = request.json
        data_camera.update(dados)
        return jsonify({'message': 'Dados de câmera recebidos com sucesso.'}), 200
    elif request.method == 'GET':
        return jsonify(data_camera), 200
    
@app.route('/config', methods=['POST'])
def save_config():
    config_data = request.json
    app.config['IP'] = config_data.get('ip')
    app.config['PORTA'] = config_data.get('porta')
    return jsonify({'message': 'Configuração salva com sucesso.'}), 200

@sio.event
def connect(sid, environ):
    print("Client connected:", sid)

@sio.event
def disconnect(sid):
    print("Client disconnected:", sid)

@sio.event
def frames(sid, data):
    sio.emit('frames', data, skip_sid=sid)

@app.route('/cadastro_page')
def cadastro_page():
    with open('templates/cadastro_page.html', 'r', encoding='utf-8') as file:
        html = file.read()
    return render_template_string(html)


@app.route('/login', methods=['GET', 'POST'])
def login():
    with open('templates/login_page.html', 'r', encoding='utf-8') as file:
        login_html = file.read()
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'mctech' and password == 'mctech':
            session['logged_in'] = True
            return redirect(url_for('config_page'))
        else:
            error = 'Usuário ou senha incorretos'
            return render_template_string(login_html, error=error)
    return render_template_string(login_html)


@app.route('/config_page')
def config_page():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    with open('templates/config_page.html', 'r', encoding='utf-8') as file:
        config_html = file.read()

    return render_template_string(config_html)


@app.route('/parametros_page')
def parametros_page():
    # Lê o IP e a porta do arquivo dados_recebidos.txt
    ip = 'localhost'
    porta = '8000'
    if os.path.exists('config.txt'):
        with open('config.txt', 'r') as f:
            lines = f.readlines()
            for line in lines:
                if 'ip =' in line:
                    ip = line.split('=')[1].strip()
                elif 'port =' in line:
                    porta = line.split('=')[1].strip()

    # Mapeamento dos nomes dos campos para nomes amigáveis
    nomes_amigaveis_parametros = {
        'mac': 'Endereço MAC',
        'velocidade_linha': 'Velocidade da Linha',
        'quantidade_placas': 'Quantidade de Placas',
        'faltam': 'Placas Faltantes',
        'quantidade_subplacas': 'Quantidade de Subplacas',
        'is_parada': 'Em Parada'
    }

    nomes_amigaveis_parada = {
        'mac': 'Endereço MAC',
        'is_parada': 'Em Parada',
        'duracao_parada': 'Duração da Parada (s)'
    }

    with open('templates/parametros_page.html', 'r', encoding='utf-8') as file:
        parametros_page_html = file.read()

    parametros_page_html = parametros_page_html.replace('{ip}', ip).replace('{porta}', porta)
    return render_template_string(parametros_page_html)

@app.route('/')
def home_page():
    return render_template('home_page.html')


if __name__ == '__main__':
    #wait_for_ethernet_ip()
    app.run(host='172.20.10.6', port=8001)
