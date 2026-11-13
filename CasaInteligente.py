from abc import ABC, abstractmethod
import pickle
from typing import Dict, List, Tuple, Type


class ComandoVoz(ABC):
    @abstractmethod
    def executar_comando(self, comando: str, id_disp: int, casa: 'CasaInteligente') -> str:
        pass


class ConexaoWiFi:
    def __init__(self, ssid: str, senha: str):
        self.__ssid = ssid
        self.__senha = senha
        self.__conectado = False

    def get_ssid(self) -> str:
        return self.__ssid

    def is_conectado_wifi(self) -> bool:
        return self.__conectado

    def conectar(self, senha_digitada: str = "12345678") -> str:
        if self.__conectado:
            return f"Já está conectado à rede '{self.__ssid}'."
        if senha_digitada == self.__senha:
            self.__conectado = True
            return f"Conectado com sucesso à rede Wi-Fi '{self.__ssid}'!"
        raise Exception("Erro Wi-Fi: Senha incorreta!")

    def desconectar(self) -> str:
        if self.__conectado:
            self.__conectado = False
            return f"Desconectado da rede '{self.__ssid}'."
        return "O dispositivo já está desconectado do Wi-Fi."


class Dispositivo(ABC):
    def __init__(self, nome: str):
        self.__nome = nome
        self.__ligado = False

    def get_nome(self) -> str:
        return self.__nome

    def is_ligado(self) -> bool:
        return self.__ligado

    def ligar(self):
        if not self.__ligado:
            self.__ligado = True
        else:
            raise Exception(f"Erro: {self.__nome} já está ligado!")

    def desligar(self):
        if self.__ligado:
            self.__ligado = False
        else:
            raise Exception(f"Erro: {self.__nome} já está desligado!")

    def __str__(self):
        status = "Ligado" if self.__ligado else "Desligado"
        return f"Nome: {self.__nome}\nStatus: {status}\n"

    def __repr__(self):
        return f"{self.__class__.__name__}(nome='{self.__nome}', ligado={self.__ligado})"

    @abstractmethod
    def testar_status(self) -> str:
        pass


class AssistenteVirtual(Dispositivo, ComandoVoz):
    def __init__(self, nome: str = "Alexa"):
        super().__init__(nome)

    def executar_comando(self, comando: str, id_disp: int, casa: 'CasaInteligente') -> str:
        if not self.is_ligado():
            raise Exception(f"O assistente {self.get_nome()} está desligado e não pode ouvir comandos.")
        if not isinstance(comando, str):
            raise TypeError("O comando deve ser um texto.")

        comando = comando.lower()
        try:
            if "ligar" in comando:
                casa.ligar_dispositivo(id_disp)
                return f"{self.get_nome()}: Ok, liguei o dispositivo {id_disp}."
            elif "desligar" in comando:
                casa.desligar_dispositivo(id_disp)
                return f"{self.get_nome()}: Ok, desliguei o dispositivo {id_disp}."
            return f"{self.get_nome()}: Desculpe, não entendi o comando."
        except Exception as e:
            return f"{self.get_nome()}: Não consegui executar. {str(e)}"

    def testar_status(self) -> str:
        return f"O assistente {self.get_nome()} está {'aguardando comandos' if self.is_ligado() else 'mudo'}."


class LampadaInteligente(Dispositivo, ConexaoWiFi):
    def __init__(self, nome: str, cor_inicial: str = "Branca", ssid: str = "Casa", senha: str = "12345678"):
        super().__init__(nome)
        self.__cor = cor_inicial
        ConexaoWiFi.__init__(self, ssid, senha)

    def mudar_cor(self, nova_cor: str):
        if self.is_ligado():
            self.__cor = nova_cor
        else:
            raise Exception("Erro: Não é possível mudar a cor. A lâmpada está desligada!")

    def testar_status(self) -> str:
        return f"A Lâmpada {self.get_nome()} está emitindo luz {self.__cor}."

    def __str__(self):
        return super().__str__() + f"Cor: {self.__cor}\n"


