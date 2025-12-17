# omie_api.py
import os
import requests
import json
import unicodedata
import time
from datetime import datetime

# --- CONFIGURAÇÕES DA API OMIE ---
# Tenta ler de variáveis de ambiente (Streamlit Cloud usa st.secrets)
try:
    import streamlit as st
    OMIE_APP_KEY = st.secrets["OMIE_APP_KEY"]
    OMIE_APP_SECRET = st.secrets["OMIE_APP_SECRET"]
except:
    # Fallback para desenvolvimento local
    OMIE_APP_KEY = os.getenv("OMIE_APP_KEY", "4422895577100")
    OMIE_APP_SECRET = os.getenv("OMIE_APP_SECRET", "a70c2d1630e1232dd8a8bef67cb69b08")

OMIE_CLIENTES_URL = "https://app.omie.com.br/api/v1/geral/clientes/"
OMIE_OS_URL = "https://app.omie.com.br/api/v1/servicos/os/"
OMIE_PRODUTOS_URL = "https://app.omie.com.br/api/v1/geral/produtos/"
CALL_LISTAR_PRODUTOS = "ListarProdutos"
OMIE_ESTOQUE_BASE_URL = "https://app.omie.com.br/api/v1/estoque/consulta/"
OMIE_RECEBIMENTO_BASE_URL = "https://app.omie.com.br/api/v1/produtos/recebimentonfe/"
CALL_ESTOQUE = "ListarPosEstoque"

# --- MAPEAMENTOS ---
DEPARTAMENTOS = {
    "1": {"codigo": "3473838422", "descricao": "OBRAS E PROJETOS"},
    "2": {"codigo": "3473838471", "descricao": "MANUTENÇÃO FIXA"},
    "3": {"codigo": "3621044217", "descricao": "LOJA"},
}

CATEGORIAS = {
    "1": {"codigo": "1.01.02", "descricao": "Obra - Serviços Prestados"},
    "2": {"codigo": "1.01.98", "descricao": "Serviços Spot"},
    "3": {"codigo": "1.01.99", "descricao": "Contrato Fixo"},
}

# --- FUNÇÕES AUXILIARES ---
def remove_accents(string):
    nfkd = unicodedata.normalize('NFKD', string)
    return "".join([c for c in nfkd if not unicodedata.combining(c)])

def make_omie_request(url, call, params):
    headers = {"Content-Type": "application/json"}
    payload = {"call": call, "app_key": OMIE_APP_KEY, "app_secret": OMIE_APP_SECRET, "param": params}
    try:
        res = requests.post(url, data=json.dumps(payload), headers=headers)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        return {"error": str(e)}

def listar_clientes_resumido(busca):
    termo = remove_accents(busca).lower()
    clientes = []
    page = 1
    total = 1
    while page <= total:
        params = [{"pagina": page, "registros_por_pagina": 50, "apenas_importado_api": "N"}]
        data = make_omie_request(OMIE_CLIENTES_URL, "ListarClientesResumido", params)
        if not data or "error" in data:
            break
        total = data.get("total_de_paginas", 1)
        for c in data.get("clientes_cadastro_resumido", []):
            nome_fantasia = remove_accents(c.get("nome_fantasia", "")).lower()
            razao_social = remove_accents(c.get("razao_social", "")).lower()
            if termo in nome_fantasia or termo in razao_social:
                clientes.append(c)
        page += 1
        if page <= total:
            time.sleep(0.1)
    return clientes

# --- PRODUTOS ---
LISTA_PRODUTOS_CACHE = None

def consultar_pagina_cadastro_produtos(pagina=1, por_pagina=100):
    payload = {
        "call": CALL_LISTAR_PRODUTOS,
        "app_key": OMIE_APP_KEY,
        "app_secret": OMIE_APP_SECRET,
        "param": [{
            "pagina": pagina,
            "registros_por_pagina": por_pagina,
            "apenas_importado_api": "N",
            "filtrar_apenas_omiepdv": "N",
            "inativo": "N"
        }]
    }
    try:
        r = requests.post(OMIE_PRODUTOS_URL, json=payload)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"Erro ao consultar página {pagina}: {e}")
        return None

def listar_todos_produtos():
    print("Carregando cadastro de produtos da Omie...")
    page = 1
    produtos_total = []
    while True:
        data = consultar_pagina_cadastro_produtos(page)
        if not data:
            break
        lista = data.get("produto_servico_cadastro", [])
        if not lista:
            break
        produtos_total.extend(lista)
        total_paginas = data.get("total_de_paginas", 1)
        if page >= total_paginas:
            break
        page += 1
        time.sleep(0.2)
    print(f"{len(produtos_total)} produtos obtidos do cadastro.")
    return produtos_total

