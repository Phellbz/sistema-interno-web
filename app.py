import streamlit as st
from omie_api import *
from PIL import Image
import os
import uuid

# Configuração da página
st.set_page_config(
    page_title="Sistema Interno - Portal Integrado",
    page_icon="📊",
    layout="wide"
)

# CSS customizado
st.markdown("""
<style>
    .main {background-color: #F3F6FA;}
    h1 {color: #004E8C;}
    .stButton>button {
        background-color: #007ACC;
        color: white;
        border-radius: 5px;
        padding: 0.5rem 1rem;
        font-weight: bold;
    }
    .stButton>button:hover {background-color: #005E9E;}
</style>
""", unsafe_allow_html=True)

# Logo e título
col1, col2 = st.columns([1, 4])
with col1:
    if os.path.exists("logo_empresa.png"):
        st.image("logo_empresa.png", width=110)
with col2:
    st.title("Sistema Interno - Portal Integrado")
    st.caption("Gerenciamento centralizado: Ordens de Serviço, Estoque e Notas Fiscais")

# Menu principal
menu = st.sidebar.selectbox(
    "📋 Menu Principal",
    ["📑 Cadastrar OS", "📦 Posição de Estoque", "🧾 Receber Nota Fiscal"]
)

# ===== TELA 1: CADASTRAR OS =====
if menu == "📑 Cadastrar OS":
    st.header("📑 Cadastro de Ordem de Serviço")

    # Busca de cliente
    with st.expander("🔍 Buscar Cliente", expanded=True):
        busca = st.text_input("Digite nome ou razão social:")
        if st.button("Buscar Cliente"):
            if busca:
                with st.spinner("Buscando clientes..."):
                    clientes = listar_clientes_resumido(busca)
                    if clientes:
                        st.session_state['clientes'] = clientes
                        st.success(f"{len(clientes)} clientes encontrados")
                    else:
                        st.warning("Nenhum cliente encontrado")

    # Seleção de cliente
    if 'clientes' in st.session_state and st.session_state['clientes']:
        cliente_selecionado = st.selectbox(
            "Selecione o cliente:",
            st.session_state['clientes'],
            format_func=lambda x: f"{x.get('nome_fantasia', 'N/A')} - {x.get('razao_social', 'N/A')}"
        )

        if st.button("✅ Confirmar Cliente"):
            st.session_state['cliente_selecionado'] = cliente_selecionado
            st.rerun()

    # Formulário de OS
    if 'cliente_selecionado' in st.session_state:
        st.success(f"✅ Cliente: {st.session_state['cliente_selecionado']['nome_fantasia']}")

        with st.form("dados_os"):
            st.subheader("📋 Dados Gerais da OS")

            col1, col2 = st.columns(2)
            with col1:
                data_prev = st.date_input("Data Previsão Faturamento")
                parcelas = st.number_input("Quantidade de Parcelas", min_value=1, value=1)
                departamento = st.selectbox("Departamento", 
                    ["OBRAS E PROJETOS", "MANUTENÇÃO FIXA", "LOJA"])
            with col2:
                categoria = st.selectbox("Categoria", 
                    ["Obra - Serviços Prestados", "Serviços Spot", "Contrato Fixo"])
                reter_iss = st.radio("Reter ISS?", ["Não", "Sim"])
                gerar_financeiro = st.radio("Gerar Conta a Pagar?", ["Não", "Sim"])

            st.subheader("🛠 Serviços")
            num_servicos = st.number_input("Número de Serviços", min_value=1, value=1, step=1)

            servicos = []
            valor_total = 0.0

            for i in range(int(num_servicos)):
                with st.expander(f"Serviço {i+1}", expanded=True):
                    desc = st.text_area(f"Descrição", key=f"desc_{i}", height=80)
                    col1, col2 = st.columns(2)
                    with col1:
                        qtd = st.number_input(f"Quantidade", min_value=0.01, value=1.0, key=f"qtd_{i}")
                    with col2:
                        valor = st.number_input(f"Valor Unitário (R$)", min_value=0.0, value=0.0, key=f"val_{i}")

                    subtotal = qtd * valor
                    st.info(f"💰 Subtotal: R$ {subtotal:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

                    if desc:
                        servicos.append({
                            "cDescServ": desc,
                            "nQtde": qtd,
                            "nValUnit": valor
                        })
                        valor_total += subtotal

            st.markdown(f"### 💵 Valor Total da OS: R$ {valor_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

            submitted = st.form_submit_button("🚀 Enviar OS para Omie", use_container_width=True)

            if submitted:
                if not servicos:
                    st.error("Adicione pelo menos um serviço!")
                else:
                    # Mapear departamento
                    dept_map = {
                        "OBRAS E PROJETOS": DEPARTAMENTOS["1"],
                        "MANUTENÇÃO FIXA": DEPARTAMENTOS["2"],
                        "LOJA": DEPARTAMENTOS["3"]
                    }
                    dept = dept_map[departamento]

                    # Mapear categoria
                    cat_map = {
                        "Obra - Serviços Prestados": CATEGORIAS["1"],
                        "Serviços Spot": CATEGORIAS["2"],
                        "Contrato Fixo": CATEGORIAS["3"]
                    }
                    cat = cat_map[categoria]

                    # Montar payload
                    os_payload = {
                        "Cabecalho": {
                            "cCodIntOS": str(uuid.uuid4()),
                            "cEtapa": "10",
                            "dDtPrevisao": data_prev.strftime("%d/%m/%Y"),
                            "nCodCli": st.session_state['cliente_selecionado']['codigo_cliente'],
                            "nQtdeParc": parcelas,
                            "nValorTotal": valor_total
                        },
                        "Departamentos": [{
                            "cCodDepto": dept["codigo"],
                            "nPerc": 100,
                            "nValor": valor_total,
                            "nValorFixo": "N"
                        }],
                        "Email": {
                            "cEnvBoleto": "N",
                            "cEnvLink": "N"
                        },
                        "InformacoesAdicionais": {
                            "cCodCateg": cat["codigo"],
                            "nCodCC": 3465583045,
                            "cDadosAdicNF": "OS incluída via API Web",
                            "cNaoGerarFinanceiro": "N" if gerar_financeiro == "Sim" else "S"
                        },
                        "ServicosPrestados": []
                    }

                    for service in servicos:
                        os_payload["ServicosPrestados"].append({
                            "cCodServLC116": "14.01",
                            "cCodServMun": "432230202",
                            "cDadosAdicItem": "Serviços prestados",
                            "cDescServ": service['cDescServ'],
                            "cRetemISS": "S" if reter_iss == "Sim" else "N",
                            "cTribServ": "01",
                            "impostos": {
                                "cRetemIRRF": "S",
                                "cRetemPIS": "N",
                                "nAliqCOFINS": 0,
                                "nAliqCSLL": 0,
                                "nAliqIRRF": 15,
                                "nAliqISS": 5,
                                "nAliqPIS": 0
                            },
                            "nQtde": service['nQtde'],
                            "nValUnit": service['nValUnit']
                        })

                    with st.spinner("Enviando OS para Omie..."):
                        resp = incluir_os(os_payload)

                        if resp and "error" not in resp and "faultstring" not in resp:
                            os_number = resp.get('nCodOS', 'N/A')
                            st.success(f"✅ OS incluída com sucesso! Número da OS: {os_number}")
                            # Limpar sessão
                            if 'cliente_selecionado' in st.session_state:
                                del st.session_state['cliente_selecionado']
                            if 'clientes' in st.session_state:
                                del st.session_state['clientes']
                        else:
                            erro = resp.get("faultstring", resp.get("error", "Erro desconhecido"))
                            st.error(f"❌ Erro ao enviar OS: {erro}")

# ===== TELA 2: RECEBER NOTA FISCAL =====
elif menu == "🧾 Receber Nota Fiscal":
    st.header("🧾 Recebimento de Notas Fiscais")
    st.info("⚙️ Funcionalidade em desenvolvimento")

# ===== TELA 3: POSIÇÃO DE ESTOQUE =====
elif menu == "📦 Posição de Estoque":
    st.header("📦 Posição de Estoque")
    st.info("⚙️ Funcionalidade em desenvolvimento")

# Rodapé
st.markdown("---")
st.caption("© 2025 - Sistema Interno Integrado da Empresa | by Peterson B'")