class ArCondicionado(Dispositivo, ConexaoWiFi):
    def __init__(self, nome: str, temperatura_inicial: int = 24, ssid: str = "Casa", senha: str = "12345678"):
        super().__init__(nome)
        self.__temperatura = temperatura_inicial
        self.__temporizador_min = 0
        ConexaoWiFi.__init__(self, ssid, senha)

    def ajustar_temperatura(self, temp: int):
        if not self.is_ligado():
            raise Exception("Erro: Não é possível ajustar. O Ar Condicionado está desligado!")
        if not isinstance(temp, int) or isinstance(temp, bool) or not (16 <= temp <= 30):
            raise Exception("Erro: Temperatura inválida! Escolha entre 16°C e 30°C.")
        self.__temperatura = temp

    def definir_temporizador(self, minutos: int) -> str:
        if not self.is_ligado():
            raise Exception("Erro: Não é possível programar o temporizador com o aparelho desligado!")
        if minutos <= 0:
            raise Exception("Erro: O tempo do temporizador deve ser maior que 0 minutos.")
        self.__temporizador_min = minutos
        return f"Temporizador definido para {minutos} minutos."

    def cancelar_temporizador(self) -> str:
        if self.__temporizador_min > 0:
            self.__temporizador_min = 0
            return "Temporizador cancelado."
        return "Nenhum temporizador ativo para cancelar."

    def testar_status(self) -> str:
        return f"O Ar Condicionado {self.get_nome()} está refrigerando a {self.__temperatura}°C."

    def __str__(self):
        return super().__str__() + f"Temperatura: {self.__temperatura}°C\n"


class SensorPresenca(Dispositivo, ConexaoWiFi):
    def __init__(self, nome: str, ssid: str = "Casa", senha: str = "12345678"):
        super().__init__(nome)
        self.__presenca_detectada = False
        ConexaoWiFi.__init__(self, ssid, senha)

    def simular_deteccao(self, presenca: bool) -> str:
        if not self.is_ligado():
            raise Exception("Erro: O sensor de presença está desligado!")
        if not isinstance(presenca, bool):
            raise ValueError("A presença deve ser informada como True ou False.")
        self.__presenca_detectada = presenca
        return f"{'Presença detectada' if presenca else 'Nenhuma presença detectada'} pelo sensor '{self.get_nome()}'."

    def tem_presenca(self) -> bool:
        return self.__presenca_detectada

    def testar_status(self) -> str:
        if not self.is_ligado():
            return f"O sensor de presença {self.get_nome()} está desligado."
        return f"O sensor {self.get_nome()} {'detectou' if self.__presenca_detectada else 'não detectou'} presença."


class SensorTemperatura(Dispositivo):
    def __init__(self, nome: str, temperatura_inicial: float = 22.0):
        super().__init__(nome)
        self.__temperatura = float(temperatura_inicial)

    def atualizar_temperatura(self, nova_temperatura: float):
        if not self.is_ligado():
            raise Exception("Erro: O sensor de temperatura está desligado!")
        if not isinstance(nova_temperatura, (int, float)) or isinstance(nova_temperatura, bool):
            raise ValueError("A temperatura precisa ser um número.")
        self.__temperatura = float(nova_temperatura)

    def get_temperatura(self) -> float:
        return self.__temperatura

    def testar_status(self) -> str:
        if not self.is_ligado():
            return f"O sensor de temperatura {self.get_nome()} está desligado."
        return f"O sensor {self.get_nome()} está registrando {self.__temperatura:.1f}°C."


class CasaInteligente:
    def __init__(self, nome_arquivo: str = 'dispositivos_casa.pkl'):
        self.__dispositivos: Dict[int, Dispositivo] = {}
        self.__nome_arquivo = nome_arquivo
        self.carregar_estado()

    def adicionar_dispositivo(self, id_disp: int, dispositivo: Dispositivo):
        if not isinstance(id_disp, int) or isinstance(id_disp, bool) or id_disp <= 0:
            raise ValueError("O ID deve ser um número inteiro positivo.")
        if not isinstance(dispositivo, Dispositivo):
            raise TypeError("O objeto informado não é um dispositivo válido.")
        if id_disp in self.__dispositivos:
            raise ValueError(f"Já existe um dispositivo cadastrado com o ID {id_disp}.")

        self.__dispositivos[id_disp] = dispositivo
        self.salvar_estado()

    def remover_dispositivo(self, id_disp: int):
        if id_disp not in self.__dispositivos:
            raise Exception("Erro: Dispositivo não encontrado no sistema!")
        dispositivo_removido = self.__dispositivos.pop(id_disp)
        self.salvar_estado()
        return dispositivo_removido

    def get_dispositivo(self, id_disp: int):
        if id_disp in self.__dispositivos:
