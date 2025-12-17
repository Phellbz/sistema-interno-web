python import streamlit as st from omie_api import * import uuid from datetime import datetime import pandas as pd import json

Configuração da página
st.set_page_config( page_title="Sistema Interno - Portal Integrado", page_icon="📊", layout="wide" )

CSS customizado
st.markdown("""

""", unsafe_allow_html=True)

Inicializar session_state
if 'omie_api' not in st.session_state: st.session_state['omie_api'] = OmieEstoqueAPI( st.secrets["OMIE_APP_KEY"], st.secrets["OMIE_APP_SECRET"], OMIE_ESTOQUE_BASE_URL )

Logo e título
col1, col2 = st.columns([1, 4]) with col1: try: st.image("logo_empresa.png", width=110) except: st.write("🏢") with col2: st.title("Sistema Interno - Portal Integrado") st.caption("Gerenciamento centralizado: Ordens de Serviço, Estoque e Notas Fiscais")

Menu principal
menu = st.sidebar.selectbox( "📋 Menu Principal", ["🏠 Início", "📑 Cadastrar OS", "🧾 Receber Nota Fiscal", "📦 Posição de Estoque"] )

===== TELA INICIAL =====
if menu == "🏠 Início": st.header("Bem-vindo ao Sistema Interno")

col1, col2, col3 = st.columns(3)

with col1:
    st.info("### 📑 Cadastrar OS\nCrie ordens de serviço vinculadas a clientes")

with col2:
    st.info("### 🧾 Receber NF\nProcesse notas fiscais de entrada")

with col3:
    st.info("### 📦 Estoque\nConsulte posição de estoque")

st.markdown("---")
st.caption("Selecione uma opção no menu lateral para começar")
===== TELA 1: CADASTRAR OS =====
elif menu == "📑 Cadastrar OS": st.header("📑 Cadastro de Ordem de Serviço")

# ETAPA 1: Busca de cliente
if 'cliente_selecionado' not in st.session_state:
    with st.expander("🔍 Buscar Cliente", expanded=True):
        busca = st.text_input("Digite nome ou razão social do cliente:")

        col1, col2 = st.columns([1, 4])
        with col1:
            buscar_btn = st.button("🔍 Buscar Cliente", use_container_width=True)

        if buscar_btn and busca:
            with st.spinner("Buscando clientes na Omie..."):
                clientes = listar_clientes_resumido(busca)
                if clientes:
                    st.session_state['clientes_encontrados'] = clientes
                    st.success(f"✅ {len(clientes)} cliente(s) encontrado(s)")
                else:
                    st.warning("⚠️ Nenhum cliente encontrado com esse termo")

    # Mostrar resultados da busca
    if 'clientes_encontrados' in st.session_state:
        st.subheader("Selecione o Cliente")

        for idx, cliente in enumerate(st.session_state['clientes_encontrados']):
            col1, col2, col3 = st.columns([3, 3, 1])

            with col1:
                st.write(f"**{cliente.get('nome_fantasia', 'N/A')}**")
            with col2:
                st.write(f"{cliente.get('razao_social', 'N/A')}")
            with col3:
                if st.button("Selecionar", key=f"sel_cliente_{idx}"):
                    st.session_state['cliente_selecionado'] = cliente
                    st.rerun()

            st.divider()

# ETAPA 2: Formulário de OS
else:
    cliente = st.session_state['cliente_selecionado']

    # Mostrar cliente selecionado
    st.success(f"✅ **Cliente Selecionado:** {cliente['nome_fantasia']} - {cliente['razao_social']}")

    if st.button("⬅️ Voltar para busca de cliente"):
        del st.session_state['cliente_selecionado']
        if 'clientes_encontrados' in st.session_state:
            del st.session_state['clientes_encontrados']
        st.rerun()

    st.markdown("---")

    # Formulário de dados da OS
    with st.form("form_os"):
        st.subheader("📋 Dados Gerais da OS")

        col1, col2 = st.columns(2)

        with col1:
            data_prev = st.date_input(
                "Data de Previsão de Faturamento",
                value=datetime.now()
            )

            parcelas = st.number_input(
                "Quantidade de Parcelas",
                min_value=1,
                value=1,
                step=1
            )

            departamento_desc = st.selectbox(
                "Departamento",
                options=[d["descricao"] for d in DEPARTAMENTOS.values()]
            )

        with col2:
            categoria_desc = st.selectbox(
                "Categoria",
                options=[c["descricao"] for c in CATEGORIAS.values()]
            )

            reter_iss = st.radio(
                "Reter ISS?",
                options=["Não", "Sim"],
                horizontal=True
            )

            gerar_financeiro = st.radio(
                "Gerar Conta a Pagar?",
                options=["Não", "Sim"],
                horizontal=True
            )

        st.markdown("---")
        st.subheader("🛠 Serviços")

        num_servicos = st.number_input(
            "Número de Serviços a Adicionar",
            min_value=1,
            value=1,
            step=1
        )

        servicos_data = []
        valor_total_os = 0.0

        for i in range(int(num_servicos)):
            with st.expander(f"📝 Serviço {i+1}", expanded=True):
                desc_servico = st.text_area(
                    "Descrição do Serviço",
                    key=f"desc_{i}",
                    height=100,
                    placeholder="Descreva o serviço prestado..."
                )

                col_qtd, col_valor = st.columns(2)

                with col_qtd:
                    qtd_servico = st.number_input(
                        "Quantidade",
                        min_value=0.01,
                        value=1.0,
                        step=0.01,
                        key=f"qtd_{i}"
                    )

                with col_valor:
                    valor_unit = st.number_input(
                        "Valor Unitário (R$)",
                        min_value=0.0,
                        value=0.0,
                        step=0.01,
                        key=f"valor_{i}"
                    )

                valor_total_servico = qtd_servico * valor_unit
                st.info(f"💰 **Valor Total deste Serviço:** R$ {valor_total_servico:,.2f}")

                servicos_data.append({
                    'cDescServ': desc_servico,
                    'nQtde': qtd_servico,
                    'nValUnit': valor_unit
                })

                valor_total_os += valor_total_servico

        st.markdown("---")
        st.success(f"### 💰 Valor Total da OS: R$ {valor_total_os:,.2f}")

        # Botão de envio
        submitted = st.form_submit_button(
            "✅ Enviar OS para Omie",
            use_container_width=True,
            type="primary"
        )

        if submitted:
            # Validações
            if valor_total_os <= 0:
                st.error("❌ O valor total da OS deve ser maior que zero!")
            elif any(not s['cDescServ'].strip() for s in servicos_data):
                st.error("❌ Todos os serviços devem ter descrição!")
            else:
                # Mapear departamento
                dept_map = {v["descricao"]: v for k, v in DEPARTAMENTOS.items()}
                dept = dept_map[departamento_desc]

                # Mapear categoria
                cat_map = {v["descricao"]: v for k, v in CATEGORIAS.items()}
                cat = cat_map[categoria_desc]

                # Montar payload
                os_payload = {
                    "Cabecalho": {
                        "cCodIntOS": str(uuid.uuid4()),
                        "cEtapa": "10",
                        "dDtPrevisao": data_prev.strftime("%d/%m/%Y"),
                        "nCodCli": cliente['codigo_cliente'],
                        "nQtdeParc": int(parcelas),
                        "nValorTotal": valor_total_os
                    },
                    "Departamentos": [{
                        "cCodDepto": dept["codigo"],
                        "nPerc": 100,
                        "nValor": valor_total_os,
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

                # Adicionar serviços
                for service in servicos_data:
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

                # Enviar para Omie
                with st.spinner("📤 Enviando OS para Omie..."):
                    resp = incluir_os(os_payload)

                    if resp and "error" not in resp and "faultstring" not in resp:
                        os_number = resp.get('nCodOS', 'N/A')
                        st.success(f"✅ **OS incluída com sucesso!**\n\n**Número da OS:** {os_number}")

                        # Limpar sessão
                        if 'cliente_selecionado' in st.session_state:
                            del st.session_state['cliente_selecionado']
                        if 'clientes_encontrados' in st.session_state:
                            del st.session_state['clientes_encontrados']

                        st.balloons()
                    else:
                        erro = resp.get("faultstring", resp.get("error", "Erro desconhecido"))
                        st.error(f"❌ **Erro ao enviar OS:**\n\n{erro}")
===== TELA 2: RECEBER NOTA FISCAL =====
elif menu == "🧾 Receber Nota Fiscal": st.header("🧾 Recebimento de Notas Fiscais")

# Configuração de geração de financeiro
st.subheader("⚙️ Configurações")
gerar_financeiro_nf = st.radio(
    "Gerar Conta a Pagar?",
    options=["Sim", "Não"],
    horizontal=True,
    help="Define se será gerado título financeiro para esta nota"
)

st.markdown("---")

# Listar recebimentos pendentes
if st.button("🔄 Carregar Notas Pendentes", use_container_width=True):
    with st.spinner("Carregando notas fiscais pendentes..."):
        recebimentos_data = st.session_state['omie_api'].listar_recebimentos(1, 50, "40")

        if recebimentos_data and "recebimentos" in recebimentos_data:
            st.session_state['recebimentos_lista'] = recebimentos_data["recebimentos"]
            st.success(f"✅ {len(st.session_state['recebimentos_lista'])} nota(s) pendente(s) encontrada(s)")
        else:
            st.warning("⚠️ Nenhuma nota pendente encontrada")

# Mostrar lista de recebimentos
if 'recebimentos_lista' in st.session_state:
    st.subheader("📋 Notas Fiscais Pendentes")

    for idx, receb in enumerate(st.session_state['recebimentos_lista']):
        with st.expander(
            f"NF {receb.get('cNumNF', 'N/A')} - {receb.get('cNomeFor', 'Fornecedor')} - R$ {receb.get('vTotalNFe', 0):,.2f}",
            expanded=False
        ):
            col1, col2, col3 = st.columns(3)

            with col1:
                st.write(f"**ID Recebimento:** {receb.get('nIdReceb')}")
                st.write(f"**Número NF:** {receb.get('cNumNF')}")

            with col2:
                st.write(f"**Fornecedor:** {receb.get('cNomeFor')}")
                st.write(f"**CNPJ:** {receb.get('cCNPJCPFFor', 'N/A')}")

            with col3:
                st.write(f"**Valor Total:** R$ {receb.get('vTotalNFe', 0):,.2f}")
                st.write(f"**Data Emissão:** {receb.get('dEmissao', 'N/A')}")

            if st.button(f"📝 Processar esta NF", key=f"processar_{idx}"):
                st.session_state['recebimento_selecionado'] = receb
                st.session_state['gerar_financeiro_nf'] = gerar_financeiro_nf
                st.rerun()

# Processar recebimento selecionado
if 'recebimento_selecionado' in st.session_state:
    receb = st.session_state['recebimento_selecionado']
    nIdReceb = receb['nIdReceb']

    st.markdown("---")
    st.subheader(f"📝 Processando NF {receb.get('cNumNF', 'N/A')}")

    if st.button("⬅️ Voltar para lista"):
        del st.session_state['recebimento_selecionado']
        st.rerun()

    # Consultar detalhes
    with st.spinner("Carregando detalhes da nota..."):
        detalhes = st.session_state['omie_api'].consultar_recebimento(nIdReceb)

    if detalhes and 'itensRecebimento' in detalhes:
        st.session_state['receipt_details'] = detalhes

        # Mostrar itens
        st.subheader("📦 Itens da Nota Fiscal")

        itens = detalhes.get("itensRecebimento", [])

        for idx, item in enumerate(itens):
            cab = item.get("itensCabec", {})
            nSeq = cab.get("nSequencia")
            desc = cab.get("cDescricaoProduto", "Produto")
            qtd = cab.get("nQuantidade", 0)
            valor_unit = cab.get("vUnitario", 0)
            valor_total = qtd * valor_unit

            with st.container():
                col1, col2 = st.columns([4, 1])

                with col1:
                    st.write(f"**{nSeq}. {desc}**")
                    st.caption(f"Qtd: {qtd} | Valor Unit: R$ {valor_unit:,.2f} | Total: R$ {valor_total:,.2f}")

                with col2:
                    if st.button("✏️ Editar", key=f"edit_{idx}"):
                        st.session_state['item_editando'] = nSeq
                        st.rerun()

                st.divider()

            # Se este item está sendo editado
            if 'item_editando' in st.session_state and st.session_state['item_editando'] == nSeq:
                with st.form(f"form_edit_{nSeq}"):
                    st.subheader(f"Editar Item {nSeq}")

                    acao = st.selectbox(
                        "Ação",
                        options=["NOVO", "ASSOCIAR-PRODUTO", "IGNORAR", "EDITAR"],
                        help="NOVO: cadastrar como novo produto | ASSOCIAR: vincular a produto existente | IGNORAR: não importar | EDITAR: ajustar valores"
                    )

                    cod_produto_associar = None
                    perc_preco = None
                    icms_st_custo = None

                    if acao == "ASSOCIAR-PRODUTO":
                        # Busca de produto
                        busca_prod = st.text_input("Buscar produto por descrição:")

                        if busca_prod:
                            produtos_cache = carregar_lista_produtos_cache()
                            encontrados = pesquisar_produtos_por_nome(produtos_cache, busca_prod)

                            if encontrados:
                                prod_selecionado = st.selectbox(
                                    "Selecione o produto:",
                                    options=encontrados,
                                    format_func=lambda x: f"{x['codigo']} - {x['nome']}"
                                )
                                cod_produto_associar = prod_selecionado['codigo']

                    elif acao == "EDITAR":
                        perc_preco = st.number_input(
                            "Percentual de atualização do preço de venda (%)",
                            min_value=0.0,
                            value=100.0,
                            step=1.0,
                            help="Ex: 100 para 100% de markup"
                        )

                        icms_st_custo = st.number_input(
                            "Valor ICMS ST a incluir no custo (R$)",
                            min_value=0.0,
                            value=0.0,
                            step=0.01
                        )

                    col1, col2 = st.columns(2)

                    with col1:
                        confirmar_edit = st.form_submit_button("✅ Confirmar Alteração", use_container_width=True)
                    with col2:
                        cancelar_edit = st.form_submit_button("❌ Cancelar", use_container_width=True)

                    if confirmar_edit:
                        # Montar payload conforme ação
                        payload = {
                            "ide": {"nIdReceb": nIdReceb},
                            "itensRecebimentoEditar": {
                                "itensIde": {
                                    "nSequencia": nSeq,
                                    "cAcao": acao
                                }
                            }
                        }

                        if acao == "ASSOCIAR-PRODUTO" and cod_produto_associar:
                            payload["itensRecebimentoEditar"]["itensIde"]["nIdProdutoExistente"] = int(cod_produto_associar)

                        elif acao == "EDITAR":
                            info_adic = detalhes.get("infoAdicionais", {})
                            totais = detalhes.get("totais", {})

                            payload["infoAdicionais"] = {
                                "cCategCompra": "2.01.01",
                                "dRegistro": info_adic.get("dRegistro", datetime.now().strftime("%Y-%m-%d"))
                            }

                            if info_adic.get("nIdConta"):
                                payload["infoAdicionais"]["nIdConta"] = info_adic["nIdConta"]

                            payload["departamentos"] = [{
                                "cCodDepartamento": DEPARTAMENTOS["3"]["codigo"],
                                "vDepartamento": totais.get("vTotalNFe", 0),
                                "pDepartamento": 100.0
                            }]

                            if perc_preco is not None:
                                payload["itensRecebimentoEditar"]["itensAtualPreco"] = {
                                    "cAtualizarAtuPre": "S",
                                    "nPercAtuPre": perc_preco,
                                    "cAtualizarMaiorAtuPre": "N"
                                }

                            if icms_st_custo is not None and icms_st_custo > 0:
                                payload["itensRecebimentoEditar"]["itensCustoEstoque"] = {
                                    "cICMSCusto": "S",
                                    "cPISCusto": "S",
                                    "cICMSSTCusto": "S",
                                    "cCOFINSCusto": "S",
                                    "cIPICusto": "S",
                                    "cFreteCusto": "S",
                                    "cSeguroCusto": "S",
                                    "cOutrosDespCusto": "S",
                                    "nValorICMSSTCusto": icms_st_custo,
                                    "nAliqCredPISCusto": 1.65,
                                    "nAliqCredCOFINSCusto": 7.6
                                }

                            # Adicionar configuração de financeiro
                            cNaoGerarFinanceiro = "N" if st.session_state.get('gerar_financeiro_nf') == "Sim" else "S"
                            payload["itensRecebimentoEditar"]["itensAjustes"] = {
                                "cNaoGerarFinanceiro": cNaoGerarFinanceiro
                            }

                        # Enviar alteração
                        with st.spinner("Enviando alteração..."):
                            resp = st.session_state['omie_api'].alterar_recebimento(payload)

                            if resp and "error" not in resp:
                                st.success("✅ Item alterado com sucesso!")

                                # Recarregar detalhes
                                novos_detalhes = st.session_state['omie_api'].consultar_recebimento(nIdReceb)
                                if novos_detalhes:
                                    st.session_state['receipt_details'] = novos_detalhes

                                del st.session_state['item_editando']
                                st.rerun()
                            else:
                                erro = resp.get("error", "Erro desconhecido")
                                st.error(f"❌ Erro ao alterar item: {erro}")

                    if cancelar_edit:
                        del st.session_state['item_editando']
                        st.rerun()

        # Botão para concluir recebimento
        st.markdown("---")

        if st.button("✅ CONCLUIR RECEBIMENTO", use_container_width=True, type="primary"):
            confirmar = st.warning("⚠️ Tem certeza que deseja CONCLUIR este recebimento? Esta ação não pode ser desfeita!")

            col1, col2 = st.columns(2)

            with col1:
                if st.button("✅ SIM, CONCLUIR", use_container_width=True):
                    with st.spinner("Concluindo recebimento..."):
                        resp = st.session_state['omie_api'].concluir_recebimento(nIdReceb)

                        if resp and "error" not in resp:
                            st.success(f"✅ Recebimento ID {nIdReceb} concluído com sucesso!")
                            st.balloons()

                            # Limpar sessão
                            if 'recebimento_selecionado' in st.session_state:
                                del st.session_state['recebimento_selecionado']
                            if 'receipt_details' in st.session_state:
                                del st.session_state['receipt_details']
                            if 'recebimentos_lista' in st.session_state:
                                del st.session_state['recebimentos_lista']

                            st.rerun()
                        else:
                            erro = resp.get("error", "Erro desconhecido")
                            st.error(f"❌ Erro ao concluir: {erro}")

            with col2:
                if st.button("❌ CANCELAR", use_container_width=True):
                    st.rerun()
===== TELA 3: POSIÇÃO DE ESTOQUE =====
elif menu == "📦 Posição de Estoque": st.header("📦 Consulta de Posição de Estoque")

if st.button("🔄 Carregar Estoque Completo", use_container_width=True):
    with st.spinner("Carregando dados de estoque... Isso pode levar alguns minutos."):
        estoque_data = st.session_state['omie_api'].listar_todos_estoques()

        if estoque_data:
            st.session_state['estoque_completo'] = estoque_data
            st.success(f"✅ {len(estoque_data)} produtos carregados do estoque")

# Mostrar estoque
if 'estoque_completo' in st.session_state:
    estoque = st.session_state['estoque_completo']

    st.subheader(f"📊 Total de Produtos: {len(estoque)}")

    # Filtros
    col1, col2 = st.columns(2)

    with col1:
        busca_estoque = st.text_input("🔍 Buscar produto:", placeholder="Digite o nome do produto...")

    with col2:
        mostrar_zerados = st.checkbox("Mostrar produtos com estoque zerado", value=False)

    # Filtrar dados
    estoque_filtrado = estoque

    if busca_estoque:
        estoque_filtrado = [
            p for p in estoque_filtrado
            if busca_estoque.lower() in p.get("cDescricao", "").lower()
        ]

    if not mostrar_zerados:
        estoque_filtrado = [
            p for p in estoque_filtrado
            if p.get("nSaldo", 0) != 0
        ]

    # Criar DataFrame
    if estoque_filtrado:
        df_estoque = pd.DataFrame([
            {
                "Código": p.get("nCodProd"),
                "Descrição": p.get("cDescricao"),
                "Saldo": p.get("nSaldo", 0),
                "Custo Unitário": f"R$ {p.get("nCustoUnit", 0):,.2f}",
                "Valor Total": f"R$ {p.get("nValorEstoque", 0):,.2f}"
            }
            for p in estoque_filtrado
        ])

        st.dataframe(
            df_estoque,
            use_container_width=True,
            height=600
        )

        # Botão de exportação
        csv = df_estoque.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Baixar Estoque em CSV",
            data=csv,
            file_name=f"estoque_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    else:
        st.info("ℹ️ Nenhum produto encontrado com os filtros aplicados")
Rodapé
st.markdown("---") st.caption("© 2025 - Sistema Interno Integrado da Empresa | by Peterson B'") ```

