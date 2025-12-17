import streamlit as st
from omie_api import *
import uuid
from datetime import datetime
import pandas as pd

# Importa tudo do módulo omie_api
from omie_api import (
    DEPARTAMENTOS,
    CATEGORIAS,
    listar_clientes_resumido,
    carregar_lista_produtos_cache,
    pesquisar_produtos_por_nome,
    incluir_os,
    OmieEstoqueAPI,
    extrair_nomes_e_codigos_produtos,
    OMIE_ESTOQUE_BASE_URL
)
from config import OMIE_APP_KEY, OMIE_APP_SECRET

# ====================================================================================
# CLASSE 1: ClientSelectionWindow (Primeira Tela)
# ====================================================================================
class ClientSelectionWindow(tk.Toplevel):
    def __init__(self, master, on_client_selected_callback):
        super().__init__(master)
        self.master = master
        self.on_client_selected_callback = on_client_selected_callback
        self.title("Seleção de Cliente para OS")
        self.geometry("700x500") # Tamanho ajustado para a primeira tela
        self.configure(bg="#F3F6FA")
        self.resizable(False, False)
        self.grab_set() # Torna a janela modal
        self.focus_set() # Garante que a janela receba o foco
        self.protocol("WM_DELETE_WINDOW", self.on_close) # Lida com o fechamento da janela
        self.selected_client = None
        self.clients_found_cache = []
        self.create_styles()
        self.create_widgets()

    def create_styles(self):
        # Estilo para o botão primário (Buscar Cliente, Continuar)
        self.style = ttk.Style()
        self.style.configure("Primary.TButton",
                             font=("Segoe UI", 10, "bold"),
                             background="#007ACC", # Azul
                             foreground="white",
                             relief="flat",
                             padding=6)
        self.style.map("Primary.TButton",
                       background=[("active", "#005E9E")]) # Azul mais escuro ao ativar
        # Estilo para os botões de navegação (Cancelar, Voltar)
        self.style.configure("Nav.TButton",
                             font=("Segoe UI", 10),
                             background="#6c757d", # Cinza
                             foreground="white",
                             relief="flat",
                             padding=6)
        self.style.map("Nav.TButton",
                       background=[("active", "#5a6268")]) # Cinza mais escuro ao ativar

    def create_widgets(self):
        main_frame = tk.Frame(self, bg="#F3F6FA", padx=20, pady=20)
        main_frame.pack(expand=True, fill="both")

        title_label = tk.Label(
            main_frame,
            text="Buscar e Selecionar Cliente Omie",
            font=("Segoe UI", 18, "bold"),
            bg="#F3F6FA",
            fg="#004E8C"
        )
        title_label.pack(pady=(0, 20))

        label_font = ("Segoe UI", 10, "bold")
        entry_font = ("Segoe UI", 10)

        tk.Label(main_frame, text="Nome/Razão Social para busca:", font=label_font, bg="#F3F6FA", fg="#333").pack(anchor="w", pady=(0, 2))
        self.search_entry = ttk.Entry(main_frame, font=entry_font)
        self.search_entry.pack(fill="x", pady=(0, 10))
        self.search_entry.bind("<Return>", self.search_clients_omie)

        button_frame = tk.Frame(main_frame, bg="#F3F6FA")
        button_frame.pack(fill="x", pady=(5, 10))
        ttk.Button(button_frame, text="Buscar Cliente", command=self.search_clients_omie, style="Primary.TButton").pack(side="left", padx=5)

        self.status_label = tk.Label(button_frame, text="", font=("Segoe UI", 9, "italic"), bg="#F3F6FA", fg="#666")
        self.status_label.pack(side="left", padx=10)

        # Treeview para exibir os resultados da busca
        self.client_tree = ttk.Treeview(main_frame, columns=("codigo_cliente", "nome_fantasia", "razao_social"), show="headings", height=8)
        self.client_tree.heading("codigo_cliente", text="Cód. Cliente")
        self.client_tree.heading("nome_fantasia", text="Nome Fantasia")
        self.client_tree.heading("razao_social", text="Razão Social")
        self.client_tree.column("codigo_cliente", width=80, anchor="center")
        self.client_tree.column("nome_fantasia", width=180, anchor="w")
        self.client_tree.column("razao_social", width=240, anchor="w")
        self.client_tree.pack(fill="x", expand=True, pady=(0, 10))

        # --- AJUSTE: Habilitar seleção com um único clique ---
        self.client_tree.bind("<<TreeviewSelect>>", self.select_client_from_treeview)

        self.selected_client_label = tk.Label(main_frame, text="Cliente Selecionado: Nenhum",
                                              font=("Segoe UI", 10, "italic"), bg="#F3F6FA", fg="#333")
        self.selected_client_label.pack(anchor="w", pady=(5, 0))

        # Botões de navegação
        nav_button_frame = tk.Frame(main_frame, bg="#F3F6FA", pady=10)
        nav_button_frame.pack(fill="x", side="bottom")
        ttk.Button(nav_button_frame, text="Cancelar", command=self.on_close, style="Nav.TButton").pack(side="left", padx=5)
        self.continue_button = ttk.Button(nav_button_frame, text="Continuar para Detalhes da OS >>",
                                          command=self.continue_to_os_details, state="disabled", style="Primary.TButton")
        self.continue_button.pack(side="right", padx=5)

    def search_clients_omie(self, event=None):
        search_term = self.search_entry.get().strip()
        if not search_term:
            messagebox.showwarning("Busca de Cliente", "Por favor, digite um termo para buscar.", parent=self)
            return

        self.status_label.config(text="Buscando clientes...", fg="#007ACC")
        self.client_tree.delete(*self.client_tree.get_children())
        self.selected_client = None
        self.selected_client_label.config(text="Cliente Selecionado: Nenhum", fg="#333")
        self.continue_button.config(state="disabled")
        self.update_idletasks()

        self.clients_found_cache = listar_clientes_resumido(search_term)

        if self.clients_found_cache:
            for c in self.clients_found_cache:
                self.client_tree.insert("", "end", values=(
                    c.get("codigo_cliente"),
                    c.get("nome_fantasia", "N/A"),
                    c.get("razao_social", "N/A")
                ))
            self.status_label.config(text=f"{len(self.clients_found_cache)} clientes encontrados.", fg="#004E8C")
        else:
            self.status_label.config(text="Nenhum cliente encontrado.", fg="red")

    def select_client_from_treeview(self, event=None):
        selected_item = self.client_tree.focus()
        if selected_item:
            values = self.client_tree.item(selected_item, "values")
            codigo_cliente = values[0]
            self.selected_client = next((c for c in self.clients_found_cache if str(c.get("codigo_cliente")) == str(codigo_cliente)), None)

            if self.selected_client:
                display_text = f"Cliente Selecionado: {self.selected_client.get('nome_fantasia', 'N/A')} ({self.selected_client.get('razao_social', 'N/A')})"
                self.selected_client_label.config(text=display_text, fg="#004E8C")
                self.continue_button.config(state="normal")
            else:
                self.selected_client_label.config(text="Cliente Selecionado: Erro ao carregar dados.", fg="red")
                self.continue_button.config(state="disabled")
        else:
            self.selected_client_label.config(text="Cliente Selecionado: Nenhum", fg="#333")
            self.continue_button.config(state="disabled")

    def continue_to_os_details(self):
        if self.selected_client:
            self.destroy() # Fecha a janela de seleção de cliente
            self.on_client_selected_callback(self.selected_client) # Chama o callback para abrir a próxima janela
        else:
            messagebox.showwarning("Seleção de Cliente", "Por favor, selecione um cliente para continuar.", parent=self)

    def on_close(self):
        self.master.deiconify() # Mostra a janela principal novamente
        self.destroy()

