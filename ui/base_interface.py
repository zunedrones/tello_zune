import tkinter as tk
from tkinter import ttk

class BaseGUI:
    """
    Uma classe base genérica para criar interfaces com um painel principal
    e uma barra lateral.
    """
    def __init__(self, root: tk.Tk, title: str = "Generic Application", geometry: str = "1200x800"):
        self.root = root
        self.root.title(title)
        self.root.geometry(geometry)

        # 1. Configurações genéricas de estilo
        self._setup_styles()

        # 2. Criação do layout principal (frames vazios)
        self._create_main_layout()

        # 3. Chamada para os métodos que as classes filhas irão implementar
        self._create_main_widgets(self.main_frame)
        self._create_sidebar_widgets(self.sidebar_frame)
        
        # 4. Configura o fechamento da janela
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _setup_styles(self) -> None:
        """Configura estilos visuais básicos para a aplicação."""
        self.style = ttk.Style(self.root)
        self.style.theme_use("clam")
        BG_COLOR = "#262626"
        TEXT_COLOR = "#FFFFFF"
        LBF_COLOR = "#3c3c3c"
        
        self.root.configure(bg=BG_COLOR)
        self.style.configure('TFrame', background=BG_COLOR)
        self.style.configure('TLabel', background=BG_COLOR, foreground=TEXT_COLOR, font=('Ubuntu', 12))
        self.style.configure('TButton', background='#555555', foreground='white', borderwidth=1)
        self.style.map('TButton', background=[('active', "#939393")])
        self.style.configure('TLabelframe', background=LBF_COLOR, bordercolor=TEXT_COLOR)
        self.style.configure('TLabelframe.Label', background=LBF_COLOR, foreground=TEXT_COLOR)

    def _create_main_layout(self) -> None:
        """Cria os containers principais da interface (área principal e sidebar)."""
        self.root.columnconfigure(0, weight=3)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)

        # Container para os widgets principais (ex: vídeo, texto grande)
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # Container para a barra lateral (ex: controles, parâmetros)
        self.sidebar_frame = ttk.Frame(self.root)
        self.sidebar_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

    # --- Métodos para serem sobrescritos pelas classes filhas ---

    def _create_main_widgets(self, container: ttk.Frame) -> None:
        """
        Método 'abstrato' para preencher a área principal.
        A classe filha DEVE implementar este método.
        """
        # Exemplo: colocar um texto genérico para mostrar que funciona
        ttk.Label(container, text="Área Principal - Implemente em sua subclasse").pack()

    def _create_sidebar_widgets(self, container: ttk.Frame) -> None:
        """
        Método 'abstrato' para preencher a barra lateral.
        A classe filha DEVE implementar este método.
        """
        # Exemplo: colocar um texto genérico
        ttk.Label(container, text="Barra Lateral - Implemente em sua subclasse").pack()

    def start_update_loops(self) -> None:
        """
        Método 'abstrato' para iniciar loops de atualização (ex: vídeo, dados).
        A classe filha DEVE implementar, se necessário.
        """
        pass

    def cleanup(self) -> None:
        """
        Método 'abstrato' para limpeza antes de fechar (ex: pousar drone).
        A classe filha DEVE implementar, se necessário.
        """
        pass

    # --- Métodos de ciclo de vida ---

    def _on_close(self) -> None:
        """Função genérica chamada ao fechar a janela."""
        print("Executando limpeza e fechando a aplicação...")
        self.cleanup()
        self.root.destroy()
        
    def run(self) -> None:
        """Inicia o loop principal da interface."""
        self.start_update_loops()
        self.root.mainloop()