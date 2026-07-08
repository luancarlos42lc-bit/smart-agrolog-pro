import datetime

# =====================================================================
# CONSTANTES GERAIS E INTERFACE DE CAMPO
# =====================================================================
# Códigos ANSI utilizados para colorir os alertas no terminal do tablet
COR_AMARELO = '\033[93m'
COR_VERMELHO = '\033[91m'
COR_VERDE = '\033[92m'
COR_RESET = '\033[0m'

# Dicionário de Ocorrências: Cadastre aqui todas as atividades operacionais permitidas
DICIONARIO_ATIVIDADES = {
    1: "Horário de Início de Turno",
    2: "Horário de Saída para Almoço",
    3: "Horário de Retorno do Almoço",
    4: "Horário de Fim de Atividade (Troca de Turno)",
    5: "Emergência (Saída do Trabalho)",
    6: "Acidente de Trabalho",
    7: "Saiu Mais Cedo",
    8: "Atendimento Médico",
    9: "Pátio",
    10: "Folga",
    11: "Folga Trabalhada",
    12: "Feriado Trabalhado"
}

# Cadastre aqui os setores válidos da sua empresa/usina para validação de dados
SETORES_CADASTRADOS = [
    "[CADASTRE_O_SETOR_AQUI_1]",
    "[CADASTRE_O_SETOR_AQUI_2]",
    "[CADASTRE_O_SETOR_AQUI_3]"
]


# =====================================================================
# CLASSES DE ESTRUTURA DE DADOS
# =====================================================================
class Funcionario:
    """Classe que representa a entidade do colaborador na base de dados local."""

    def __init__(self, cracha, nome, funcao, setor_origem, status_escala="Normal"):
        # Tratamento de exceção: Converte crachás inválidos para 0, evitando quebra (Crash)
        try:
            self.cracha = int(cracha)
        except (ValueError, TypeError):
            self.cracha = 0

        # O .strip() remove espaços vazios invisíveis digitados acidentalmente
        self.nome = str(nome).strip()
        self.funcao = str(funcao).strip()
        self.setor_origem = str(setor_origem).strip()
        self.status_escala = str(status_escala).strip()

        # Define se o funcionário começa o dia inativo ou já possui folga programada
        self.status_inicial = "Inativo" if self.status_escala != "Folga" else "Folga"


class Supervisor:
    """Classe responsável pelo nível de acesso de chefia e assinatura de lote."""

    def __init__(self, cracha_super, nome):
        try:
            self.cracha_super = int(cracha_super)
        except (ValueError, TypeError):
            self.cracha_super = 0
        self.nome = str(nome).strip()
        self.equipe_do_dia = []