# ====================================================================================
# CLASSE 2: OSDetailsWindow (Segunda Tela)
# ====================================================================================
class OSDetailsWindow(tk.Toplevel):
    def __init__(self, master, selected_client_data, os_data=None):
        super().__init__(master)
        self.master = master
        self.selected_client = selected_client_data
        self.title("Detalhes da Ordem de Serviço")
        self.geometry("800x750") # Tamanho ajustado para a segunda tela
        self.configure(bg="#F3F6FA")
        self.resizable(False, False)
        self.grab_set()
        self.focus_set()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.os_data = os_data if os_data else {
            'selected_client': self.selected_client,
            'data_prev_faturamento': None,
            'quantidade_parcelas': 1,
            'departamento': None,
            'categoria': None,
            'reter_iss': 'N',
            'num_servicos': 0,
            'servicos': [],
            'produtos': [], # Para uso futuro
            'valor_total_os': 0.0
        }
        self.service_entry_vars = [] # Lista para armazenar as variáveis de entrada dos serviços
        self.service_frames = [] # Lista para armazenar os frames de cada serviço

        self.create_styles()
        self.create_widgets()
        self.load_os_data() # Carrega dados se estiver voltando da revisão

    def create_styles(self):
        self.style = ttk.Style()
        self.style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"), background="#007ACC", foreground="white", relief="flat", padding=6)
        self.style.map("Primary.TButton", background=[("active", "#005E9E")])
        self.style.configure("Nav.TButton", font=("Segoe UI", 10), background="#6c757d", foreground="white", relief="flat", padding=6)
        self.style.map("Nav.TButton", background=[("active", "#5a6268")])
        self.style.configure("Danger.TButton", font=("Segoe UI", 10, "bold"), background="#dc3545", foreground="white", relief="flat", padding=6)
        self.style.map("Danger.TButton", background=[("active", "#c82333")])
        self.style.configure("Success.TButton", font=("Segoe UI", 10, "bold"), background="#28a745", foreground="white", relief="flat", padding=6)
        self.style.map("Success.TButton", background=[("active", "#218838")])
        self.style.configure("Info.TButton", font=("Segoe UI", 10, "bold"), background="#17a2b8", foreground="white", relief="flat", padding=6)
        self.style.map("Info.TButton", background=[("active", "#138496")])

    def create_widgets(self):
        main_frame = tk.Frame(self, bg="#F3F6FA", padx=20, pady=20)
        main_frame.pack(expand=True, fill="both")

        title_label = tk.Label(
            main_frame,
            text="Detalhes da Ordem de Serviço",
            font=("Segoe UI", 18, "bold"),
            bg="#F3F6FA",
            fg="#004E8C"
        )
        title_label.pack(pady=(0, 15))

        label_font = ("Segoe UI", 10, "bold")
        entry_font = ("Segoe UI", 10)

        # Cliente Selecionado
        tk.Label(main_frame, text="Cliente Selecionado:", font=label_font, bg="#F3F6FA", fg="#333").pack(anchor="w", pady=(0, 2))
        self.client_display_label = tk.Label(main_frame, text=f"{self.selected_client.get('nome_fantasia', 'N/A')} ({self.selected_client.get('razao_social', 'N/A')})",
                                              font=("Segoe UI", 10, "italic"), bg="#F3F6FA", fg="#004E8C")
        self.client_display_label.pack(anchor="w", pady=(0, 15))

        # Frame para os campos principais da OS
        os_details_frame = tk.LabelFrame(main_frame, text="Dados Gerais da OS", font=label_font, bg="#F3F6FA", fg="#004E8C", bd=2, padx=10, pady=10)
        os_details_frame.pack(fill="x", pady=(0, 15))

        # Data de Previsão de Faturamento
        tk.Label(os_details_frame, text="Data de Previsão de Faturamento (DD/MM/AAAA):", font=label_font, bg="#F3F6FA", fg="#333").grid(row=0, column=0, sticky="w", pady=5, padx=5)
        self.data_prev_entry = ttk.Entry(os_details_frame, font=entry_font)
        self.data_prev_entry.grid(row=0, column=1, sticky="ew", pady=5, padx=5)
        self.data_prev_entry.insert(0, datetime.now().strftime("%d/%m/%Y")) # Valor padrão

        # Quantidade de Parcelas
        tk.Label(os_details_frame, text="Quantidade de Parcelas:", font=label_font, bg="#F3F6FA", fg="#333").grid(row=1, column=0, sticky="w", pady=5, padx=5)
        self.parcelas_entry = ttk.Entry(os_details_frame, font=entry_font)
        self.parcelas_entry.grid(row=1, column=1, sticky="ew", pady=5, padx=5)
        self.parcelas_entry.insert(0, "1") # Valor padrão

        # Departamento
        tk.Label(os_details_frame, text="Departamento:", font=label_font, bg="#F3F6FA", fg="#333").grid(row=2, column=0, sticky="w", pady=5, padx=5)
        self.departamento_combobox = ttk.Combobox(os_details_frame, values=[d["descricao"] for d in DEPARTAMENTOS.values()], state="readonly", font=entry_font)
        self.departamento_combobox.grid(row=2, column=1, sticky="ew", pady=5, padx=5)
        if DEPARTAMENTOS: self.departamento_combobox.set(DEPARTAMENTOS["1"]["descricao"]) # Valor padrão

        # Categoria
        tk.Label(os_details_frame, text="Categoria:", font=label_font, bg="#F3F6FA", fg="#333").grid(row=3, column=0, sticky="w", pady=5, padx=5)
        self.categoria_combobox = ttk.Combobox(os_details_frame, values=[c["descricao"] for c in CATEGORIAS.values()], state="readonly", font=entry_font)
        self.categoria_combobox.grid(row=3, column=1, sticky="ew", pady=5, padx=5)
        if CATEGORIAS: self.categoria_combobox.set(CATEGORIAS["1"]["descricao"]) # Valor padrão

        # Reter ISS
        tk.Label(os_details_frame, text="Reter ISS:", font=label_font, bg="#F3F6FA", fg="#333").grid(row=4, column=0, sticky="w", pady=5, padx=5)
        self.reter_iss_var = tk.StringVar(value="N")
        reter_iss_frame = tk.Frame(os_details_frame, bg="#F3F6FA")
        reter_iss_frame.grid(row=4, column=1, sticky="w", pady=5, padx=5)
        ttk.Radiobutton(reter_iss_frame, text="Sim", variable=self.reter_iss_var, value="S").pack(side="left", padx=5)
        ttk.Radiobutton(reter_iss_frame, text="Não", variable=self.reter_iss_var, value="N").pack(side="left", padx=5)

        os_details_frame.grid_columnconfigure(1, weight=1)

        tk.Label(os_details_frame, text="Gerar Conta a Pagar?", 
         font=label_font, bg="#F3F6FA", fg="#333").grid(row=5, column=0, sticky="w", pady=5, padx=5)

        self.gerar_financeiro_var = tk.StringVar(value="Não")

        ttk.Combobox(os_details_frame,
                    textvariable=self.gerar_financeiro_var,
                    values=["Sim", "Não"],
                    state="readonly",
                    font=entry_font
                    ).grid(row=5, column=1, sticky="ew", pady=5, padx=5)

        # Número de Serviços
        tk.Label(main_frame, text="Número de Serviços a Adicionar:", font=label_font, bg="#F3F6FA", fg="#333").pack(anchor="w", pady=(10, 2))
        num_services_frame = tk.Frame(main_frame, bg="#F3F6FA")
        num_services_frame.pack(fill="x", pady=(0, 10))
        self.num_services_entry = ttk.Entry(num_services_frame, font=entry_font, width=10)
        self.num_services_entry.pack(side="left", padx=5)
        self.num_services_entry.insert(0, "1") # Valor padrão

        # --- AJUSTE: Mover os botões de navegação para o final para garantir visibilidade ---
        # Botões de navegação (Empacotado primeiro com side="bottom" para garantir que fique no final da janela)
        nav_button_frame = tk.Frame(main_frame, bg="#F3F6FA", pady=10)
        nav_button_frame.pack(fill="x", side="bottom")
        ttk.Button(nav_button_frame, text="Voltar para Seleção de Cliente", command=self.go_back_to_client_selection, style="Nav.TButton").pack(side="left", padx=5)

        # Os botões "Gerar Campos de Serviço" e "Continuar para Revisão da OS" agora estarão visíveis
        self.generate_services_button = ttk.Button(num_services_frame, text="Gerar Campos de Serviço", command=self.generate_service_input_fields, style="Primary.TButton")
        self.generate_services_button.pack(side="left", padx=5) # Este botão permanece junto ao campo de número de serviços

        self.continue_button = ttk.Button(nav_button_frame, text="Continuar para Revisão da OS >>",
                                          command=self.continue_to_os_review, state="disabled", style="Primary.TButton")
        self.continue_button.pack(side="right", padx=5)
        # --- FIM DO AJUSTE ---

        # Frame para os campos de serviço dinâmicos (Agora empacotado depois dos botões de navegação)
        self.services_input_frame = tk.LabelFrame(main_frame, text="Detalhes dos Serviços", font=label_font, bg="#F3F6FA", fg="#004E8C", bd=2, padx=10, pady=10)
        self.services_input_frame.pack(fill="both", expand=True, pady=(0, 15)) # Este frame preencherá o espaço restante

        # Adiciona um Canvas e Scrollbar para o services_input_frame
        self.canvas = tk.Canvas(self.services_input_frame, bg="#F3F6FA", highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.services_input_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg="#F3F6FA")

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

    def load_os_data(self):
        if self.os_data['data_prev_faturamento']:
            self.data_prev_entry.delete(0, tk.END)
            self.data_prev_entry.insert(0, self.os_data['data_prev_faturamento'].strftime("%d/%m/%Y"))
        if self.os_data['quantidade_parcelas']:
            self.parcelas_entry.delete(0, tk.END)
            self.parcelas_entry.insert(0, str(self.os_data['quantidade_parcelas']))
        if self.os_data['departamento']:
            self.departamento_combobox.set(self.os_data['departamento']['descricao'])
        if self.os_data['categoria']:
            self.categoria_combobox.set(self.os_data['categoria']['descricao'])
        self.reter_iss_var.set(self.os_data['reter_iss'])

        if self.os_data['num_servicos'] > 0:
            self.num_services_entry.delete(0, tk.END)
            self.num_services_entry.insert(0, str(self.os_data['num_servicos']))
            self.generate_service_input_fields(load_existing=True)
            self.continue_button.config(state="normal") # Habilita o botão de continuar se já houver serviços

    def generate_service_input_fields(self, load_existing=False):
        # Limpa campos existentes
        for frame in self.service_frames:
            frame.destroy()
        self.service_frames.clear()
        self.service_entry_vars.clear()

        try:
            num_services = int(self.num_services_entry.get())
            if num_services <= 0:
                messagebox.showwarning("Entrada Inválida", "O número de serviços deve ser maior que zero.", parent=self)
                return
        except ValueError:
            messagebox.showwarning("Entrada Inválida", "Por favor, insira um número válido para a quantidade de serviços.", parent=self)
            return

        for i in range(num_services):
            service_frame = tk.LabelFrame(self.scrollable_frame, text=f"Serviço {i+1}", font=("Segoe UI", 9, "bold"), bg="#F3F6FA", fg="#004E8C", bd=1, padx=5, pady=5)
            service_frame.pack(fill="x", padx=5, pady=5)
            self.service_frames.append(service_frame)

            desc_var = tk.StringVar()
            qty_var = tk.StringVar(value="1")
            val_unit_var = tk.StringVar(value="0.00")

            if load_existing and i < len(self.os_data['servicos']):
                service = self.os_data['servicos'][i]
                desc_var.set(service['cDescServ'])
                qty_var.set(str(service['nQtde']))
                val_unit_var.set(f"{service['nValUnit']:.2f}")

            tk.Label(service_frame, text="Descrição:", font=("Segoe UI", 9), bg="#F3F6FA", fg="#333").grid(row=0, column=0, sticky="w", padx=2, pady=2)
            service_frame.grid_columnconfigure(1, weight=1)
            ttk.Entry(service_frame, textvariable=desc_var, font=("Segoe UI", 9), width=80).grid(row=0, column=1, sticky="ew", padx=5, pady=2)

            tk.Label(service_frame, text="Quantidade:", font=("Segoe UI", 9), bg="#F3F6FA", fg="#333").grid(row=1, column=0, sticky="w", padx=2, pady=2)
            ttk.Entry(service_frame, textvariable=qty_var, font=("Segoe UI", 9)).grid(row=1, column=1, sticky="ew", padx=2, pady=2)

            tk.Label(service_frame, text="Valor Unitário:", font=("Segoe UI", 9), bg="#F3F6FA", fg="#333").grid(row=2, column=0, sticky="w", padx=2, pady=2)
            ttk.Entry(service_frame, textvariable=val_unit_var, font=("Segoe UI", 9)).grid(row=2, column=1, sticky="ew", padx=2, pady=2)

            service_frame.grid_columnconfigure(1, weight=1)
            self.service_entry_vars.append({'desc': desc_var, 'qty': qty_var, 'val_unit': val_unit_var})

        self.canvas.update_idletasks()
        self.canvas.config(scrollregion=self.canvas.bbox("all"))
        self.continue_button.config(state="normal") # Habilita o botão de continuar após gerar os campos

    def continue_to_os_review(self):
        # 1. Validar e coletar dados gerais da OS
        try:
            data_prev_str = self.data_prev_entry.get()
            data_prev_faturamento = datetime.strptime(data_prev_str, "%d/%m/%Y")
        except ValueError:
            messagebox.showerror("Erro de Validação", "Formato de data inválido. Use DD/MM/AAAA.", parent=self)
            return

        try:
            quantidade_parcelas = int(self.parcelas_entry.get())
            if quantidade_parcelas <= 0:
                messagebox.showerror("Erro de Validação", "A quantidade de parcelas deve ser maior que zero.", parent=self)
                return
        except ValueError:
            messagebox.showerror("Erro de Validação", "Quantidade de parcelas inválida.", parent=self)
            return

        departamento_desc = self.departamento_combobox.get()
        departamento = next((d for d in DEPARTAMENTOS.values() if d["descricao"] == departamento_desc), None)
        if not departamento:
            messagebox.showerror("Erro de Validação", "Departamento inválido selecionado.", parent=self)
            return

        categoria_desc = self.categoria_combobox.get()
        categoria = next((c for c in CATEGORIAS.values() if c["descricao"] == categoria_desc), None)
        if not categoria:
            messagebox.showerror("Erro de Validação", "Categoria inválida selecionada.", parent=self)
            return

        reter_iss = self.reter_iss_var.get()

        # 2. Validar e coletar dados dos serviços
        servicos_para_omie = []
        valor_total_os = 0.0
        for i, service_vars in enumerate(self.service_entry_vars):
            desc = service_vars['desc'].get().strip()
            qty_str = service_vars['qty'].get().strip()
            val_unit_str = service_vars['val_unit'].get().strip().replace(',', '.') # Substitui vírgula por ponto para float

            if not desc:
                messagebox.showerror("Erro de Validação", f"Descrição do Serviço {i+1} não pode estar vazia.", parent=self)
                return
            try:
                qty = float(qty_str)
                if qty <= 0:
                    messagebox.showerror("Erro de Validação", f"Quantidade do Serviço {i+1} deve ser maior que zero.", parent=self)
                    return
            except ValueError:
                messagebox.showerror("Erro de Validação", f"Quantidade inválida para o Serviço {i+1}.", parent=self)
                return
            try:
                val_unit = float(val_unit_str)
                if val_unit < 0:
                    messagebox.showerror("Erro de Validação", f"Valor Unitário do Serviço {i+1} não pode ser negativo.", parent=self)
                    return
            except ValueError:
                messagebox.showerror("Erro de Validação", f"Valor Unitário inválido para o Serviço {i+1}.", parent=self)
                return

            servicos_para_omie.append({
                "cDescServ": desc,
                "nQtde": qty,
                "nValUnit": val_unit
            })
            valor_total_os += (qty * val_unit)

        if not servicos_para_omie:
            messagebox.showwarning("Serviços Vazios", "Nenhum serviço foi adicionado à OS.", parent=self)
            return

        # 3. Armazenar todos os dados na variável self.os_data
        self.os_data.update({
            'data_prev_faturamento': data_prev_faturamento,
            'quantidade_parcelas': quantidade_parcelas,
            'departamento': departamento,
            'categoria': categoria,
            'reter_iss': reter_iss,
            'num_servicos': len(servicos_para_omie),
            'servicos': servicos_para_omie,
            'valor_total_os': valor_total_os,
            'gerar_financeiro': self.gerar_financeiro_var.get()
        })

        # 4. Abrir a próxima janela (Revisão da OS)
        self.destroy()
        OSReviewWindow(self.master, self.os_data)

    def go_back_to_client_selection(self):
        self.destroy()
        # Reabre a janela de seleção de cliente
        ClientSelectionWindow(self.master, self.master.on_client_selected)

    def on_close(self):
        self.master.deiconify() # Mostra a janela principal novamente
        self.destroy()