def extrair_nomes_e_codigos(lista):
    resultado = []
    for p in lista:
        nome = p.get("descricao")
        cod = p.get("codigo_produto")
        if nome and cod:
            resultado.append({"nome": nome, "codigo": cod})
    return resultado

def carregar_lista_produtos_cache():
    global LISTA_PRODUTOS_CACHE
    if LISTA_PRODUTOS_CACHE is not None:
        print(f"Lista cacheada ({len(LISTA_PRODUTOS_CACHE)} produtos).")
        return LISTA_PRODUTOS_CACHE
    dados = listar_todos_produtos()
    produtos = extrair_nomes_e_codigos(dados)
    LISTA_PRODUTOS_CACHE = produtos
    print(f"Cache criado com {len(LISTA_PRODUTOS_CACHE)} produtos.")
    return LISTA_PRODUTOS_CACHE

def pesquisar_produtos_por_nome(lista, termo):
    termo = remove_accents(termo).lower()
    return [p for p in lista if termo in remove_accents(p["nome"]).lower()]

def incluir_os(os_payload):
    return make_omie_request(OMIE_OS_URL, "IncluirOS", [os_payload])

# --- CLASSE: OmieEstoqueAPI ---
class OmieEstoqueAPI:
    def __init__(self, app_key, app_secret, base_url_estoque):
        self.app_key = app_key
        self.app_secret = app_secret
        self.base_url_estoque = base_url_estoque

    def _send_request(self, call_method, params, custom_base_url=None):
        url_to_use = custom_base_url if custom_base_url else self.base_url_estoque
        payload = {
            "call": call_method,
            "app_key": self.app_key,
            "app_secret": self.app_secret,
            "param": [params],
        }
        headers = {"Content-Type": "application/json"}
        try:
            response = requests.post(url_to_use, headers=headers, data=json.dumps(payload))
            response.raise_for_status()
            data = response.json()
            if "faultstring" in data:
                return {"error": f"{data['faultstring']} (Código: {data['faultcode']})"}
            return data
        except Exception as e:
            return {"error": str(e)}

    def consultar_pagina_estoque(self, pagina: int, data_posicao: str = None, registros_por_pagina: int = 50):
        if data_posicao is None:
            data_posicao = datetime.now().strftime("%d/%m/%Y")
        params = {
            "nPagina": pagina,
            "nRegPorPagina": registros_por_pagina,
            "dDataPosicao": data_posicao,
            "cExibeTodos": "S",
            "codigo_local_estoque": 0
        }
        return self._send_request(CALL_ESTOQUE, params, custom_base_url=self.base_url_estoque)

    def listar_todos_estoques(self):
        pagina = 1
        todos_itens = []
        while True:
            data = self.consultar_pagina_estoque(pagina)
            if not data or "error" in data:
                break
            produtos = data.get("produtos", [])
            if not produtos:
                break
            todos_itens.extend(produtos)
            total_paginas = data.get("nTotPaginas", 1)
            if pagina >= total_paginas:
                break
            pagina += 1
        return todos_itens

    def listar_recebimentos(self, page, records_per_page=50, cEtapa="40"):
        params = {"nPagina": page, "nRegistrosPorPaginas": records_per_page, "cEtapa": cEtapa}
        return self._send_request("ListarRecebimentos", params, custom_base_url=OMIE_RECEBIMENTO_BASE_URL)

    def consultar_recebimento(self, nIdReceb):
        return self._send_request("ConsultarRecebimento", {"nIdReceb": nIdReceb}, custom_base_url=OMIE_RECEBIMENTO_BASE_URL)

    def alterar_recebimento(self, payload):
        return self._send_request("AlterarRecebimento", payload, custom_base_url=OMIE_RECEBIMENTO_BASE_URL)

    def concluir_recebimento(self, nIdReceb):
        return self._send_request("ConcluirRecebimento", {"nIdReceb": nIdReceb}, custom_base_url=OMIE_RECEBIMENTO_BASE_URL)

def extrair_nomes_e_codigos_produtos(produtos_data: list):
    lista_produtos_formatada = []
    for produto in produtos_data:
        nome = produto.get("cDescricao")
        codigo = produto.get("nCodProd")
        if nome and codigo is not None:
            lista_produtos_formatada.append({"nome": nome, "codigo": codigo})
    return lista_produtos_formatada