# =====================================================================
# MOTOR PRINCIPAL (LÓGICA DE NEGÓCIO E VALIDAÇÕES)
# =====================================================================
class RegistroAtividadeCOA:
    """Máquina de estados que processa, valida e armazena os horários antes de enviar ao SAP."""

    def __init__(self, encarregado, supervisor, fazenda, talhao, setor_responsavel):
        self.encarregado = str(encarregado).strip()
        self.supervisor = supervisor
        self.fazenda = str(fazenda).strip()
        self.talhao = str(talhao).strip()
        self.setor_responsavel = str(setor_responsavel).strip()  # Setor dono da frente de trabalho

        # Estruturas de memória volátil do lote atual
        self.registros_funcionarios = []
        self.trabalhadores_no_registro = {}
        self.ultimo_horario_por_cracha = {}  # Rastreia a cronologia para impedir horários retroativos

    def verificar_escala_tela(self, funcionario):
        """Dispara um alerta visual se o supervisor tentar alocar alguém que está de folga."""
        if not isinstance(funcionario, Funcionario):
            return False
        if funcionario.status_escala == "Folga":
            print(
                f"{COR_AMARELO}⚠️  ALERTA: O Colaborador [{funcionario.nome}] está em dia de FOLGA na escala!{COR_RESET}")
            return True
        return False

    def obter_status_atual_no_lote(self, id_cracha, status_inicial):
        """Calcula dinamicamente qual o status atual do funcionário lendo os eventos em sequência."""
        status = status_inicial
        for reg in self.registros_funcionarios:
            if reg["Crachá"] == id_cracha:
                cod = reg["Codigo_Atividade"]
                # 1=Início, 11=Folga Trab, 12=Feriado Trab, 3=Retorno Almoço, 8=Médico, 9=Pátio
                if cod in [1, 11, 12, 3, 8, 9]:
                    status = "Trabalhando"
                elif cod == 2:  # 2=Saída Almoço
                    status = "Almoço"
                elif cod in [4, 5, 6, 7]:  # Códigos de saída/término
                    status = "Inativo" if status_inicial != "Folga" else "Folga"
                elif cod == 10:  # 10=Dar Folga
                    status = "Folga"
        return status

    def adicionar_registro(self, funcionario, codigo_atividade, hora, data_evento=None, observacao=""):
        """Método central: Valida regras matemáticas e de negócio antes de aceitar um horário."""

        # BLINDAGEM 1: Evita que objetos errados (ex: strings, dicionários vazios) entrem no sistema
        if not isinstance(funcionario, Funcionario):
            print(f"{COR_VERMELHO}❌ ERRO INTERNO: Objeto funcionário inválido fornecido ao lote!{COR_RESET}")
            return False

        # BLINDAGEM 2: Verifica se a atividade existe no nosso dicionário
        if codigo_atividade not in DICIONARIO_ATIVIDADES:
            print(f"{COR_VERMELHO}❌ ERRO: Código [{codigo_atividade}] inválido para {funcionario.nome}!{COR_RESET}")
            return False

        # BLINDAGEM 3: Converte o horário para formato de tempo. Captura erros como '25:00' ou letras.
        try:
            hora_objeto = datetime.datetime.strptime(str(hora).strip(), "%H:%M").time()
        except ValueError:
            print(f"{COR_VERMELHO}❌ ERRO: Horário '{hora}' inválido para {funcionario.nome}. Use HH:MM.{COR_RESET}")
            return False

        id_cracha = funcionario.cracha

        # Transforma horas e minutos em um valor inteiro linear para checagem matemática
        minutos_atuais = hora_objeto.hour * 60 + hora_objeto.minute

        # Busca em qual estado o funcionário se encontra no momento neste lote
        status_dinamico = self.obter_status_atual_no_lote(id_cracha, funcionario.status_inicial)

        # BLINDAGEM 4 (Bug Noturno): Protege a cronologia, mas permite viradas de meia-noite
        if id_cracha in self.ultimo_horario_por_cracha:
            ultimo_tempo = self.ultimo_horario_por_cracha[id_cracha]

            # Se o horário inserido for numericamente menor, mas o funcionário está em atividade,
            # o sistema entende que passou da meia-noite e adiciona 24h (1440 min) ao relógio.
            if minutos_atuais < ultimo_tempo and status_dinamico in ["Trabalhando", "Almoço"]:
                minutos_atuais += 1440

            # Bloqueia se o supervisor digitar um horário do passado (retroativo) no mesmo turno
            if minutos_atuais < ultimo_tempo:
                print(
                    f"{COR_VERMELHO}❌ ERRO CRÍTICO: Horário {hora} é inferior ao último evento registrado para {funcionario.nome}!{COR_RESET}")
                return False

        # Grava o funcionário na memória da equipe deste lote
        if id_cracha not in self.trabalhadores_no_registro:
            self.trabalhadores_no_registro[id_cracha] = funcionario

        # =================================================================
        # MÁQUINA DE ESTADOS: Regras de negócio de RH e Apontamento Agrícola
        # =================================================================
        if codigo_atividade in [1, 11, 12]:
            if status_dinamico in ["Trabalhando", "Almoço"]:
                print(f"{COR_VERMELHO}❌ ERRO: {funcionario.nome} já possui uma jornada ativa!{COR_RESET}")
                return False

        elif codigo_atividade == 2:
            if status_dinamico != "Trabalhando":
                print(
                    f"{COR_VERMELHO}❌ ERRO: {funcionario.nome} não pode ir para o almoço sem estar trabalhando!{COR_RESET}")
                return False

        elif codigo_atividade == 3:
            if status_dinamico != "Almoço":
                print(
                    f"{COR_VERMELHO}❌ ERRO: {funcionario.nome} não está em horário de almoço para retornar!{COR_RESET}")
                return False

        elif codigo_atividade in [8, 9]:
            if status_dinamico not in ["Trabalhando", "Almoço"]:
                print(
                    f"{COR_VERMELHO}❌ ERRO: {funcionario.nome} precisa iniciar o turno antes de ir para Pátio/Médico!{COR_RESET}")
                return False

        elif codigo_atividade == 10:
            if status_dinamico != "Folga" and len(
                    [r for r in self.registros_funcionarios if r["Crachá"] == id_cracha]) > 0:
                print(
                    f"{COR_VERMELHO}❌ ERRO: Não é possível dar FOLGA para {funcionario.nome} pois já existem lançamentos ativos hoje!{COR_RESET}")
                return False

        elif codigo_atividade in [4, 5, 6, 7]:
            if status_dinamico not in ["Trabalhando", "Almoço"]:
                print(
                    f"{COR_VERMELHO}❌ ERRO: Não é possível encerrar o turno de {funcionario.nome} (Status atual: {status_dinamico}).{COR_RESET}")
                return False

        # Atualiza a referência temporal do colaborador
        self.ultimo_horario_por_cracha[id_cracha] = minutos_atuais

        # Tratamento de fallback para a data: Se falhar a data informada, pega a data do sistema
        try:
            data_final = str(data_evento).strip() if data_evento else datetime.date.today().strftime("%d/%m/%Y")
        except Exception:
            data_final = datetime.date.today().strftime("%d/%m/%Y")

        # Lógica de Empréstimo de RH: Compara o setor de origem com o setor da frente de trabalho atual
        if funcionario.setor_origem.upper() == self.setor_responsavel.upper():
            tipo_vinculo = "Interno"
        else:
            tipo_vinculo = f"EMPRÉSTIMO DE: {funcionario.setor_origem.upper()}"

        # Montagem do pacote de dados final que irá para a integração ERP/SAP
        dados = {
            "Data": data_final,
            "Encarregado": self.encarregado,
            "Supervisor_Nome": self.supervisor.nome,
            "Supervisor_Cracha": self.supervisor.cracha_super,
            "Fazenda": self.fazenda,
            "Talhão": self.talhao,
            "Crachá": id_cracha,
            "Funcionário": funcionario.nome,
            "Função": funcionario.funcao,
            "Vínculo": tipo_vinculo,
            "Codigo_Atividade": codigo_atividade,
            "Ocorrência/Atividade": DICIONARIO_ATIVIDADES[codigo_atividade],
            "Horário": hora,
            "Observação": str(observacao).strip(),
            "Assinatura Func": f"ASSINATURA_DIGITAL_CRACHA_{id_cracha}",
            "Assinatura Super": f"ASSINATURA_SUPERVISOR_CRACHA_{self.supervisor.cracha_super}"
        }
        self.registros_funcionarios.append(dados)
        return True

    def resetar_lote(self):
        """Limpa as memórias do objeto, permitindo que a mesma tela inicie um novo lote vazio com segurança."""
        self.registros_funcionarios.clear()
        self.trabalhadores_no_registro.clear()
        self.ultimo_horario_por_cracha.clear()

    def enviar_para_escritorio(self):
        """Auditoria matemática final e transmissão dos dados processados."""
        saldos_de_jornada = {}
        status_no_almoço = {}

        # Varredura para checar se algum colaborador iniciou turno mas não fechou,
        # ou se saiu para almoço e esqueceu de dar o retorno.
        for reg in self.registros_funcionarios:
            cracha = reg["Crachá"]
            cod = reg["Codigo_Atividade"]

            if cracha not in saldos_de_jornada:
                saldos_de_jornada[cracha] = 0
                status_no_almoço[cracha] = False

            if cod in [1, 11, 12]:
                saldos_de_jornada[cracha] += 1
            elif cod == 2:
                status_no_almoço[cracha] = True
            elif cod == 3:
                status_no_almoço[cracha] = False
            elif cod in [4, 5, 6, 7]:
                saldos_de_jornada[cracha] -= 1
                if status_no_almoço[cracha]:
                    saldos_de_jornada[cracha] = -999  # Força quebra (-999) para erro de fechamento no almoço

        # Impede a transmissão caso a balança matemática do lote não feche em ZERO para todos
        for cracha, saldo in saldos_de_jornada.items():
            funcionario_obj = self.trabalhadores_no_registro[cracha]
            if saldo != 0 or status_no_almoço[cracha] or saldo == -999:
                print(f"\n{COR_VERMELHO}🛑 BLOQUEIO DE TRANSMISSÃO: Inconsistência matemática no Lote!{COR_RESET}")
                situacao = "esquecido no almoço" if saldo == -999 else (
                    "com turno aberto" if saldo > 0 else "com erro duplo")
                print(
                    f"{COR_VERMELHO}👉 Colaborador [{funcionario_obj.nome}] está {situacao}. Corrija os apontamentos.{COR_RESET}")
                return False

        # Verifica se tentou enviar um lote vazio
        if not self.registros_funcionarios:
            print(f"\n{COR_AMARELO}⚠️  AVISO: Lote vazio. Nenhum registro para processar.{COR_RESET}")
            return False

        # =================================================================
        # SIMULAÇÃO DE EXPORTAÇÃO PARA O SISTEMA CENTRAL (LOG DE CONSOLE)
        # =================================================================
        print(f"\n📡 Conexão Estabelecida! Sincronizando lote com o banco central...")
        print("=" * 140)
        print(f"📊 RELATÓRIO CONSOLIDADO | SETOR: {self.setor_responsavel} | ENCARREGADO: {self.encarregado}")
        print(f"📋 SUPERVISOR RESPONSÁVEL: {self.supervisor.nome} (Crachá: {self.supervisor.cracha_super})")
        print("=" * 140)

        for reg in self.registros_funcionarios:
            cod = reg["Codigo_Atividade"]
            txt_atividade = reg["Ocorrência/Atividade"]

            # Formatação de cores de acordo com a gravidade da atividade
            if cod in [5, 6]:
                txt_atividade = f"{COR_VERMELHO}🚨 {txt_atividade.upper()}{COR_RESET}"
            elif cod in [10, 11, 12]:
                txt_atividade = f"{COR_AMARELO}💤 {txt_atividade.upper()}{COR_RESET}"

            print(f"Data: {reg['Data']} | Crachá: {reg['Crachá']} | Nome: {reg['Funcionário']} [{reg['Função']}]")
            print(
                f"   ↳ Loc: {reg['Fazenda']} - Talhão {reg['Talhão']} | Hora: {reg['Horário']} | Vínculo: {reg['Vínculo']}")
            print(f"   ↳ Atividade: {txt_atividade}")
            if reg['Observação']:
                print(f"   ↳ OBSERVAÇÃO: {reg['Observação']}")
            print("-" * 140)

        print(f"{COR_VERDE}✅ [SISTEMA HOMOLOGADO] Lote integrado com sucesso!{COR_RESET}")

        # Limpa o lote automaticamente após sucesso para o próximo uso
        self.resetar_lote()
        return True