# ====================================================================================
# CLASSE 3: OSReviewWindow (Terceira Tela)
# ====================================================================================
class OSReviewWindow(tk.Toplevel):
    def __init__(self, master, os_data):
        try:
            super().__init__(master)
            self.master = master
            self.os_data = os_data
            self.title("Revisão da Ordem de Serviço")
            self.geometry("850x700")
            self.configure(bg="#F3F6FA")
            self.resizable(False, False)
            self.grab_set()
            self.focus_set()
            self.protocol("WM_DELETE_WINDOW", self.on_close)
            self.create_styles()
            self.create_widgets()
            self.display_os_data()
        except Exception as e:
            print(f"[ERRO] Falha ao inicializar OSReviewWindow: {e}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Erro na Janela de Revisão", f"Erro ao abrir tela de revisão:\n{e}")
            raise

    def create_styles(self):
        self.style = ttk.Style()
        self.style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"), background="#007ACC", foreground="white", relief="flat", padding=6)
        self.style.map("Primary.TButton", background=[("active", "#005E9E")])
        self.style.configure("Nav.TButton", font=("Segoe UI", 10), background="#6c757d", foreground="white", relief="flat", padding=6)
        self.style.map("Nav.TButton", background=[("active", "#5a6268")])
        self.style.configure("Success.TButton", font=("Segoe UI", 10, "bold"), background="#28a745", foreground="white", relief="flat", padding=6)
        self.style.map("Success.TButton", background=[("active", "#218838")])
        self.style.configure("Info.TButton", font=("Segoe UI", 10, "bold"), background="#17a2b8", foreground="white", relief="flat", padding=6)
        self.style.map("Info.TButton", background=[("active", "#138496")])

    def create_widgets(self):
        main_frame = tk.Frame(self, bg="#F3F6FA", padx=20, pady=20)
        main_frame.pack(expand=True, fill="both")

        title_label = tk.Label(
            main_frame,
            text="Revisão da Ordem de Serviço",
            font=("Segoe UI", 18, "bold"),
            bg="#F3F6FA",
            fg="#004E8C"
        )
        title_label.pack(pady=(0, 15))

        label_font = ("Segoe UI", 10, "bold")
        value_font = ("Segoe UI", 10)

        # Frame para dados do Cliente
        client_frame = tk.LabelFrame(main_frame, text="Cliente", font=label_font, bg="#F3F6FA", fg="#004E8C", bd=2, padx=10, pady=10)
        client_frame.pack(fill="x", pady=(0, 15))
        tk.Label(client_frame, text="Cód. Cliente:", font=label_font, bg="#F3F6FA", fg="#333").grid(row=0, column=0, sticky="w", pady=2, padx=5)
        self.client_code_label = tk.Label(client_frame, font=value_font, bg="#F3F6FA", fg="#333")
        self.client_code_label.grid(row=0, column=1, sticky="w", pady=2, padx=5)
        tk.Label(client_frame, text="Nome Fantasia:", font=label_font, bg="#F3F6FA", fg="#333").grid(row=1, column=0, sticky="w", pady=2, padx=5)
        self.client_fantasia_label = tk.Label(client_frame, font=value_font, bg="#F3F6FA", fg="#333")
        self.client_fantasia_label.grid(row=1, column=1, sticky="w", pady=2, padx=5)
        tk.Label(client_frame, text="Razão Social:", font=label_font, bg="#F3F6FA", fg="#333").grid(row=2, column=0, sticky="w", pady=2, padx=5)
        self.client_razao_label = tk.Label(client_frame, font=value_font, bg="#F3F6FA", fg="#333")
        self.client_razao_label.grid(row=2, column=1, sticky="w", pady=2, padx=5)
        client_frame.grid_columnconfigure(1, weight=1)

        # Frame para dados gerais da OS
        os_details_frame = tk.LabelFrame(main_frame, text="Dados Gerais da OS", font=label_font, bg="#F3F6FA", fg="#004E8C", bd=2, padx=10, pady=10)
        os_details_frame.pack(fill="x", pady=(0, 15))
        tk.Label(os_details_frame, text="Data Previsão Faturamento:", font=label_font, bg="#F3F6FA", fg="#333").grid(row=0, column=0, sticky="w", pady=2, padx=5)
        self.data_prev_label = tk.Label(os_details_frame, font=value_font, bg="#F3F6FA", fg="#333")
        self.data_prev_label.grid(row=0, column=1, sticky="w", pady=2, padx=5)
        tk.Label(os_details_frame, text="Qtd. Parcelas:", font=label_font, bg="#F3F6FA", fg="#333").grid(row=1, column=0, sticky="w", pady=2, padx=5)
        self.parcelas_label = tk.Label(os_details_frame, font=value_font, bg="#F3F6FA", fg="#333")
        self.parcelas_label.grid(row=1, column=1, sticky="w", pady=2, padx=5)
        tk.Label(os_details_frame, text="Departamento:", font=label_font, bg="#F3F6FA", fg="#333").grid(row=2, column=0, sticky="w", pady=2, padx=5)
        self.departamento_label = tk.Label(os_details_frame, font=value_font, bg="#F3F6FA", fg="#333")
        self.departamento_label.grid(row=2, column=1, sticky="w", pady=2, padx=5)
        tk.Label(os_details_frame, text="Categoria:", font=label_font, bg="#F3F6FA", fg="#333").grid(row=3, column=0, sticky="w", pady=2, padx=5)
        self.categoria_label = tk.Label(os_details_frame, font=value_font, bg="#F3F6FA", fg="#333")
        self.categoria_label.grid(row=3, column=1, sticky="w", pady=2, padx=5)
        tk.Label(os_details_frame, text="Reter ISS:", font=label_font, bg="#F3F6FA", fg="#333").grid(row=4, column=0, sticky="w", pady=2, padx=5)
        self.reter_iss_label = tk.Label(os_details_frame, font=value_font, bg="#F3F6FA", fg="#333")
        self.reter_iss_label.grid(row=4, column=1, sticky="w", pady=2, padx=5)
        os_details_frame.grid_columnconfigure(1, weight=1)

        # Botões de Ação (Empacotado primeiro com side="bottom" para garantir que fique no final da janela)
        action_button_frame = tk.Frame(main_frame, bg="#F3F6FA", pady=10)
        action_button_frame.pack(fill="x", side="bottom")
        ttk.Button(action_button_frame, text="Corrigir Detalhes da OS", command=self.go_back_to_details, style="Nav.TButton").pack(side="left", padx=5)
        ttk.Button(action_button_frame, text="Incluir Materiais", command=self.add_materials_placeholder, style="Info.TButton").pack(side="left", padx=5)
        ttk.Button(action_button_frame, text="Enviar OS para Omie", command=self.send_os_to_omie, style="Success.TButton").pack(side="right", padx=5)

        # Valor Total da OS (Empacotado em seguida, ficará acima dos botões de ação)
        total_frame = tk.Frame(main_frame, bg="#F3F6FA")
        total_frame.pack(fill="x", pady=(5, 15))
        tk.Label(total_frame, text="Valor Total da OS:", font=("Segoe UI", 12, "bold"), bg="#F3F6FA", fg="#004E8C").pack(side="left", padx=5)
        self.total_os_value_label = tk.Label(total_frame, font=("Segoe UI", 12, "bold"), bg="#F3F6FA", fg="#004E8C")
        self.total_os_value_label.pack(side="right", padx=5)

        # Frame para Serviços (Empacotado por último, para preencher o espaço restante no meio)
        services_frame = tk.LabelFrame(main_frame, text="Serviços Prestados", font=label_font, bg="#F3F6FA", fg="#004E8C", bd=2, padx=10, pady=10)
        services_frame.pack(fill="both", expand=True, pady=(0, 15))
        self.services_tree = ttk.Treeview(services_frame, columns=("descricao", "quantidade", "valor_unitario", "valor_total"), show="headings", height=5)
        self.services_tree.heading("descricao", text="Descrição")
        self.services_tree.heading("quantidade", text="Qtd.")
        self.services_tree.heading("valor_unitario", text="Vlr. Unit.")
        self.services_tree.heading("valor_total", text="Vlr. Total")
        self.services_tree.column("descricao", width=250, anchor="w")
        self.services_tree.column("quantidade", width=60, anchor="center")
        self.services_tree.column("valor_unitario", width=100, anchor="e")
        self.services_tree.column("valor_total", width=100, anchor="e")
        self.services_tree.pack(fill="both", expand=True)

        # Frame para Produtos/Materiais (NOVO)
        products_frame = tk.LabelFrame(main_frame, text="Materiais/Produtos Utilizados", font=label_font, bg="#F3F6FA", fg="#004E8C", bd=2, padx=10, pady=10)
        products_frame.pack(fill="both", expand=True, pady=(0, 15))

        self.products_tree = ttk.Treeview(products_frame, columns=("codigo", "descricao", "quantidade"), show="headings", height=5)
        self.products_tree.heading("codigo", text="Código")
        self.products_tree.heading("descricao", text="Descrição")
        self.products_tree.heading("quantidade", text="Qtd.")
        self.products_tree.column("codigo", width=80, anchor="center")
        self.products_tree.column("descricao", width=400, anchor="w")
        self.products_tree.column("quantidade", width=80, anchor="center")
        self.products_tree.pack(fill="both", expand=True)


    def display_os_data(self):
        try:
            client = self.os_data['selected_client']
            self.client_code_label.config(text=client.get('codigo_cliente', 'N/A'))
            self.client_fantasia_label.config(text=client.get('nome_fantasia', 'N/A'))
            self.client_razao_label.config(text=client.get('razao_social', 'N/A'))
            self.data_prev_label.config(text=self.os_data['data_prev_faturamento'].strftime("%d/%m/%Y"))
            self.parcelas_label.config(text=str(self.os_data['quantidade_parcelas']))
            self.departamento_label.config(text=self.os_data['departamento']['descricao'])
            self.categoria_label.config(text=self.os_data['categoria']['descricao'])
            self.reter_iss_label.config(text=self.os_data['reter_iss'])

            # Limpa e preenche a treeview de serviços
            for item in self.services_tree.get_children():
                self.services_tree.delete(item)
            for service in self.os_data['servicos']:
                valor_total_servico = service['nQtde'] * service['nValUnit']
                self.services_tree.insert("", "end", values=(
                    service['cDescServ'],
                    service['nQtde'],
                    f"R$ {service['nValUnit']:.2f}".replace('.', ','),
                    f"R$ {valor_total_servico:.2f}".replace('.', ',')
                ))
            
            self.total_os_value_label.config(text=f"R$ {self.os_data['valor_total_os']:.2f}".replace('.', ','))

            # Limpa e preenche a treeview de produtos/materiais
            for item in self.products_tree.get_children():
                self.products_tree.delete(item)

            if self.os_data.get('produtos'):
                # Carrega cache de produtos se necessário
                produtos_cadastrados = carregar_lista_produtos_cache()

                for produto in self.os_data['produtos']:
                    codigo = produto["nCodProdutoPU"]
                    qtd = produto["nQtdePU"]

                    # Busca descrição do produto no cache
                    produto_info = next((p for p in produtos_cadastrados if int(p["codigo"]) == codigo), None)
                    descricao = produto_info["nome"] if produto_info else f"Produto código {codigo}"

                    self.products_tree.insert("", "end", values=(
                        codigo,
                        descricao,
                        qtd
                    ))


        except Exception as e:
            print(f"[ERRO] Falha ao exibir dados da OS: {e}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Erro ao Exibir Dados", f"Erro ao carregar dados da revisão:\n{e}")

    def send_os_to_omie(self):
        # Monta o payload da OS no formato igual ao código funcional de terminal
        os_payload = {
            "Cabecalho": {
                "cCodIntOS": str(uuid.uuid4()),
                "cEtapa": "10",
                # usa o mesmo formato do código funcional: DD/MM/AAAA
                "dDtPrevisao": self.os_data['data_prev_faturamento'].strftime("%d/%m/%Y"),
                "nCodCli": self.os_data['selected_client']['codigo_cliente'],
                "nQtdeParc": self.os_data['quantidade_parcelas'],
                "nValorTotal": self.os_data['valor_total_os']
            },
            "Departamentos": [
                {
                    "cCodDepto": self.os_data['departamento']['codigo'],
                    "nPerc": 100,
                    "nValor": self.os_data['valor_total_os'],
                    "nValorFixo": "N"
                }
            ],
            "Email": {
                "cEnvBoleto": "N",
                "cEnvLink": "N"
            },
            "InformacoesAdicionais": {
                "cCodCateg": self.os_data['categoria']['codigo'],
                "nCodCC": 3465583045,
                "cDadosAdicNF": "OS incluída via API",
                "cNaoGerarFinanceiro": "N" if self.os_data["gerar_financeiro"] == "Sim" else "S"
            },
            "ServicosPrestados": []
        }

        # UM ÚNICO LOOP (corrigido)
        for service in self.os_data['servicos']:
            os_payload["ServicosPrestados"].append({
                "cCodServLC116": "14.01",
                "cCodServMun": "432230202",
                "cDadosAdicItem": "Serviços prestados",
                "cDescServ": service['cDescServ'],
                "cRetemISS": self.os_data['reter_iss'],
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

        # Adiciona produtos/materiais se houver
        if self.os_data.get('produtos'):
            os_payload["produtosUtilizados"] = {
                "cAcaoProdUtilizados": "PED",
                "cCodCategRem": "1.01.03",
                "produtoUtilizado": self.os_data['produtos']
            }
            print(f"[DEBUG] {len(self.os_data['produtos'])} produtos incluídos no payload")

        print("\n[DEBUG] Payload completo sendo enviado:")
        print(json.dumps(os_payload, indent=2, ensure_ascii=False))

        resp = incluir_os(os_payload)

        if resp:
            if "faultstring" not in resp:
                os_number = resp.get('nCodOS', 'N/A')
                messagebox.showinfo(
                    "Sucesso no Envio",
                    f"OS incluída com sucesso na Omie! Número da OS: {os_number}",
                    parent=self
                )
                self.on_close()
            else:
                erro = resp.get("faultstring", "Erro desconhecido da API Omie.")
                messagebox.showerror("Falha no Envio", f"A Omie retornou um erro: {erro}", parent=self)


    def go_back_to_details(self):
        self.destroy()
        # Reabre a janela de detalhes da OS, passando os dados para preenchimento
        OSDetailsWindow(self.master, self.os_data['selected_client'], os_data=self.os_data)

    def add_materials_placeholder(self):
        MaterialSelectionWindow(self, self.os_data, self.on_materials_added)

    def on_materials_added(self, produtos, erros):
        self.os_data['produtos'] = produtos

        observacoes_extra = ""
        if erros:
            observacoes_extra = "\n\nProdutos não encontrados no cadastro: " + ", ".join(erros)
            messagebox.showwarning(
                "Produtos Não Encontrados",
                f"{len(erros)} produtos não foram encontrados no cadastro Omie e serão listados nas observações da OS:\n\n" + "\n".join(erros[:10]) + ("..." if len(erros) > 10 else ""),
                parent=self
            )

        if self.os_data['produtos']:
            messagebox.showinfo(
                "Materiais Adicionados",
                f"{len(self.os_data['produtos'])} materiais foram adicionados à OS com sucesso!" + observacoes_extra,
                parent=self
            )
            self.display_os_data()


    def on_close(self):
        self.master.deiconify() # Mostra a janela principal novamente
        self.destroy()

# ====================================================================================
# CLASSE: RecebimentoNFeWindow (Janela de Recebimento de Notas Fiscais)
# ====================================================================================
class RecebimentoNFeWindow(tk.Toplevel):
    def __init__(self, master, omie_estoque_api_client):
        super().__init__(master)
        self.master = master
        self.omie_api = omie_estoque_api_client
        self.title("Recebimento de Notas Fiscais")
        self.geometry("1000x700")
        self.configure(bg="#F3F6FA")
        self.resizable(False, False)
        self.grab_set()
        self.focus_set()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.recebimentos_cache = []
        self.create_styles()
        self.create_widgets()
        self.load_recebimentos()

    def create_styles(self):
        self.style = ttk.Style()
        self.style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"), background="#007ACC", foreground="white", relief="flat", padding=6)
        self.style.map("Primary.TButton", background=[("active", "#005E9E")])
        self.style.configure("Nav.TButton", font=("Segoe UI", 10), background="#6c757d", foreground="white", relief="flat", padding=6)
        self.style.map("Nav.TButton", background=[("active", "#5a6268")])

    def create_widgets(self):
        main_frame = tk.Frame(self, bg="#F3F6FA", padx=20, pady=20)
        main_frame.pack(expand=True, fill="both")

        title_label = tk.Label(main_frame, text="Recebimento de Notas Fiscais (Etapa 40)", 
                               font=("Segoe UI", 18, "bold"), bg="#F3F6FA", fg="#004E8C")
        title_label.pack(pady=(0, 20))

        # Treeview para listar recebimentos
        self.recebimentos_tree = ttk.Treeview(main_frame, 
                                              columns=("id_receb", "numero_nfe", "razao_social", "total_nfe", "emissao"), 
                                              show="headings", height=15)
        self.recebimentos_tree.heading("id_receb", text="ID Receb")
        self.recebimentos_tree.heading("numero_nfe", text="Nº NFe")
        self.recebimentos_tree.heading("razao_social", text="Razão Social")
        self.recebimentos_tree.heading("total_nfe", text="Total NFe")
        self.recebimentos_tree.heading("emissao", text="Emissão")

        self.recebimentos_tree.column("id_receb", width=80, anchor="center")
        self.recebimentos_tree.column("numero_nfe", width=100, anchor="center")
        self.recebimentos_tree.column("razao_social", width=300, anchor="w")
        self.recebimentos_tree.column("total_nfe", width=120, anchor="e")
        self.recebimentos_tree.column("emissao", width=100, anchor="center")

        self.recebimentos_tree.pack(fill="both", expand=True, pady=(0, 15))
        self.recebimentos_tree.bind("<<TreeviewSelect>>", self.on_recebimento_select)

        # Botões
        button_frame = tk.Frame(main_frame, bg="#F3F6FA")
        button_frame.pack(fill="x", pady=(10, 0))

        ttk.Button(button_frame, text="Atualizar Lista", command=self.load_recebimentos, style="Primary.TButton").pack(side="left", padx=5)
        self.view_button = ttk.Button(button_frame, text="Visualizar Detalhes", command=self.view_recebimento_details, state="disabled", style="Primary.TButton")
        self.view_button.pack(side="left", padx=5)
        ttk.Button(button_frame, text="Fechar", command=self.on_close, style="Nav.TButton").pack(side="right", padx=5)

        self.status_label = tk.Label(main_frame, text="Carregando recebimentos...", font=("Segoe UI", 9, "italic"), bg="#F3F6FA", fg="#666")
        self.status_label.pack(pady=(10, 0))

    def load_recebimentos(self):
        self.recebimentos_tree.delete(*self.recebimentos_tree.get_children())
        self.recebimentos_cache.clear()
        self.status_label.config(text="Buscando recebimentos na Etapa 40...", fg="#007ACC")
        self.update_idletasks()

        page = 1
        while True:
            res = self.omie_api.listar_recebimentos(page)
            if not res or not res.get("recebimentos"):
                break
            self.recebimentos_cache.extend(res["recebimentos"])
            if page >= res.get("nTotalPaginas", 1):
                break
            page += 1

        if self.recebimentos_cache:
            for rec in self.recebimentos_cache:
                cabec = rec.get("cabec", {})
                totais = rec.get("totais", {})
                self.recebimentos_tree.insert("", "end", values=(
                    cabec.get('nIdReceb', 'N/A'),
                    cabec.get('cNumeroNFe', 'N/A'),
                    cabec.get('cRazaoSocial', 'N/A'),
                    f"R$ {totais.get('vTotalNFe', 0.0):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                    cabec.get('dEmissaoNFe', 'N/A')
                ))
            self.status_label.config(text=f"{len(self.recebimentos_cache)} recebimentos encontrados.", fg="#004E8C")
        else:
            self.status_label.config(text="Nenhum recebimento encontrado na Etapa 40.", fg="red")

    def on_recebimento_select(self, event=None):
        selected_item = self.recebimentos_tree.focus()
        if selected_item:
            self.view_button.config(state="normal")
        else:
            self.view_button.config(state="disabled")

    def view_recebimento_details(self):
        selected_item = self.recebimentos_tree.focus()
        if not selected_item:
            return

        values = self.recebimentos_tree.item(selected_item, "values")
        nIdReceb = int(values[0])

        # Consulta detalhes do recebimento na Omie
        detalhes = self.omie_api.consultar_recebimento(nIdReceb)
        if not detalhes:
            messagebox.showerror("Erro", f"Não foi possível consultar o recebimento ID {nIdReceb}.", parent=self)
            return

        # Abre a janela de detalhes
        RecebimentoDetalhesWindow(self, self.omie_api, detalhes)

    def on_close(self):
        self.master.deiconify()
        self.destroy()
    
    # ====================================================================================
# CLASSE: RecebimentoDetalhesWindow (itens, ações e confirmação)
# ====================================================================================
class RecebimentoDetalhesWindow(tk.Toplevel):
    def __init__(self, master, omie_api_client, receipt_details):
        super().__init__(master)
        self.master = master            # janela RecebimentoNFeWindow
        self.omie_api = omie_api_client # OmieEstoqueAPI (mas também com métodos de recebimento)
        self.receipt_details = receipt_details

        self.title(f"Detalhes do Recebimento ID {self.receipt_details.get('cabec', {}).get('nIdReceb', 'N/A')}")
        self.geometry("1300x700")
        self.configure(bg="#F3F6FA")
        self.resizable(False, False)
        self.grab_set()
        self.focus_set()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.create_styles()
        self.create_widgets()
        self.display_receipt()

    def create_styles(self):
        self.style = ttk.Style()
        self.style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"),
                             background="#007ACC", foreground="white", relief="flat", padding=6)
        self.style.map("Primary.TButton", background=[("active", "#005E9E")])
        self.style.configure("Nav.TButton", font=("Segoe UI", 10),
                             background="#6c757d", foreground="white", relief="flat", padding=6)
        self.style.map("Nav.TButton", background=[("active", "#5a6268")])
        self.style.configure("Success.TButton", font=("Segoe UI", 10, "bold"),
                             background="#28a745", foreground="white", relief="flat", padding=6)
        self.style.map("Success.TButton", background=[("active", "#218838")])

    def create_widgets(self):
        main_frame = tk.Frame(self, bg="#F3F6FA", padx=20, pady=20)
        main_frame.pack(expand=True, fill="both")

        title_label = tk.Label(
            main_frame,
            text="Detalhes do Recebimento",
            font=("Segoe UI", 18, "bold"),
            bg="#F3F6FA",
            fg="#004E8C"
        )
        title_label.pack(pady=(0, 15))

        label_font = ("Segoe UI",10, "bold")
        value_font = ("Segoe UI", 10)

        # --- Cabeçalho ---
        cabec = self.receipt_details.get("cabec", {})
        totais = self.receipt_details.get("totais", {})

        header_frame = tk.LabelFrame(main_frame, text="Cabeçalho da NFe",
                                     font=label_font, bg="#F3F6FA", fg="#004E8C",
                                     bd=2, padx=10, pady=10)
        header_frame.pack(fill="x", pady=(0, 15))

        def add_row(row, label, value):
            tk.Label(header_frame, text=label, font=label_font,
                     bg="#F3F6FA", fg="#333").grid(row=row, column=0, sticky="w", padx=5, pady=2)
            tk.Label(header_frame, text=value, font=value_font,
                     bg="#F3F6FA", fg="#333").grid(row=row, column=1, sticky="w", padx=5, pady=2)

        add_row(0, "ID Recebimento:", cabec.get("nIdReceb", "N/A"))
        add_row(1, "Número NFe:", cabec.get("cNumeroNFe", "N/A"))
        add_row(2, "Razão Social:", cabec.get("cRazaoSocial", "N/A"))
        add_row(3, "Data Emissão:", cabec.get("dEmissaoNFe", "N/A"))
        add_row(4, "Valor Total NFe:",
                f"R$ {totais.get('vTotalNFe', 0.0):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

        header_frame.grid_columnconfigure(1, weight=1)

        # --- Opção de gerar conta a pagar ---
        financeiro_frame = tk.Frame(main_frame, bg="#F3F6FA", pady=10)
        financeiro_frame.pack(fill="x", pady=(0, 10))

        tk.Label(
            financeiro_frame,
            text="Deseja gerar conta a pagar?",
            font=label_font,
            bg="#F3F6FA",
            fg="#333"
        ).pack(side="left", padx=5)

        self.gerar_financeiro_var = tk.StringVar(value="Não")
        ttk.Combobox(
            financeiro_frame,
            textvariable=self.gerar_financeiro_var,
            values=["Sim", "Não"],
            state="readonly",
            font=("Segoe UI", 10),
            width=10
        ).pack(side="left", padx=5)


        # --- Treeview de Itens ---
        itens_frame = tk.LabelFrame(main_frame, text="Itens da NFe",
                                    font=label_font, bg="#F3F6FA", fg="#004E8C",
                                    bd=2, padx=10, pady=10)
        itens_frame.pack(fill="both", expand=True, pady=(0, 15))

        self.itens_tree = ttk.Treeview(
            itens_frame,
            columns=("seq", "cod_prod", "descricao", "qtd", "preco_unit", "valor_total", "situacao", "cmc", "preco_venda"),
            show="headings",
            height=10
        )
        self.itens_tree.heading("seq", text="Seq")
        self.itens_tree.heading("cod_prod", text="Cód. Produto")
        self.itens_tree.heading("descricao", text="Descrição Produto")
        self.itens_tree.heading("qtd", text="Qtde")
        self.itens_tree.heading("preco_unit", text="Preço Unit.")
        self.itens_tree.heading("valor_total", text="Valor Total")
        self.itens_tree.heading("situacao", text="Situação")
        self.itens_tree.heading("cmc", text="CMC")
        self.itens_tree.heading("preco_venda", text="Preço Venda")

        self.itens_tree.column("seq", width=50, anchor="center")
        self.itens_tree.column("cod_prod", width=100, anchor="center")
        self.itens_tree.column("descricao", width=250, anchor="w")
        self.itens_tree.column("qtd", width=60, anchor="e")
        self.itens_tree.column("preco_unit", width=90, anchor="e")
        self.itens_tree.column("valor_total", width=100, anchor="e")
        self.itens_tree.column("situacao", width=120, anchor="center")
        self.itens_tree.column("cmc", width=90, anchor="e")
        self.itens_tree.column("preco_venda", width=100, anchor="e")

        self.itens_tree.pack(fill="both", expand=True)

        # --- Botões inferiores ---
        buttons_frame = tk.Frame(main_frame, bg="#F3F6FA", pady=10)
        buttons_frame.pack(fill="x", side="bottom")

        ttk.Button(buttons_frame, text="Alterar Item Selecionado",
                   command=self.alterar_item_selecionado,
                   style="Primary.TButton").pack(side="left", padx=5)

        ttk.Button(buttons_frame, text="Confirmar Recebimento",
                   command=self.confirmar_recebimento,
                   style="Success.TButton").pack(side="right", padx=5)

        ttk.Button(buttons_frame, text="Voltar", command=self.on_close,
                   style="Nav.TButton").pack(side="right", padx=5)

    def display_receipt(self):
        # Preenche a tree com os itens
        for item in self.itens_tree.get_children():
            self.itens_tree.delete(item)

        itens = self.receipt_details.get("itensRecebimento", [])
        for item in itens:
            cab = item.get("itensCabec", {})
            atual_preco = item.get("itensAtualPreco", {})
            itens_custo_estoque = item.get("itensCustoEstoque", {})

            n_seq = cab.get("nSequencia", "N/A")
            cod_prod = cab.get("cCodigoProduto", "N/A")
            desc_prod = cab.get("cDescricaoProduto", "N/A")
            qtd = cab.get("nQtdeNFe", 0.0)
            preco_unit = cab.get("nPrecoUnit", 0.0)
            total_item = cab.get("vTotalItem", 0.0)

            # Valor do ICMS ST para o custo
            n_valor_icms_st_custo_existente = itens_custo_estoque.get("nValorICMSSTCusto", 0.0)

            # Situação
            situacao = "Pendente"
            if cab.get("cIgnorarItem") == "S":
                situacao = "Ignorado"
            elif cab.get("cAdicionarNovo") == "S":
                situacao = "Adicionar Novo"
            elif cab.get("cAssociarExistente") == "S":
                situacao = "Associar Existente"

            # Cálculo do CMC (Custo Médio de Compra)
            # CMC = (vTotalItem + nValorICMSSTCusto) / nQtdeNFe
            cmc = (total_item + n_valor_icms_st_custo_existente) / qtd if qtd else 0.0

            # Preço de venda = CMC * (1 + nPercAtuPre / 100)
            perc_atu_pre = atual_preco.get("nPercAtuPre", 0.0)
            preco_venda = cmc * (1 + perc_atu_pre / 100)

            self.itens_tree.insert(
                "",
                "end",
                values=(
                    n_seq,
                    cod_prod,
                    desc_prod[:40],
                    f"{qtd:.2f}".replace(".", ","),
                    f"R$ {preco_unit:.2f}".replace(".", ","),
                    f"R$ {total_item:.2f}".replace(".", ","),
                    situacao,
                    f"R$ {cmc:.2f}".replace(".", ","),
                    f"R$ {preco_venda:.2f}".replace(".", ",")
                )
            )


    # --------- Ações ---------

    def get_selected_item_seq(self):
        sel = self.itens_tree.focus()
        if not sel:
            messagebox.showwarning("Seleção", "Selecione um item na lista.", parent=self)
            return None
        values = self.itens_tree.item(sel, "values")
        try:
            return int(values[0])
        except (ValueError, TypeError):
            return None
        
    def buscar_produto_existente(self, descricao_item_nfe: str) -> int | None:
        """
        Abre uma janela para buscar e selecionar um produto existente no estoque Omie.
        Retorna o código do produto (int) ou None se cancelar.
        """
        # Carrega todos os itens de estoque
        produtos_brutos = self.omie_api.listar_todos_estoques()
        if not produtos_brutos:
            messagebox.showerror(
                "Estoque",
                "Nenhum produto retornado pela API de estoque.\n"
                "Verifique credenciais, data de posição ou código de local de estoque.",
                parent=self
            )
            return None

        lista_completa = extrair_nomes_e_codigos_produtos(produtos_brutos)
        if not lista_completa:
            messagebox.showerror(
                "Estoque",
                "Não foi possível extrair nomes e códigos dos produtos de estoque.",
                parent=self
            )
            return None

        # Janela de busca
        top = tk.Toplevel(self)
        top.title("Associar Produto Existente")
        top.transient(self)
        top.grab_set()
        top.configure(bg="#F3F6FA")
        top.geometry("800x500")

        tk.Label(
            top,
            text="Item da NFe sendo associado:",
            font=("Segoe UI", 9, "bold"),
            bg="#F3F6FA",
            fg="#333"
        ).pack(anchor="w", padx=10, pady=(10, 0))

        tk.Label(
            top,
            text=descricao_item_nfe,
            font=("Segoe UI", 9, "italic"),
            bg="#F3F6FA",
            fg="#004E8C"
        ).pack(anchor="w", padx=10, pady=(0, 10))

        search_frame = tk.Frame(top, bg="#F3F6FA")
        search_frame.pack(fill="x", padx=10, pady=(0, 10))

        tk.Label(
            search_frame,
            text="Buscar produto por descrição:",
            font=("Segoe UI", 9, "bold"),
            bg="#F3F6FA"
        ).pack(side="left")

        search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=search_var, width=40)
        search_entry.pack(side="left", padx=5)

        ttk.Button(
            search_frame,
            text="Buscar",
            command=lambda: executar_busca(),
            style="Primary.TButton"
        ).pack(side="left", padx=5)

        # Treeview de resultados
        results_frame = tk.Frame(top, bg="#F3F6FA")
        results_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        cols = ("codigo", "nome")
        results_tree = ttk.Treeview(results_frame, columns=cols, show="headings", height=12)
        results_tree.heading("codigo", text="Código")
        results_tree.heading("nome", text="Descrição Produto")
        results_tree.column("codigo", width=100, anchor="center")
        results_tree.column("nome", width=500, anchor="w")
        results_tree.pack(fill="both", expand=True, side="left")

        scrollbar = ttk.Scrollbar(results_frame, orient="vertical", command=results_tree.yview)
        results_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        selected_code: list[int | None] = [None]  # truque para fechamento sobre escopo

        def executar_busca():
            termo = search_var.get().strip()
            for item in results_tree.get_children():
                results_tree.delete(item)
            if not termo:
                return
            encontrados = pesquisar_produtos_por_nome(lista_completa, termo)
            for p in encontrados[:100]:
                results_tree.insert("", "end", values=(p["codigo"], p["nome"]))

        def confirmar():
            sel = results_tree.focus()
            if not sel:
                messagebox.showwarning("Seleção", "Selecione um produto na lista.", parent=top)
                return
            values = results_tree.item(sel, "values")
            try:
                selected_code[0] = int(values[0])
            except (ValueError, TypeError):
                messagebox.showerror("Erro", "Código de produto inválido.", parent=top)
                return
            top.destroy()

        def cancelar():
            selected_code[0] = None
            top.destroy()

        btn_frame = tk.Frame(top, bg="#F3F6FA")
        btn_frame.pack(fill="x", padx=10, pady=(0, 10))

        ttk.Button(btn_frame, text="Confirmar", command=confirmar, style="Success.TButton").pack(side="right", padx=5)
        ttk.Button(btn_frame, text="Cancelar", command=cancelar, style="Nav.TButton").pack(side="right", padx=5)

        search_entry.bind("<Return>", lambda e: executar_busca())
        search_entry.focus_set()

        top.wait_window()

        return selected_code[0]


    def alterar_item_selecionado(self):
        nSeq = self.get_selected_item_seq()
        if nSeq is None:
            return

        # Encontrar o dicionário do item selecionado no JSON
        itens = self.receipt_details.get("itensRecebimento", [])
        selected_item = next(
            (it for it in itens if it.get("itensCabec", {}).get("nSequencia") == nSeq),
            None
        )
        if not selected_item:
            messagebox.showerror("Erro", f"Item de sequência {nSeq} não encontrado no retorno da API.", parent=self)
            return

        cab = selected_item.get("itensCabec", {})
        desc_item_nfe = cab.get("cDescricaoProduto", "Item da NFe")

        # Menu de opções
        op = tk.simpledialog.askinteger(
            "Alterar Item",
            "Escolha o que deseja fazer com o item:\n\n"
            "1 - NOVO (cadastrar como novo produto)\n"
            "2 - ASSOCIAR-PRODUTO (associar a um produto de estoque)\n"
            "3 - IGNORAR (não importar o item da NFe)\n"
            "4 - EDITAR (ICMS ST / custo / preço de venda)\n\n"
            "Digite o número da opção:",
            parent=self,
            minvalue=1,
            maxvalue=4,
        )
        if not op:
            return

        nIdReceb = self.receipt_details.get("cabec", {}).get("nIdReceb")
        if not nIdReceb:
            messagebox.showerror("Erro", "ID do recebimento não encontrado.", parent=self)
            return

        if op == 1:
            # NOVO
            acao = "NOVO"
            payload = {
                "ide": {"nIdReceb": nIdReceb},
                "itensRecebimentoEditar": {
                    "itensIde": {
                        "nSequencia": nSeq,
                        "cAcao": acao
                    }
                }
            }
            self._enviar_alteracao_item(payload, nIdReceb)

        elif op == 2:
            # ASSOCIAR-PRODUTO com busca real
            cod_produto = self.buscar_produto_existente(desc_item_nfe)
            if cod_produto is None:
                return

            payload = {
                "ide": {"nIdReceb": nIdReceb},
                "itensRecebimentoEditar": {
                    "itensIde": {
                        "nSequencia": nSeq,
                        "cAcao": "ASSOCIAR-PRODUTO",
                        "nIdProdutoExistente": cod_produto
                    }
                }
            }
            self._enviar_alteracao_item(payload, nIdReceb)

        elif op == 3:
            # IGNORAR
            payload = {
                "ide": {"nIdReceb": nIdReceb},
                "itensRecebimentoEditar": {
                    "itensIde": {
                        "nSequencia": nSeq,
                        "cAcao": "IGNORAR"
                    }
                }
            }
            self._enviar_alteracao_item(payload, nIdReceb)

        elif op == 4:
            # EDITAR: abre diálogo para ICMS ST e nPercAtuPre
            self._editar_item_valores(nIdReceb, nSeq, selected_item)

    def _enviar_alteracao_item(self, payload: dict, nIdReceb: int):
        resp = self.omie_api.alterar_recebimento(payload)
        if resp:
            novos_detalhes = self.omie_api.consultar_recebimento(nIdReceb)
            if novos_detalhes:
                self.receipt_details = novos_detalhes
                self.display_receipt()

            messagebox.showinfo(
                "Sucesso",
                "Alteração enviada para a Omie com sucesso.",
                parent=self
            )
        else:
            messagebox.showerror(
                "Erro",
                "Falha ao alterar item na Omie.",
                parent=self
            )

    def _editar_item_valores(self, nIdReceb: int, nSeq: int, item_data: dict):
        """
        Edição de ICMS ST/custo e preço de venda para UM item.
        """
        cab = item_data.get("itensCabec", {})
        desc_item_nfe = cab.get("cDescricaoProduto", "Item da NFe")

        # Diálogo simples para escolher o que editar
        op = tk.simpledialog.askinteger(
            "Editar Item",
            f"Item {nSeq} - {desc_item_nfe}\n\n"
            "1 - Atualizar preço de venda (nPercAtuPre)\n"
            "2 - Incluir ICMS ST no custo\n"
            "3 - Ambos\n\n"
            "Digite a opção:",
            parent=self,
            minvalue=1,
            maxvalue=3,
        )
        if not op:
            return

        nPercAtuPre = None
        nValorICMSSTCusto = None

        if op in (1, 3):
            nPercAtuPre = tk.simpledialog.askfloat(
                "Preço de Venda",
                "Digite o percentual de atualização do preço de venda\n"
                "Exemplo: 100 para 100% de markup, 20 para 20%:\n",
                parent=self,
                minvalue=0.0,
            )
            if nPercAtuPre is None:
                return

        if op in (2, 3):
            nValorICMSSTCusto = tk.simpledialog.askfloat(
                "ICMS ST no Custo",
                "Digite o valor do ICMS ST a ser incluído no custo deste item:\n",
                parent=self,
                minvalue=0.0,
            )
            if nValorICMSSTCusto is None:
                return

        # Monta payload completo para EDITAR
        info_adic_existente = self.receipt_details.get("infoAdicionais", {})
        totais = self.receipt_details.get("totais", {})
        vTotalNFe = totais.get("vTotalNFe", 0.0)

        info_adicionais_payload = {
            "cCategCompra": "2.01.01",  # pode parametrizar se quiser
            "dRegistro": info_adic_existente.get("dRegistro", datetime.now().strftime("%Y-%m-%d")),
        }
        if info_adic_existente.get("nIdConta") is not None:
            info_adicionais_payload["nIdConta"] = info_adic_existente["nIdConta"]
        if info_adic_existente.get("nIdComprador") is not None:
            info_adicionais_payload["nIdComprador"] = info_adic_existente["nIdComprador"]
        if info_adic_existente.get("nIdProjeto") is not None:
            info_adicionais_payload["nIdProjeto"] = info_adic_existente["nIdProjeto"]

        payload = {
            "ide": {"nIdReceb": nIdReceb},
            "itensRecebimentoEditar": {
                "itensIde": {
                    "nSequencia": nSeq,
                    "cAcao": "EDITAR"
                }
            },
            "infoAdicionais": info_adicionais_payload,
            "departamentos": [
                {
                    "cCodDepartamento": DEPARTAMENTOS["3"]["codigo"],
                    "vDepartamento": vTotalNFe,
                    "pDepartamento": 100.0
                }
            ]
        }

        if nPercAtuPre is not None:
            payload["itensRecebimentoEditar"]["itensAtualPreco"] = {
                "cAtualizarAtuPre": "S",
                "nPercAtuPre": nPercAtuPre,
                "cAtualizarMaiorAtuPre": "N"
            }

        if nValorICMSSTCusto is not None:
            payload["itensRecebimentoEditar"]["itensCustoEstoque"] = {
                "cICMSCusto": "S",
                "cPISCusto": "S",
                "cICMSSTCusto": "S",
                "cCOFINSCusto": "S",
                "cIPICusto": "S",
                "cFreteCusto": "S",
                "cSeguroCusto": "S",
                "cOutrosDespCusto": "S",
                "nValorICMSSTCusto": nValorICMSSTCusto,
                "nAliqCredPISCusto": 1.65,
                "nAliqCredCOFINSCusto": 7.6
            }
            
        # Adiciona o campo de não gerar financeiro
        gerar_financeiro = self.gerar_financeiro_var.get()
        cNaoGerarFinanceiro = "N" if gerar_financeiro == "Sim" else "S"

        payload["itensRecebimentoEditar"]["itensAjustes"] = {
            "cNaoGerarFinanceiro": cNaoGerarFinanceiro
        }

        print(json.dumps(payload, indent=2, ensure_ascii=False))
        self._enviar_alteracao_item(payload, nIdReceb)

    def confirmar_recebimento(self):
        nIdReceb = self.receipt_details.get("cabec", {}).get("nIdReceb")
        if not nIdReceb:
            messagebox.showerror("Erro", "ID do recebimento não encontrado.", parent=self)
            return

        resp = messagebox.askyesno(
            "Confirmar Recebimento",
            f"Tem certeza que deseja CONFIRMAR o recebimento ID {nIdReceb}?",
            parent=self
        )
        if not resp:
            return

        resposta_api = self.omie_api.concluir_recebimento(nIdReceb)
        if resposta_api:
            messagebox.showinfo(
                "Recebimento Confirmado",
                f"Recebimento ID {resposta_api.get('nIdReceb', nIdReceb)} confirmado com sucesso!",
                parent=self
            )
            self.on_close()
        else:
            messagebox.showerror(
                "Erro",
                "Falha ao confirmar recebimento na Omie.",
                parent=self
            )

    def on_close(self):
        self.destroy()


class MaterialSelectionWindow(tk.Toplevel):
    def __init__(self, master, os_data, on_materials_added_callback):
        super().__init__(master)
        self.master = master
        self.os_data = os_data
        self.on_materials_added_callback = on_materials_added_callback
        self.title("Seleção de Materiais/Produtos")
        self.geometry("700x600")
        self.configure(bg="#F3F6FA")
        self.resizable(False, False)
        self.grab_set()
        self.focus_set()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.produtos_selecionados = []
        self.erros_importacao = []
        self.produtos_cadastrados = []

        self.create_styles()
        self.create_widgets()

    def create_styles(self):
        self.style = ttk.Style()
        self.style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"), background="#007ACC", foreground="white", relief="flat", padding=6)
        self.style.map("Primary.TButton", background=[("active", "#005E9E")])
        self.style.configure("Nav.TButton", font=("Segoe UI", 10), background="#6c757d", foreground="white", relief="flat", padding=6)
        self.style.map("Nav.TButton", background=[("active", "#5a6268")])
        self.style.configure("Success.TButton", font=("Segoe UI", 10, "bold"), background="#28a745", foreground="white", relief="flat", padding=6)
        self.style.map("Success.TButton", background=[("active", "#218838")])

    def create_widgets(self):
        main_frame = tk.Frame(self, bg="#F3F6FA", padx=20, pady=20)
        main_frame.pack(expand=True, fill="both")

        title_label = tk.Label(
            main_frame,
            text="Adicionar Materiais/Produtos à OS",
            font=("Segoe UI", 18, "bold"),
            bg="#F3F6FA",
            fg="#004E8C"
        )
        title_label.pack(pady=(0, 20))

        label_font = ("Segoe UI", 10, "bold")

        tk.Label(
            main_frame,
            text="Adicionar materiais manualmente:",
            font=label_font,
            bg="#F3F6FA",
            fg="#333"
        ).pack(anchor="w", pady=(0, 10))

        button_frame = tk.Frame(main_frame, bg="#F3F6FA")
        button_frame.pack(fill="x", pady=(0, 10))

        ttk.Button(
            button_frame,
            text="➕ Adicionar Material",
            command=self.add_manually,
            style="Primary.TButton"
        ).pack(side="left", padx=5)

        ttk.Button(
            button_frame,
            text="🗑 Remover Selecionado",
            command=self.remove_selected,
            style="Nav.TButton"
        ).pack(side="left", padx=5)

        products_frame = tk.LabelFrame(main_frame, text="Produtos Adicionados", font=label_font, bg="#F3F6FA", fg="#004E8C", bd=2, padx=10, pady=10)
        products_frame.pack(fill="both", expand=True, pady=(0, 15))

        self.products_tree = ttk.Treeview(products_frame, columns=("codigo", "descricao", "quantidade"), show="headings", height=10)
        self.products_tree.heading("codigo", text="Código")
        self.products_tree.heading("descricao", text="Descrição")
        self.products_tree.heading("quantidade", text="Quantidade")
        self.products_tree.column("codigo", width=80, anchor="center")
        self.products_tree.column("descricao", width=350, anchor="w")
        self.products_tree.column("quantidade", width=100, anchor="center")
        self.products_tree.pack(fill="both", expand=True)

        self.status_label = tk.Label(main_frame, text="Nenhum produto adicionado ainda.", font=("Segoe UI", 9, "italic"), bg="#F3F6FA", fg="#666")
        self.status_label.pack(anchor="w", pady=(5, 0))

        nav_button_frame = tk.Frame(main_frame, bg="#F3F6FA", pady=10)
        nav_button_frame.pack(fill="x", side="bottom")
        ttk.Button(nav_button_frame, text="Cancelar", command=self.on_close, style="Nav.TButton").pack(side="left", padx=5)
        self.confirm_button = ttk.Button(nav_button_frame, text="Confirmar e Voltar para Revisão", command=self.confirm_materials, state="disabled", style="Success.TButton")
        self.confirm_button.pack(side="right", padx=5)

    def add_manually(self):
        # Garante cache carregado
        if not self.produtos_cadastrados:
            self.produtos_cadastrados = carregar_lista_produtos_cache()

        # Janela simples para digitar descrição e quantidade
        top = tk.Toplevel(self)
        top.title("Adicionar Material")
        top.transient(self)
        top.grab_set()
        top.configure(bg="#F3F6FA")

        tk.Label(top, text="Buscar produto por descrição:", font=("Segoe UI", 9, "bold"), bg="#F3F6FA").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        search_var = tk.StringVar()
        search_entry = ttk.Entry(top, textvariable=search_var, width=40)
        search_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        tk.Label(top, text="Quantidade:", font=("Segoe UI", 9, "bold"), bg="#F3F6FA").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        qty_var = tk.StringVar(value="1")
        qty_entry = ttk.Entry(top, textvariable=qty_var, width=10)
        qty_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        # Lista de resultados
        results_frame = tk.LabelFrame(top, text="Resultados", bg="#F3F6FA")
        results_frame.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky="nsew")

        results_tree = ttk.Treeview(results_frame, columns=("codigo", "nome"), show="headings", height=6)
        results_tree.heading("codigo", text="Código")
        results_tree.heading("nome", text="Descrição")
        results_tree.column("codigo", width=80, anchor="center")
        results_tree.column("nome", width=300, anchor="w")
        results_tree.pack(fill="both", expand=True)

        top.grid_columnconfigure(1, weight=1)
        top.grid_rowconfigure(2, weight=1)

        def executar_busca(*args):
            termo = search_var.get().strip()
            for item in results_tree.get_children():
                results_tree.delete(item)
            if not termo:
                return
            encontrados = pesquisar_produtos_por_nome(self.produtos_cadastrados, termo)
            for p in encontrados[:50]:  # limita resultados
                results_tree.insert("", "end", values=(p["codigo"], p["nome"]))

        def confirmar():
            selecionado = results_tree.focus()
            if not selecionado:
                messagebox.showwarning("Seleção", "Selecione um produto na lista.", parent=top)
                return
            values = results_tree.item(selecionado, "values")
            cod = int(values[0])
            desc = values[1]

            try:
                qtd = float(qty_var.get().replace(",", "."))
                if qtd <= 0:
                    raise ValueError()
            except ValueError:
                messagebox.showerror("Quantidade inválida", "Informe uma quantidade numérica maior que zero.", parent=top)
                return

            # Estrutura conforme esperado pela API Omie
            self.produtos_selecionados.append({
                "nIdItemPU": 0,
                "cAcaoItemPU": "I",
                "nCodProdutoPU": cod,
                "nQtdePU": qtd,
                "codigo_local_estoque": 0
            })

            self.update_products_tree()
            self.status_label.config(text=f"{len(self.produtos_selecionados)} produtos adicionados.", fg="#004E8C")
            self.confirm_button.config(state="normal")
            top.destroy()

        search_entry.bind("<Return>", executar_busca)

        btn_frame = tk.Frame(top, bg="#F3F6FA")
        btn_frame.grid(row=3, column=0, columnspan=2, pady=10, sticky="e")
        ttk.Button(btn_frame, text="Buscar", command=executar_busca, style="Primary.TButton").pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Adicionar", command=confirmar, style="Success.TButton").pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Cancelar", command=top.destroy, style="Nav.TButton").pack(side="left", padx=5)

        search_entry.focus_set()

    def remove_selected(self):
        selected = self.products_tree.focus()
        if not selected:
            messagebox.showwarning("Remover", "Selecione um material na lista para remover.", parent=self)
            return

        values = self.products_tree.item(selected, "values")
        codigo = int(values[0])
        qtd = float(str(values[2]).replace(",", "."))

        # remove da lista interna (primeira ocorrência)
        for i, prod in enumerate(self.produtos_selecionados):
            if prod["nCodProdutoPU"] == codigo and float(prod["nQtdePU"]) == qtd:
                del self.produtos_selecionados[i]
                break

        self.update_products_tree()

        if not self.produtos_selecionados:
            self.confirm_button.config(state="disabled")
            self.status_label.config(text="Nenhum produto adicionado ainda.", fg="#666")
        else:
            self.status_label.config(text=f"{len(self.produtos_selecionados)} produtos adicionados.", fg="#004E8C")


    def update_products_tree(self):
        for item in self.products_tree.get_children():
            self.products_tree.delete(item)

        if not self.produtos_cadastrados:
            self.produtos_cadastrados = carregar_lista_produtos_cache()

        for produto in self.produtos_selecionados:
            codigo = produto["nCodProdutoPU"]
            qtd = produto["nQtdePU"]
            produto_info = next((p for p in self.produtos_cadastrados if int(p["codigo"]) == codigo), None)
            descricao = produto_info["nome"] if produto_info else f"Código {codigo}"
            self.products_tree.insert("", "end", values=(codigo, descricao, qtd))

    def confirm_materials(self):
        if self.produtos_selecionados:
            self.destroy()
            self.on_materials_added_callback(self.produtos_selecionados, self.erros_importacao)
        else:
            messagebox.showwarning("Nenhum Material", "Nenhum material foi adicionado.", parent=self)

    def on_close(self):
        self.destroy()

