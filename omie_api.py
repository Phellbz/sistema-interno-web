import requests
import json
import unicodedata
import time
from datetime import datetime
import os
import streamlit as st

# Streamlit expõe secrets como dicionário
OMIE_APP_KEY = st.secrets["OMIE_APP_KEY"]
OMIE_APP_SECRET = st.secrets["OMIE_APP_SECRET"]

# --- CONFIGURAÇÕES DA API OMIE ---
OMIE_CLIENTES_URL = "https://app.omie.com.br/api/v1/geral/clientes/"
OMIE_OS_URL = "https://app.omie.com.br/api/v1/servicos/os/"
OMIE_PRODUTOS_URL = "https://app.omie.com.br/api/v1/geral/produtos/"
OMIE_ESTOQUE_BASE_URL = "https://app.omie.com.br/api/v1/estoque/consulta/"
OMIE_RECEBIMENTO_BASE_URL = "https://app.omie.com.br/api/v1/produtos/recebimentonfe/"

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

def incluir_os(os_payload):
    return make_omie_request(OMIE_OS_URL, "IncluirOS", [os_payload])

def listar_todos_produtos():
    page = 1
    produtos_total = []
    while True:
        payload = {
            "call": "ListarProdutos",
            "app_key": OMIE_APP_KEY,
            "app_secret": OMIE_APP_SECRET,
            "param": [{
                "pagina": page,
                "registros_por_pagina": 100,
                "apenas_importado_api": "N",
                "filtrar_apenas_omiepdv": "N",
                "inativo": "N"
            }]
        }
        try:
            r = requests.post(OMIE_PRODUTOS_URL, json=payload)
            r.raise_for_status()
            data = r.json()
        except:
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
    return produtos_total

def extrair_nomes_e_codigos(lista):
    resultado = []
    for p in lista:
        nome = p.get("descricao")
        cod = p.get("codigo_produto")
        if nome and cod:
            resultado.append({"nome": nome, "codigo": cod})
    return resultado

def pesquisar_produtos_por_nome(lista, termo):
    termo = remove_accents(termo).lower()
    return [p for p in lista if termo in remove_accents(p["nome"]).lower()]

class OmieEstoqueAPI:
    def __init__(self):
        self.app_key = OMIE_APP_KEY
        self.app_secret = OMIE_APP_SECRET

    def _send_request(self, call_method, params, custom_base_url=None):
        url_to_use = custom_base_url if custom_base_url else OMIE_ESTOQUE_BASE_URL
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
                return None
            return data
        except:
            return None

    def listar_recebimentos(self, page, records_per_page=50, cEtapa="40"):
        params = {"nPagina": page, "nRegistrosPorPagina": records_per_page, "cEtapa": cEtapa}
        return self._send_request("ListarRecebimentos", params, custom_base_url=OMIE_RECEBIMENTO_BASE_URL)

    def consultar_recebimento(self, nIdReceb):
        return self._send_request("ConsultarRecebimento", {"nIdReceb": nIdReceb}, custom_base_url=OMIE_RECEBIMENTO_BASE_URL)

    def alterar_recebimento(self, payload):
        return self._send_request("AlterarRecebimento", payload, custom_base_url=OMIE_RECEBIMENTO_BASE_URL)

    def concluir_recebimento(self, nIdReceb):
        return self._send_request("ConcluirRecebimento", {"nIdReceb": nIdReceb}, custom_base_url=OMIE_RECEBIMENTO_BASE_URL)