# =====================================================================
# ÁREA DE EXECUÇÃO (SIMULAÇÃO E INTEGRAÇÃO EXTERNA)
# =====================================================================
if __name__ == "__main__":
    # 1. Cadastro Fictício do Banco de Dados (Substituir pela query real do seu banco)
    banco_de_dados = {
        1001: Funcionario(cracha=1001, nome="[CADASTRE_O_NOME_1]", funcao="[CADASTRE_A_FUNCAO_1]",
                          setor_origem="[CADASTRE_O_SETOR_AQUI_1]"),

        # Exemplo de funcionário emprestado de outro setor (Teste de Lógica de Empréstimo)
        1002: Funcionario(cracha=1002, nome="[CADASTRE_O_NOME_2]", funcao="[CADASTRE_A_FUNCAO_2]",
                          setor_origem="[CADASTRE_O_SETOR_AQUI_2]", status_escala="Folga")
    }

    # 2. Inicialização dos Operadores do Tablet
    supervisor_turno = Supervisor(cracha_super=99999, nome="[NOME_DO_SUPERVISOR_AQUI]")

    registro_tablet = RegistroAtividadeCOA(
        encarregado="[NOME_DO_ENCARREGADO_AQUI]",
        supervisor=supervisor_turno,
        fazenda="[NOME_DA_FAZENDA_OU_LOCAL_AQUI]",
        talhao="[NUMERO_OU_NOME_DO_TALHAO_AQUI]",
        setor_responsavel="[CADASTRE_O_SETOR_AQUI_1]"  # Define quem é o dono desta frente de trabalho
    )

    print("\n--- INICIANDO ROTINA DE APONTAMENTOS ---")

    # Validações operacionais e apontamentos simulados:
    registro_tablet.verificar_escala_tela(banco_de_dados[1002])

    # Ciclo de vida padrão de um funcionário do setor principal
    registro_tablet.adicionar_registro(banco_de_dados[1001], codigo_atividade=1, hora="07:00")
    registro_tablet.adicionar_registro(banco_de_dados[1001], codigo_atividade=2, hora="11:30")
    registro_tablet.adicionar_registro(banco_de_dados[1001], codigo_atividade=3, hora="12:30")
    registro_tablet.adicionar_registro(banco_de_dados[1001], codigo_atividade=4, hora="16:00")

    # Fechamento e Envio do Lote processado
    registro_tablet.enviar_para_escritorio()