# ====================================================================================
# CLASSE PRINCIPAL: MainApp
# ====================================================================================
class MainApp(tk.Frame): # Alterado para herdar de tk.Frame para facilitar o gerenciamento de estilos
    def __init__(self, root):
        super().__init__(root)
        self.root = root
        self.root.title("Sistema Interno - Portal Principal")
        self.root.geometry("820x600")
        self.root.configure(bg="#F3F6FA")
        self.root.resizable(False, False)
        self.omie_estoque_api = OmieEstoqueAPI(OMIE_APP_KEY, OMIE_APP_SECRET, OMIE_ESTOQUE_BASE_URL)
        self.pack(fill="both", expand=True) # Empacota o frame principal da MainApp
        self.create_styles() # Cria os estilos globais para a aplicação

        if getattr(sys, 'frozen', False):
            # Rodando como executável
            base_path = sys._MEIPASS
        else:
            # Rodando como script
            base_path = os.path.dirname(__file__)

        logo_path = os.path.join(base_path, "logo_empresa.png")

        # ====== TOPO (LOGO + TÍTULO) ======
        header_frame = tk.Frame(self, bg="#F3F6FA")
        header_frame.pack(pady=25)

        # Logo da empresa
        if os.path.exists(logo_path):
            imagem_logo = Image.open(logo_path)
            imagem_logo = imagem_logo.resize((110, 110), Image.LANCZOS)
            self.logo = ImageTk.PhotoImage(imagem_logo)
            logo_label = tk.Label(header_frame, image=self.logo, bg="#F3F6FA")
            logo_label.pack(side="left", padx=15)
        else:
            logo_label = tk.Label(header_frame, text="(Logo não encontrada)",
                                  bg="#F3F6FA", fg="red", font=("Segoe UI", 10, "italic"))
            logo_label.pack(side="left", padx=15)

        # Título
        title_label = tk.Label(
            header_frame,
            text="Sistema Interno - Portal Integrado",
            font=("Segoe UI", 20, "bold"),
            bg="#F3F6FA",
            fg="#004E8C"
        )
        title_label.pack(side="left", padx=10)

        # Subtítulo
        subtitle_label = tk.Label(
            self,
            text="Gerenciamento centralizado: Ordens de Serviço, Estoque e Notas Fiscais",
            bg="#F3F6FA",
            fg="#666",
            font=("Segoe UI", 10)
        )
        subtitle_label.pack()

        # ====== MENU PRINCIPAL ======
        menu_frame = tk.LabelFrame(
            self,
            text="Menu Principal",
            font=("Segoe UI", 12, "bold"),
            bg="#F3F6FA",
            fg="#004E8C",
            bd=2
        )
        menu_frame.pack(pady=30, padx=50, fill="x")

        button_style = {
            "font": ("Segoe UI", 12),
            "bg": "#007ACC",
            "fg": "white",
            "activebackground": "#005E9E",
            "activeforeground": "white",
            "width": 40,
            "height": 2,
            "bd": 0,
            "relief": "flat",
            "cursor": "hand2"
        }

        tk.Button(menu_frame, text="📑 Cadastrar OS", command=self.abrir_cadastro_os, **button_style).pack(pady=5)
        tk.Button(menu_frame, text="📦 Posição de Estoque", command=self.abrir_posicao_estoque, **button_style).pack(pady=5)
        tk.Button(menu_frame, text="🧾 Receber Nota Fiscal", command=self.abrir_receber_nf, **button_style).pack(pady=5)
        tk.Button(menu_frame, text="❌ Fechar Aplicativo", command=self.root.quit, **button_style).pack(pady=12)

        # Rodapé
        rodape = tk.Label(
            self,
            text="© 2025 - Sistema Interno Integrado da Empresa | by Peterson B'",
            bg="#F3F6FA",
            fg="#666",
            font=("Segoe UI", 10)
        )
        rodape.pack(side="bottom", pady=6)

    def create_styles(self):
        # Estilos globais para ttk.Button, podem ser sobrescritos por estilos específicos
        style = ttk.Style(self.root)
        style.theme_use('clam') # Um tema moderno para ttk

        style.configure("TButton",
                        font=("Segoe UI", 10),
                        background="#007ACC",
                        foreground="white",
                        relief="flat",
                        padding=6)
        style.map("TButton",
                  background=[("active", "#005E9E")])

        style.configure("Primary.TButton",
                        font=("Segoe UI", 10, "bold"),
                        background="#007ACC",
                        foreground="white",
                        relief="flat",
                        padding=6)
        style.map("Primary.TButton",
                  background=[("active", "#005E9E")])

        style.configure("Nav.TButton",
                        font=("Segoe UI", 10),
                        background="#6c757d",
                        foreground="white",
                        relief="flat",
                        padding=6)
        style.map("Nav.TButton",
                  background=[("active", "#5a6268")])

        style.configure("Success.TButton",
                        font=("Segoe UI", 10, "bold"),
                        background="#28a745", # Verde
                        foreground="white",
                        relief="flat",
                        padding=6)
        style.map("Success.TButton",
                  background=[("active", "#218838")])

        style.configure("Info.TButton",
                        font=("Segoe UI", 10, "bold"),
                        background="#17a2b8", # Azul claro
                        foreground="white",
                        relief="flat",
                        padding=6)
        style.map("Info.TButton",
                  background=[("active", "#138496")])

    def abrir_cadastro_os(self):
        # Esconde a janela principal enquanto as janelas modais estão abertas
        self.root.withdraw()
        ClientSelectionWindow(self.root, self.on_client_selected)

    def on_client_selected(self, client_data):
        # Callback chamado quando um cliente é selecionado na primeira janela
        # Abre a segunda janela (detalhes e serviços)
        OSDetailsWindow(self.root, client_data)

    def abrir_posicao_estoque(self):
        messagebox.showinfo("Posição de Estoque", "Está função será implementada posteriormente, pelo nosso time de TI.")

    def abrir_receber_nf(self):
        self.root.withdraw()
        RecebimentoNFeWindow(self.root, self.omie_estoque_api)
if __name__ == "__main__":
    root = tk.Tk()
    app = MainApp(root)
    root.mainloop()


