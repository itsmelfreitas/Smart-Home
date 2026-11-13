from CasaInteligente import (
    CasaInteligente, AssistenteVirtual, LampadaInteligente,
    ArCondicionado, SensorPresenca, SensorTemperatura
)

def exibir_menu():
    print("\n" + "=" * 40)
    print("🏠 CASA INTELIGENTE - MENU INTERATIVO")
    print("=" * 40)
    print("1. Adicionar dispositivo")
    print("2. Listar dispositivos")
    print("3. Ligar dispositivo")
    print("4. Desligar dispositivo")
    print("5. Ajustar temperatura (Ar Condicionado)")
    print("6. Mudar cor (Lâmpada Inteligente)")
    print("7. Simular presença (Sensor de Presença)")
    print("8. Atualizar temperatura (Sensor de Temperatura)")
    print("9. Usar Assistente Virtual (Comando de Voz)")
    print("10. Exibir detalhes de um dispositivo")
    print("0. Sair")
    print("=" * 40)

def selecionar_dispositivo(casa, tipo=None):
    dispositivos = casa.listar_dispositivos()
    if tipo is not None:
        dispositivos = [(id_disp, disp) for id_disp, disp in dispositivos if isinstance(disp, tipo)]

    if not dispositivos:
        print("\nNenhum dispositivo compatível encontrado.")
        return None

    print("\n📋 Selecione um dispositivo:")
    print("-" * 40)
    for indice, (id_disp, disp) in enumerate(dispositivos, start=1):
        estado = "Ligado" if disp.is_ligado() else "Desligado"
        print(f"{indice}. {disp.get_nome().title()} | {estado}")
    print("0. Voltar")

    try:
        escolha = int(input("\nEscolha o dispositivo: "))
        if escolha == 0 or escolha < 1 or escolha > len(dispositivos):
            if escolha != 0: print("Opção inválida!")
            return None
        return dispositivos[escolha - 1][0]
    except ValueError:
        print("Digite uma opção numérica válida!")
        return None


def main():
    casa = CasaInteligente()

    while True:
        exibir_menu()
        opcao = input("Selecione uma opção: ").strip()

        try:
            if opcao == "1":
                id_disp = max(casa.listar_ids_dispositivos(), default=0) + 1
                tipo = input("Digite o tipo (lampada, ar, presenca, temperatura, assistente): ").strip().lower()
                nome = input("Digite o nome do dispositivo: ")

                if tipo == "lampada":
                    disp = LampadaInteligente(nome, input("Digite a cor inicial: "))
                elif tipo == "ar":
                    disp = ArCondicionado(nome, int(input("Digite a temperatura inicial: ")))
                elif tipo == "presenca":
                    disp = SensorPresenca(nome)
                elif tipo == "temperatura":
                    disp = SensorTemperatura(nome, float(input("Digite a temperatura inicial: ")))
                elif tipo == "assistente":
                    disp = AssistenteVirtual(nome)
                else:
                    print("Tipo inválido!")
                    continue

                casa.adicionar_dispositivo(id_disp, disp)
                print(f"\nDispositivo '{nome}' adicionado com sucesso! (ID interno: {id_disp})")

            elif opcao == "2":
                print("\n📋 Dispositivos cadastrados:\n" + casa.exibir_todos())

            elif opcao == "3":
                if (id_disp := selecionar_dispositivo(casa)):
                    casa.ligar_dispositivo(id_disp)
                    print(f"\n{casa.get_dispositivo(id_disp).get_nome()} ligado com sucesso!")

            elif opcao == "4":
                if (id_disp := selecionar_dispositivo(casa)):
                    casa.desligar_dispositivo(id_disp)
                    print(f"\n{casa.get_dispositivo(id_disp).get_nome()} desligado com sucesso!")

            elif opcao == "5":
                if (id_disp := selecionar_dispositivo(casa, ArCondicionado)):
                    casa.get_dispositivo(id_disp).ajustar_temperatura(int(input("Nova temperatura (16-30°C): ")))
                    casa.salvar_estado()
                    print("Temperatura ajustada.")

            elif opcao == "6":
                if (id_disp := selecionar_dispositivo(casa, LampadaInteligente)):
                    casa.get_dispositivo(id_disp).mudar_cor(input("Nova cor da lâmpada: "))
                    casa.salvar_estado()
                    print("Cor alterada.")

            elif opcao == "7":
                if (id_disp := selecionar_dispositivo(casa, SensorPresenca)):
                    resposta = input("Presença detectada? (s/n): ").strip().lower()
                    if resposta in ("s", "n"):
                        print(casa.simular_presenca(id_disp, resposta == "s"))

            elif opcao == "8":
                if (id_disp := selecionar_dispositivo(casa, SensorTemperatura)):
                    casa.atualizar_sensor_temperatura(id_disp, float(input("Nova temperatura: ")))
                    print("Temperatura atualizada.")

            elif opcao == "9":
                if (id_asst := selecionar_dispositivo(casa, AssistenteVirtual)):
                    comando = input("Digite o comando (ex: 'ligar', 'desligar'): ")
                    print("\nQual dispositivo deseja controlar?")
                    if (id_alvo := selecionar_dispositivo(casa)):
                        print(casa.get_dispositivo(id_asst).executar_comando(comando, id_alvo, casa))

            elif opcao == "10":
                if (id_disp := selecionar_dispositivo(casa)):
                    disp = casa.get_dispositivo(id_disp)
                    print(f"\nDetalhes do dispositivo:\n{disp}{disp.testar_status()}")

            elif opcao == "0":
                print("Encerrando o sistema. Até logo!")
                break
            else:
                print("Opção inválida! Tente novamente.")

        except Exception as e:
            print(f"Erro na operação: {e}")

if __name__ == "__main__":
    main()
