import numpy as np
import matplotlib.pyplot as plt

# Tempos de produção (em segundos)
tempos_producao = np.array([61, 60, 59, 62, 58, 60, 61, 59, 63, 60, 
                            61, 62, 60, 58, 61, 59, 60, 62, 61, 60, 
                            59, 60, 61, 63, 59, 58, 60, 61, 60, 59])

# Calcula a média dos tempos individuais
media_tempos = np.mean(tempos_producao)

# Calcula a amplitude móvel
amplitude_movel = np.abs(np.diff(tempos_producao))

# Calcula a média das amplitudes móveis
media_amplitude_movel = np.mean(amplitude_movel)

# Constantes para n = 30
E2 = 0.5477
D3 = 0.6067
D4 = 1.3933

# Calcula os limites de controle para a carta X (Valores Individuais)
LCS_X = media_tempos + E2 * media_amplitude_movel
LCI_X = media_tempos - E2 * media_amplitude_movel

# Calcula os limites de controle para a carta AM (Amplitude Móvel)
LCS_AM = D4 * media_amplitude_movel
LCI_AM = D3 * media_amplitude_movel

# Plotagem da Carta X (Valores Individuais)
plt.figure(figsize=(10, 6))
plt.plot(tempos_producao, marker='o', linestyle='-', color='b', label='Tempos de Produção')
plt.axhline(media_tempos, color='green', linestyle='--', label='LC')
plt.axhline(LCS_X, color='red', linestyle='--', label='LCS')
plt.axhline(LCI_X, color='red', linestyle='--', label='LCI')
plt.title('Carta de Controle para Valores Individuais (X)')
plt.xlabel('Amostra')
plt.ylabel('Tempo de Produção (s)')
plt.legend()
plt.show()

# Plotagem da Carta AM (Amplitude Móvel)
plt.figure(figsize=(10, 6))
plt.plot(amplitude_movel, marker='o', linestyle='-', color='b', label='Amplitude Móvel')
plt.axhline(media_amplitude_movel, color='green', linestyle='--', label='LC')
plt.axhline(LCS_AM, color='red', linestyle='--', label='LCS')
plt.axhline(LCI_AM, color='red', linestyle='--', label='LCI')
plt.title('Carta de Controle para Amplitude Móvel (AM)')
plt.xlabel('Amostra')
plt.ylabel('Amplitude Móvel (s)')
plt.legend()
plt.show()
