# O programa analisa arquivos, mostra uma prévia, organiza por categoria e detecta duplicados.
# Os movimentos são registrados em um histórico local para permitir desfazer as operações.
# Dependências: Python 3; Pillow é opcional e habilita miniaturas de imagens.

# Sistema de arquivos, caminhos e operações locais.
import os
import sys
# Operações de movimentação de arquivos.
import shutil
# Leitura e gravação do histórico em formato JSON.
import json
# Cálculo de hash para comparar o conteúdo de arquivos.
import hashlib
# Exportação de relatórios de estatísticas para CSV.
import csv
# Expressões regulares para reconhecer nomes de pastas de categoria.
import re
# Conversão de datas de modificação/criação para exibição.
from datetime import datetime
# Interface gráfica nativa do Python.
import tkinter as tk
# Diálogos, mensagens, caixa de relatório e widgets com estilo.
from tkinter import filedialog, messagebox, scrolledtext, ttk

# Localiza arquivos incluídos no programa, tanto no código-fonte quanto no executável.
def caminho_recurso(nome):
    pasta_base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(pasta_base, nome)


# Pillow é opcional: quando instalado, permite mostrar miniaturas de imagens.
try:
    from PIL import Image, ImageTk
except ImportError:
    Image = None
    ImageTk = None


# ============================================================
# CONFIGURAÇÕES
# Mapeia cada categoria para as extensões que serão reconhecidas.
# ============================================================

CATEGORIES = {
    "Imagens": [
        ".jpg", ".jpeg", ".png", ".gif",
        ".bmp", ".svg", ".webp"
    ],

    "Documentos": [
        ".pdf", ".doc", ".docx", ".txt",
        ".odt", ".rtf"
    ],

    "Planilhas": [
        ".xls", ".xlsx", ".ods", ".csv"
    ],

    "Apresentações": [
        ".ppt", ".pptx", ".odp"
    ],

    "Áudios": [
        ".mp3", ".wav", ".aac", ".ogg", ".flac"
    ],

    "Vídeos": [
        ".mp4", ".avi", ".mov", ".mkv",
        ".wmv", ".webm"
    ],

    "Compactados": [
        ".zip", ".rar", ".tar", ".gz", ".7z"
    ],

    "Executáveis": [
        ".exe", ".msi", ".sh", ".bat", ".apk"
    ],

    "Códigos": [
        ".py", ".c", ".cpp", ".java",
        ".js", ".html", ".css",
        ".php", ".json", ".sql"
    ],

    "Outros": []
}


# Nome do arquivo de histórico criado dentro da pasta selecionada.
HISTORY_FILE = "historico_organizacao.json"


# Usa a extensão do arquivo para escolher uma categoria definida em CATEGORIES.
def get_category(extension):
    # Padroniza a extensão para que .JPG e .jpg sejam tratados da mesma forma.
    extension = extension.lower()
    for category, extensions in CATEGORIES.items():
        if extension in extensions:
            return category
    return "Outros"


# Procura um caminho existente sem diferenciar letras maiúsculas de minúsculas.
def find_case_insensitive_path(path):
    # Separa o diretório pai do nome que estamos tentando localizar.
    parent = os.path.dirname(path) or "."
    name = os.path.basename(path)

    if not os.path.isdir(parent):
        return path if os.path.exists(path) else None

    try:
        for entry in os.listdir(parent):
            if entry.casefold() == name.casefold():
                return os.path.join(parent, entry)
    except OSError:
        pass

    return None


# Evita colisões com caminhos que já existem ou que a prévia já reservou.
def path_is_taken(path, reserved=None):
    # Primeiro verifica a lista de destinos já reservados durante esta operação.
    if reserved is not None and os.path.normcase(os.path.abspath(path)).casefold() in reserved:
        return True
    return find_case_insensitive_path(path) is not None


# Se o nome estiver ocupado, acrescenta um número até encontrar um nome livre.
def generate_unique_path(destination, reserved=None):
    if not path_is_taken(destination, reserved):
        return destination

    # Divide o destino em pasta, nome e extensão para criar alternativas numeradas.
    folder = os.path.dirname(destination)
    filename = os.path.basename(destination)
    name, extension = os.path.splitext(filename)
    counter = 1

    while True:
        new_destination = os.path.join(folder, f"{name} ({counter}){extension}")
        if not path_is_taken(new_destination, reserved):
            return new_destination
        counter += 1


# Decide qual pasta de categoria usar e evita conflitos com arquivos de mesmo nome.
def get_category_folder(directory, category):
    requested = os.path.join(directory, category)
    existing = find_case_insensitive_path(requested)

    if existing and os.path.isdir(existing):
        return existing
    if not existing:
        return requested

    counter = 1
    while True:
        candidate = os.path.join(directory, f"{category} ({counter})")
        existing_candidate = find_case_insensitive_path(candidate)
        if existing_candidate and os.path.isdir(existing_candidate):
            return existing_candidate
        if not existing_candidate:
            return candidate
        counter += 1


# Mantém o arquivo de histórico dentro da pasta que está sendo organizada.
def history_path(directory):
    # Usa caminho absoluto para o histórico continuar associado à pasta correta.
    return os.path.join(os.path.abspath(directory), HISTORY_FILE)


# Grava os caminhos originais e novos para permitir desfazer os movimentos.
def save_history(history, directory):
    try:
        # O modo "w" cria ou substitui o arquivo de histórico em UTF-8.
        with open(history_path(directory), "w", encoding="utf-8") as file:
            json.dump(history, file, indent=4, ensure_ascii=False)
    except OSError as error:
        print(f"Erro ao salvar histórico: {error}")


# Lê o histórico da pasta escolhida; se não houver histórico válido, retorna lista vazia.
def load_history(directory):
    path = history_path(directory)
    if not os.path.exists(path):
        return []
    try:
        # Abre o histórico para leitura sem alterar seu conteúdo.
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError) as error:
        print(f"Erro ao ler histórico: {error}")
        return []


# Reconhece pastas de categorias e a pasta de revisão que não devem ser reorganizadas.
def should_skip_folder(name):
    if name == "_Duplicados_para_revisar":
        return True
    for category in CATEGORIES:
        if name.casefold() == category.casefold():
            return True
        if re.fullmatch(re.escape(category) + r" \(\d+\)", name, re.IGNORECASE):
            return True
    return False


# Percorre as subpastas e entrega os caminhos dos arquivos um por um.
def walk_files(directory, skip_category_folders=False):
    # os.walk percorre a pasta selecionada e suas subpastas.
    for current_root, dirs, filenames in os.walk(directory):
        # Filtra pastas que não devem ser percorridas e mantém uma ordem previsível.
        dirs[:] = sorted(
            [name for name in dirs if name != "_Duplicados_para_revisar"
             and not (skip_category_folders and should_skip_folder(name))],
            key=str.casefold
        )
        for filename in sorted(filenames, key=str.casefold):
            path = os.path.join(current_root, filename)
            if os.path.abspath(path) == os.path.abspath(os.path.join(directory, HISTORY_FILE)):
                continue
            # yield entrega um caminho por vez, sem montar uma lista enorme na memória.
            yield path


# Prévia: esta função apenas calcula os destinos, sem mover arquivos.
# Monta uma lista de destinos previstos sem alterar os arquivos no disco.
def preview_files(directory):
    if not os.path.isdir(directory):
        raise FileNotFoundError("A pasta informada não existe ou não pode ser acessada.")
    # Esta lista acumulará os dados necessários para exibir cada arquivo na tabela.
    preview = []
    # Guarda destinos já usados na prévia para não sugerir o mesmo caminho duas vezes.
    reserved = set()
    category_folders = {}
    for file_path in walk_files(directory, skip_category_folders=False):
        filename = os.path.basename(file_path)
        relative_source = os.path.relpath(file_path, directory)
        _, extension = os.path.splitext(filename)
        extension = extension.lower()
        category = get_category(extension)
        if category not in category_folders:
            category_folders[category] = get_category_folder(directory, category)
        category_folder = category_folders[category]
        requested_destination = os.path.join(category_folder, filename)
        first_folder = relative_source.split(os.sep, 1)[0] if os.sep in relative_source else ""
        already_in_category = os.path.isdir(os.path.join(directory, first_folder)) and should_skip_folder(first_folder)
        if already_in_category or os.path.normcase(os.path.abspath(file_path)) == os.path.normcase(os.path.abspath(requested_destination)):
            destination = file_path
            conflict = False
        else:
            destination = generate_unique_path(requested_destination, reserved)
            conflict = os.path.normcase(os.path.abspath(destination)).casefold() != os.path.normcase(os.path.abspath(requested_destination)).casefold()
        reserved.add(os.path.normcase(os.path.abspath(destination)).casefold())
        preview.append({
            "filename": filename, "relative_source": relative_source, "source": file_path,
            "extension": extension or "Sem extensão", "category": category,
            "category_folder": category_folder, "destination": destination,
            "conflict": conflict, "folder_conflict": os.path.basename(category_folder) != category
        })
    return preview


# Duplicatas: arquivos são comparados pelo conteúdo, não apenas pelo nome.
# Calcula SHA-256 em blocos, evitando carregar arquivos grandes inteiros na memória.
def file_hash(path):
    # Cria o acumulador SHA-256 que representa o conteúdo do arquivo.
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        # Lê blocos de 1 MiB até chegar ao fim do arquivo.
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            # Incorpora o bloco atual ao cálculo do hash.
            digest.update(chunk)
    return digest.hexdigest()


# Agrupa arquivos com mesmo tamanho e hash, forte indicação de conteúdo idêntico.
def find_duplicate_groups(directory):
    # A chave combina tamanho e hash; o valor guarda os caminhos correspondentes.
    by_hash = {}
    for path in walk_files(directory, skip_category_folders=False):
        try:
            size = os.path.getsize(path)
            by_hash.setdefault((size, file_hash(path)), []).append(path)
        except OSError:
            continue
    return [paths for paths in by_hash.values() if len(paths) > 1]


# Organização real: os movimentos são registrados para permitir a restauração posterior.
# Move arquivos para as pastas de categoria e registra cada movimento bem-sucedido.
def organize_files(directory, log_callback):
    if not os.path.isdir(directory):
        raise FileNotFoundError("A pasta informada não existe ou não pode ser acessada.")
    # Cada item registra o caminho original e o destino para permitir desfazer.
    moved_files = []
    moved_count = 0
    # Copia os caminhos para uma lista antes de mover, pois a árvore de pastas mudará.
    for file_path in list(walk_files(directory, skip_category_folders=True)):
        filename = os.path.basename(file_path)
        _, extension = os.path.splitext(filename)
        category = get_category(extension.lower())
        try:
            category_folder = get_category_folder(directory, category)
            os.makedirs(category_folder, exist_ok=True)
            if not os.path.isdir(category_folder):
                raise OSError(f"O destino da categoria não é uma pasta: {category_folder}")
            requested_destination = os.path.join(category_folder, filename)
            if os.path.normcase(os.path.abspath(file_path)) == os.path.normcase(os.path.abspath(requested_destination)):
                continue
            destination = generate_unique_path(requested_destination)
            if path_is_taken(destination):
                destination = generate_unique_path(destination)
            # Move o arquivo para o destino calculado sem substituir outro arquivo.
            shutil.move(file_path, destination)
            # Registra o movimento para que a função de desfazer saiba onde devolver.
            moved_files.append({"original": file_path, "destination": destination})
            moved_count += 1
            log_callback(f"✓ {os.path.relpath(file_path, directory)} → {os.path.relpath(destination, directory)}")
        except (OSError, shutil.Error) as error:
            log_callback(f"✗ Erro ao mover {filename}: {error}")
    if moved_files:
        # Junta os novos movimentos ao histórico da pasta em vez de apagar registros anteriores.
        previous_history = load_history(directory)
        save_history(previous_history + moved_files, directory)
    return moved_count, moved_files


# Desfazer: o histórico é específico da pasta escolhida, evitando misturar trabalhos distintos.
# Tenta devolver os arquivos aos caminhos originais, preservando conflitos no histórico.
def undo_last_organization(directory, log_callback):
    # Recupera somente os movimentos registrados para esta pasta.
    history = load_history(directory)
    if not history:
        return False, "Nenhuma operação registrada para desfazer nesta pasta."

    restored_count = 0
    remaining_history = []

    # Desfaz em ordem inversa, como uma pilha de operações.
    for operation in reversed(history):
        original = operation.get("original")
        destination = operation.get("destination")

        if not original or not destination or not os.path.exists(destination):
            log_callback(f"✗ Arquivo não encontrado: {destination or 'caminho inválido'}")
            if original and destination:
                remaining_history.append(operation)
            continue

        try:
            if path_is_taken(original):
                log_callback(f"✗ Não foi possível restaurar porque o destino já existe: {original}")
                remaining_history.append(operation)
                continue

            # Restaura o arquivo no local em que estava antes da organização.
            shutil.move(destination, original)
            restored_count += 1
            log_callback(f"↩ Restaurado: {os.path.basename(original)}")
        except (OSError, shutil.Error) as error:
            log_callback(f"✗ Erro ao restaurar arquivo: {error}")
            remaining_history.append(operation)

    if remaining_history:
        save_history(list(reversed(remaining_history)), directory)
    else:
        try:
            path = history_path(directory)
            if os.path.exists(path):
                os.remove(path)
        except OSError:
            pass

    if restored_count:
        return True, f"{restored_count} arquivo(s) restaurado(s)."
    return False, "Nenhum arquivo foi restaurado. Consulte o relatório para ver os motivos."


# Reúne os componentes visuais e as ações que o usuário pode executar.
class FileOrganizerApp:
    # Paleta escura com acentos violeta. Continua usando apenas Tkinter/ttk.
    BG = "#0D0B14"
    PANEL = "#171421"
    PANEL_ALT = "#1D192A"
    BORDER = "#30283F"
    TEXT = "#F4F0FF"
    MUTED = "#A7A0B8"
    PURPLE = "#7C3AED"
    PURPLE_HOVER = "#8B5CF6"
    GREEN = "#22C55E"
    BLUE = "#38BDF8"

    # Configura a janela principal e prepara o estado inicial da aplicação.
    def __init__(self, root):
        self.root = root
        # Reutiliza o ícone extraído do executável da versão antiga.
        try:
            self.root.iconbitmap(caminho_recurso("icone_extraido.ico"))
        except (tk.TclError, OSError):
            pass
        self.root.title("Organizador de Arquivos | Dashboard")
        self.root.geometry("1380x850")
        self.root.minsize(1000, 680)
        self.root.configure(bg=self.BG)
        # Relaciona cada linha da tabela aos dados completos do arquivo.
        self.preview_items = {}
        self.all_preview_items = []
        self.search_var = tk.StringVar()
        self.category_var = tk.StringVar(value="Todas")
        self.extension_var = tk.StringVar()
        # Mantém referência à miniatura para que o Tkinter não a descarte da tela.
        self.current_photo = None
        self._setup_styles()
        self.create_interface()

    # Define cores, fontes e estilos dos componentes ttk, especialmente da tabela.
    def _setup_styles(self):
        # O objeto Style controla a aparência dos widgets ttk.
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Dark.Treeview", background=self.PANEL, fieldbackground=self.PANEL,
                        foreground=self.TEXT, borderwidth=0, rowheight=31,
                        font=("Segoe UI", 9))
        style.configure("Dark.Treeview.Heading", background="#241D33", foreground="#D9CCFF",
                        relief="flat", borderwidth=0, font=("Segoe UI", 9, "bold"), padding=(8, 10))
        style.map("Dark.Treeview", background=[("selected", "#4C2A7A")],
                  foreground=[("selected", "#FFFFFF")])
        style.map("Dark.Treeview.Heading", background=[("active", "#33264A")])

        # Combobox de categoria com a mesma paleta roxo-escura da aplicação.
        style.configure("Dark.TCombobox",
                        fieldbackground="#100D19",
                        background="#292438",
                        foreground=self.TEXT,
                        arrowcolor="#D9CCFF",
                        bordercolor=self.BORDER,
                        lightcolor=self.BORDER,
                        darkcolor=self.BORDER,
                        padding=(8, 6),
                        relief="flat")
        style.map("Dark.TCombobox",
                  fieldbackground=[("readonly", "#100D19"), ("focus", "#171421")],
                  foreground=[("readonly", self.TEXT), ("disabled", self.MUTED)],
                  background=[("readonly", "#292438"), ("active", "#39314D")],
                  arrowcolor=[("disabled", self.MUTED), ("active", "#FFFFFF")],
                  selectbackground=[("readonly", "#4C2A7A")],
                  selectforeground=[("readonly", "#FFFFFF")])
        # Estiliza também a lista aberta de categorias (lista suspensa).
        self.root.option_add("*TCombobox*Listbox.background", "#171421")
        self.root.option_add("*TCombobox*Listbox.foreground", self.TEXT)
        self.root.option_add("*TCombobox*Listbox.selectBackground", "#4C2A7A")
        self.root.option_add("*TCombobox*Listbox.selectForeground", "#FFFFFF")
        self.root.option_add("*TCombobox*Listbox.font", ("Segoe UI", 9))

        style.configure("Dark.Vertical.TScrollbar", background="#342B46", troughcolor=self.PANEL,
                        bordercolor=self.PANEL, arrowcolor="#D9CCFF")
        style.configure("Dark.Horizontal.TScrollbar", background="#342B46", troughcolor=self.PANEL,
                        bordercolor=self.PANEL, arrowcolor="#D9CCFF")

    # Cria um painel reutilizável com fundo escuro e borda discreta.
    def _card(self, parent, **kwargs):
        return tk.Frame(parent, bg=self.PANEL, highlightbackground=self.BORDER,
                        highlightthickness=1, bd=0, **kwargs)

    # Padroniza botões e adiciona mudança de cor quando o mouse passa por cima.
    def _button(self, parent, text, command, variant="secondary", **kwargs):
        # Cada variante de botão define cor normal, cor ao passar o mouse e texto.
        colors = {
            "primary": (self.PURPLE, self.PURPLE_HOVER, "#FFFFFF"),
            "success": ("#166534", "#15803D", "#F0FDF4"),
            "blue": ("#075985", "#0369A1", "#F0F9FF"),
            "secondary": ("#292438", "#39314D", self.TEXT),
            "danger": ("#54223D", "#713052", "#FFE4F0"),
        }
        bg, active, fg = colors[variant]
        button = tk.Button(parent, text=text, command=command, bg=bg, fg=fg,
                           activebackground=active, activeforeground=fg, relief="flat", bd=0,
                           padx=14, pady=10, cursor="hand2", font=("Segoe UI", 9, "bold"),
                           **kwargs)
        button.bind("<Enter>", lambda _e: button.configure(bg=active))
        button.bind("<Leave>", lambda _e: button.configure(bg=bg))
        return button

    # Desenha o cabeçalho em gradiente usando linhas do Canvas do Tkinter.
    def _gradient_header(self, parent):
        height, width = 118, 1200
        canvas = tk.Canvas(parent, height=height, highlightthickness=0, bd=0, bg=self.BG)
        canvas.grid(row=0, column=0, sticky="ew")
        parent.grid_columnconfigure(0, weight=1)
        # Gradiente desenhado em faixas, sem bibliotecas adicionais.
        start = (48, 24, 78)
        end = (28, 35, 78)

        # Redesenha o fundo usando a largura atual do cabeçalho.
        def draw_gradient(event=None):
            current_width = max(canvas.winfo_width(), width)
            canvas.delete("all")
            for i in range(current_width):
                ratio = i / max(current_width - 1, 1)
                color = "#%02x%02x%02x" % tuple(
                    int(start[j] * (1-ratio) + end[j] * ratio) for j in range(3)
                )
                canvas.create_line(i, 0, i, height, fill=color)
            canvas.create_oval(current_width-250, -100, current_width+50, 180, fill="#332064", outline="")
            canvas.create_oval(current_width-160, 45, current_width+10, 210, fill="#27285D", outline="")
            canvas.create_text(34, 34, anchor="w", text="ORGANIZADOR DE ARQUIVOS",
                               fill="#C4B5FD", font=("Segoe UI", 9, "bold"))
            canvas.create_text(32, 65, anchor="w", text="Sua organização, em outro nível.",
                               fill="#FFFFFF", font=("Segoe UI", 21, "bold"))
            canvas.create_text(34, 94, anchor="w", text="Visualize • classifique • organize com segurança",
                               fill="#D4CDE5", font=("Segoe UI", 10))
            canvas.create_text(current_width-70, 55, text="✦", fill="#C4B5FD", font=("Segoe UI", 34, "bold"))

        # O evento Configure é disparado quando o cabeçalho muda de tamanho.
        canvas.bind("<Configure>", draw_gradient)
        return canvas

    # Monta o layout principal: cabeçalho, ações, tabela, prévia e relatório.
    def create_interface(self):
        # Permite que a área de trabalho cresça quando a janela for redimensionada.
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        self._gradient_header(self.root)

        workspace = tk.Frame(self.root, bg=self.BG)
        workspace.grid(row=1, column=0, sticky="nsew")
        workspace.grid_rowconfigure(0, weight=1)
        workspace.grid_columnconfigure(1, weight=1)

        # Painel lateral informativo: não há itens falsos de navegação.
        # Ele apresenta apenas o fluxo de uso, enquanto todas as ações reais
        # ficam disponíveis nos botões da área principal.
        sidebar = tk.Frame(workspace, bg="#100D19", width=205)
        sidebar.grid(row=0, column=0, sticky="nsw")
        sidebar.grid_propagate(False)

        tk.Label(
            sidebar, text="COMO UTILIZAR", bg="#100D19", fg="#BBA8E8",
            font=("Segoe UI", 9, "bold")
        ).pack(anchor="w", padx=18, pady=(24, 14))

        # Etapas de uso são apenas instruções visuais, não abas clicáveis.
        for number, instruction in [
            ("01", "Escolha uma pasta"),
            ("02", "Confira a prévia"),
            ("03", "Organize arquivos"),
            ("04", "Revise duplicados"),
            ("05", "Desfaça se necessário"),
        ]:
            step = tk.Frame(sidebar, bg="#100D19")
            step.pack(fill="x", padx=14, pady=7)
            tk.Label(
                step, text=number, bg="#29203A", fg="#C4B5FD",
                font=("Segoe UI", 8, "bold"), padx=7, pady=5
            ).pack(side="left")
            tk.Label(
                step, text=instruction, bg="#100D19", fg="#B7AEC7",
                font=("Segoe UI", 8), anchor="w", wraplength=125, justify="left"
            ).pack(side="left", padx=8)

        tk.Frame(sidebar, bg=self.BORDER, height=1).pack(
            fill="x", padx=16, pady=18
        )
        tk.Label(
            sidebar,
            text="Seus arquivos permanecem no computador. Duplicados são movidos para uma pasta de revisão, não apagados.",
            bg="#100D19", fg="#8F849F", font=("Segoe UI", 8),
            wraplength=165, justify="left"
        ).pack(anchor="w", padx=18)
        tk.Label(
            sidebar, text="TKINTER • LOCAL", bg="#100D19", fg="#5F566F",
            font=("Segoe UI", 7, "bold")
        ).pack(side="bottom", pady=18)

        main = tk.Frame(workspace, bg=self.BG)
        main.grid(row=0, column=1, sticky="nsew", padx=(20, 22), pady=(18, 16))
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(3, weight=1)

        # Seletor de pasta
        folder_card = self._card(main)
        folder_card.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        folder_card.grid_columnconfigure(0, weight=1)
        tk.Label(folder_card, text="PASTA DE TRABALHO", bg=self.PANEL, fg="#BBA8E8",
                 font=("Segoe UI", 8, "bold")).grid(row=0, column=0, sticky="w", padx=16, pady=(12, 4))
        path_row = tk.Frame(folder_card, bg=self.PANEL)
        path_row.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 13))
        path_row.grid_columnconfigure(0, weight=1)
        self.folder_entry = tk.Entry(path_row, font=("Segoe UI", 10), bg="#100D19", fg=self.TEXT,
                                     insertbackground=self.TEXT, relief="flat", bd=0,
                                     highlightthickness=1, highlightbackground=self.BORDER,
                                     highlightcolor=self.PURPLE)
        self.folder_entry.grid(row=0, column=0, sticky="ew", ipady=11, padx=(0, 10))
        self.folder_entry.insert(0, "")
        self._button(path_row, "▣  Escolher pasta", self.select_folder, "secondary").grid(row=0, column=1)

        # Ações principais
        actions = tk.Frame(main, bg=self.BG)
        actions.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        for col in range(5):
            actions.grid_columnconfigure(col, weight=1, uniform="actions")
        self._button(actions, "◉  Pré-visualizar", self.show_preview, "blue").grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self._button(actions, "✦  Organizar", self.start_organization, "primary").grid(row=0, column=1, sticky="ew", padx=3)
        self._button(actions, "⧉  Duplicados", self.show_duplicates, "secondary").grid(row=0, column=2, sticky="ew", padx=3)
        self._button(actions, "↶  Desfazer", self.undo_organization, "danger").grid(row=0, column=3, sticky="ew", padx=3)
        self._button(actions, "▥  Estatísticas", self.show_statistics, "secondary").grid(row=0, column=4, sticky="ew", padx=(5, 0))

        # Resumo de estado
        summary_card = self._card(main)
        summary_card.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        tk.Label(summary_card, text="RESUMO DA ANÁLISE", bg=self.PANEL, fg="#BBA8E8",
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=15, pady=(10, 3))
        self.summary_label = tk.Label(summary_card,
            text="Selecione uma pasta e clique em Pré-visualizar para analisar os arquivos.",
            bg=self.PANEL, fg=self.TEXT, anchor="w", justify="left", font=("Segoe UI", 9), wraplength=1050)
        self.summary_label.pack(fill="x", padx=15, pady=(0, 12))

        # Área de arquivos e pré-visualização
        content = tk.PanedWindow(main, orient="horizontal", sashwidth=5, sashrelief="flat",
                                 bg=self.BG, bd=0, opaqueresize=True)
        content.grid(row=3, column=0, sticky="nsew", pady=(0, 12))
        list_frame = self._card(content)
        columns = ("source", "extension", "category", "destination", "size", "modified", "status")
        # Barra de pesquisa e filtros. Os controles afetam apenas a visualização,
        # sem alterar ou mover os arquivos no disco.
        filter_bar = tk.Frame(list_frame, bg=self.PANEL)
        filter_bar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=10)
        filter_bar.grid_columnconfigure(0, weight=3)
        filter_bar.grid_columnconfigure(2, weight=1)
        tk.Label(filter_bar, text="Pesquisar", bg=self.PANEL, fg=self.MUTED,
                 font=("Segoe UI", 8, "bold")).grid(row=0, column=0, sticky="w")
        self.search_entry = tk.Entry(filter_bar, textvariable=self.search_var,
                                     font=("Segoe UI", 9), bg="#100D19", fg=self.TEXT,
                                     insertbackground=self.TEXT, relief="flat",
                                     highlightthickness=1, highlightbackground=self.BORDER)
        self.search_entry.grid(row=1, column=0, sticky="ew", padx=(0, 10), ipady=7)
        self.search_entry.insert(0, "")
        tk.Label(filter_bar, text="Categoria", bg=self.PANEL, fg=self.MUTED,
                 font=("Segoe UI", 8, "bold")).grid(row=0, column=1, sticky="w")
        self.category_filter = ttk.Combobox(filter_bar, textvariable=self.category_var,
                                            values=["Todas"] + list(CATEGORIES.keys()),
                                            state="readonly", width=15, style="Dark.TCombobox")
        self.category_filter.grid(row=1, column=1, sticky="ew", padx=(0, 10), ipady=3)
        tk.Label(filter_bar, text="Extensão", bg=self.PANEL, fg=self.MUTED,
                 font=("Segoe UI", 8, "bold")).grid(row=0, column=2, sticky="w")
        self.extension_entry = tk.Entry(filter_bar, textvariable=self.extension_var,
                                        font=("Segoe UI", 9), bg="#100D19", fg=self.TEXT,
                                        insertbackground=self.TEXT, relief="flat",
                                        highlightthickness=1, highlightbackground=self.BORDER,
                                        width=12)
        self.extension_entry.grid(row=1, column=2, sticky="ew", padx=(0, 10), ipady=7)
        self._button(filter_bar, "Limpar filtros", self.clear_filters, "secondary").grid(row=1, column=3, sticky="ew")
        self.filter_count_label = tk.Label(filter_bar, text="Exibindo 0 arquivo(s)",
                                           bg=self.PANEL, fg=self.MUTED, font=("Segoe UI", 8))
        self.filter_count_label.grid(row=2, column=0, columnspan=4, sticky="w", pady=(7, 0))
        self.search_var.trace_add("write", lambda *_: self.apply_filters())
        self.extension_var.trace_add("write", lambda *_: self.apply_filters())
        self.category_filter.bind("<<ComboboxSelected>>", lambda _event: self.apply_filters())

        self.file_tree = ttk.Treeview(list_frame, columns=columns, show="tree headings",
                                      selectmode="extended", style="Dark.Treeview")
        self.file_tree.heading("#0", text="Arquivo")
        self.file_tree.heading("source", text="Local atual")
        self.file_tree.heading("extension", text="Extensão")
        self.file_tree.heading("category", text="Categoria")
        self.file_tree.heading("destination", text="Destino previsto")
        self.file_tree.heading("size", text="Tamanho")
        self.file_tree.heading("modified", text="Modificado em")
        self.file_tree.heading("status", text="Situação")
        self.file_tree.column("#0", width=175, minwidth=130)
        self.file_tree.column("source", width=185, minwidth=130)
        self.file_tree.column("extension", width=85, minwidth=70, anchor="center")
        self.file_tree.column("category", width=110, minwidth=90)
        self.file_tree.column("destination", width=230, minwidth=150)
        self.file_tree.column("size", width=90, minwidth=70, anchor="e")
        self.file_tree.column("modified", width=145, minwidth=125)
        self.file_tree.column("status", width=150, minwidth=120)
        tree_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.file_tree.yview, style="Dark.Vertical.TScrollbar")
        horizontal_scroll = ttk.Scrollbar(list_frame, orient="horizontal", command=self.file_tree.xview, style="Dark.Horizontal.TScrollbar")
        self.file_tree.configure(yscrollcommand=tree_scroll.set, xscrollcommand=horizontal_scroll.set)
        self.file_tree.grid(row=1, column=0, sticky="nsew", padx=(1, 0), pady=(1, 0))
        tree_scroll.grid(row=1, column=1, sticky="ns", pady=(1, 0))
        horizontal_scroll.grid(row=2, column=0, sticky="ew")
        list_frame.grid_rowconfigure(1, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)
        # Conecta a seleção de uma linha à atualização do painel de detalhes.
        self.file_tree.bind("<<TreeviewSelect>>", self.on_file_selected)
        content.add(list_frame, minsize=520, stretch="always")

        preview_frame = self._card(content)
        preview_frame.configure(width=280)
        preview_frame.grid_propagate(False)
        tk.Label(preview_frame, text="PRÉ-VISUALIZAÇÃO", bg=self.PANEL, fg="#BBA8E8",
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=14, pady=(13, 8))
        self.image_label = tk.Label(preview_frame, text="Selecione um arquivo\npara ver os detalhes.",
                                    justify="center", anchor="center", wraplength=235,
                                    bg="#100D19", fg=self.MUTED, font=("Segoe UI", 9),
                                    padx=8, pady=12)
        self.image_label.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        self.details_label = tk.Label(preview_frame, text="", justify="left", anchor="nw",
                                      wraplength=240, font=("Segoe UI", 8), bg=self.PANEL,
                                      fg="#C7BED8")
        self.details_label.pack(fill="x", padx=13, pady=(0, 14))
        content.add(preview_frame, minsize=250, width=280, stretch="never")

        # Relatório / log
        report_card = self._card(main)
        report_card.grid(row=4, column=0, sticky="ew")
        report_header = tk.Frame(report_card, bg=self.PANEL)
        report_header.pack(fill="x", padx=14, pady=(9, 5))
        tk.Label(report_header, text="RELATÓRIO DE ATIVIDADE", bg=self.PANEL, fg="#BBA8E8",
                 font=("Segoe UI", 8, "bold")).pack(side="left")
        self._button(report_header, "Limpar", self.clear_log, "secondary").pack(side="right")
        self.log_text = scrolledtext.ScrolledText(report_card, height=5, font=("Consolas", 9),
            state="disabled", bg="#100D19", fg="#CFC6E2", insertbackground=self.TEXT,
            relief="flat", bd=0, padx=12, pady=9, wrap="word",
            selectbackground="#4C2A7A")
        self.log_text.pack(fill="x", padx=12, pady=(0, 12))
        self.add_log("Aplicativo iniciado. Escolha uma pasta para começar.")

    # Apaga o texto do relatório e registra que ele foi limpo.
    def clear_log(self):
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", tk.END)
        self.log_text.config(state="disabled")
        self.add_log("Relatório limpo.")

    # Abre a janela do sistema para escolher a pasta de trabalho.
    def select_folder(self):
        directory = filedialog.askdirectory(title="Selecione a pasta que deseja organizar")
        if directory:
            self.folder_entry.delete(0, tk.END)
            self.folder_entry.insert(0, directory)
            self.add_log(f"Pasta selecionada: {directory}")
            self.clear_preview()

    # Acrescenta uma mensagem ao relatório e mantém visível a linha mais recente.
    def add_log(self, message):
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")

    # Limpa dados antigos da tabela e do painel de pré-visualização.
    def clear_preview(self):
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)
        self.preview_items.clear()
        self.all_preview_items.clear()
        self.current_photo = None
        self.image_label.config(image="", text="Selecione uma imagem\nna lista para visualizá-la.")
        self.details_label.config(text="")
        self.summary_label.config(text="Selecione uma pasta e clique em Pré-visualizar.")

    # Remove os critérios de pesquisa e volta a exibir todos os arquivos analisados.
    def clear_filters(self):
        self.search_var.set("")
        self.category_var.set("Todas")
        self.extension_var.set("")
        self.apply_filters()

    # Aplica pesquisa por nome/caminho e filtros por categoria e extensão.
    def apply_filters(self):
        if not hasattr(self, "file_tree"):
            return
        query = self.search_var.get().strip().casefold()
        category = self.category_var.get()
        extension_query = self.extension_var.get().strip().casefold()
        if extension_query and not extension_query.startswith("."):
            extension_query = "." + extension_query

        for iid in self.file_tree.get_children():
            self.file_tree.delete(iid)
        self.preview_items.clear()
        visible_count = 0

        for item in self.all_preview_items:
            searchable = f"{item['filename']} {item['relative_source']}".casefold()
            if query and query not in searchable:
                continue
            if category != "Todas" and item["category"] != category:
                continue
            actual_extension = os.path.splitext(item["filename"])[1].casefold()
            if extension_query and actual_extension != extension_query:
                continue

            directory = self.folder_entry.get().strip()
            destination = os.path.relpath(item["destination"], directory) if directory else item["destination"]
            status = []
            if item.get("conflict"):
                status.append("Nome alternativo")
            if item.get("folder_conflict"):
                status.append("Pasta alternativa")
            status_text = ", ".join(status) if status else "Sem conflito"
            try:
                stat = os.stat(item["source"])
                size_text = self.format_size(stat.st_size)
                modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
            except OSError:
                size_text, modified = "Indisponível", "Indisponível"
            iid = self.file_tree.insert("", "end", text=item["filename"], values=(
                item["relative_source"], item["extension"], item["category"],
                destination, size_text, modified, status_text))
            self.preview_items[iid] = item
            visible_count += 1

        if hasattr(self, "filter_count_label"):
            self.filter_count_label.config(text=f"Exibindo {visible_count} de {len(self.all_preview_items)} arquivo(s)")

    # Atualiza a tabela com os arquivos, categorias, destinos e possíveis conflitos.
    def show_preview(self):
        directory = self.folder_entry.get().strip()
        if not directory:
            messagebox.showwarning("Atenção", "Selecione uma pasta primeiro.")
            return
        try:
            # Calcula os destinos sem mover nada, para o usuário revisar antes.
            items = preview_files(directory)
            self.clear_preview()
            counts = {category: 0 for category in CATEGORIES}
            conflict_count = 0
            folder_conflict_count = 0

            for item in items:
                counts[item["category"]] += 1
                if item["conflict"]:
                    conflict_count += 1
                if item["folder_conflict"]:
                    folder_conflict_count += 1

                destination = os.path.relpath(item["destination"], directory)
                status = []
                if item["conflict"]:
                    status.append("Nome alternativo")
                if item["folder_conflict"]:
                    status.append("Pasta alternativa")
                first_folder = item["relative_source"].split(os.sep, 1)[0] if os.sep in item["relative_source"] else ""
                if os.path.isdir(os.path.join(directory, first_folder)) and should_skip_folder(first_folder):
                    status.append("Já em pasta organizada")
                status_text = ", ".join(status) if status else "Sem conflito"
                try:
                    stat = os.stat(item["source"])
                    size_text = self.format_size(stat.st_size)
                    modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
                except OSError:
                    size_text, modified = "Indisponível", "Indisponível"
                # Guarda todos os arquivos analisados; a tabela mostrará apenas os que
                # correspondem à pesquisa e aos filtros selecionados.
                self.all_preview_items.append(item)

            self.apply_filters()
            count_text = " | ".join(f"{category}: {count}" for category, count in counts.items() if count)
            if not count_text:
                count_text = "Nenhum arquivo encontrado"
            self.summary_label.config(text=f"Total: {len(items)} arquivo(s)   |   {count_text}   |   Conflitos de nome: {conflict_count}   |   Conflitos de pasta: {folder_conflict_count}")

            self.add_log("=== PRÉ-VISUALIZAÇÃO ATUALIZADA ===")
            self.add_log(f"Total de arquivos: {len(items)}")
            for item in items:
                destination = os.path.relpath(item["destination"], directory)
                self.add_log(f"{item['filename']} → {destination}")
            if conflict_count or folder_conflict_count:
                self.add_log("Foram previstos nomes ou pastas alternativos para evitar conflitos.")
            else:
                self.add_log("Nenhum conflito de nome ou pasta detectado.")

            if not items:
                self.image_label.config(text="Não há arquivos para exibir.")
        except (OSError, ValueError) as error:
            messagebox.showerror("Erro na pré-visualização", str(error))

    # Exibe um painel com estatísticas calculadas a partir da pasta selecionada.
    def show_statistics(self):
        directory = self.folder_entry.get().strip()
        if not directory or not os.path.isdir(directory):
            messagebox.showwarning("Atenção", "Selecione uma pasta válida primeiro.")
            return

        counts = {category: 0 for category in CATEGORIES}
        sizes_by_category = {category: 0 for category in CATEGORIES}
        total_size = 0
        total_files = 0
        largest_files = []

        # Inclui subpastas e categorias organizadas, mas ignora o histórico interno
        # e a pasta de revisão de duplicados, conforme a rotina walk_files.
        for path in walk_files(directory, skip_category_folders=False):
            try:
                size = os.path.getsize(path)
                _, extension = os.path.splitext(path)
                category = get_category(extension)
                counts[category] += 1
                sizes_by_category[category] += size
                total_files += 1
                total_size += size
                largest_files.append((size, path))
            except OSError:
                continue

        largest_files.sort(key=lambda item: item[0], reverse=True)
        largest_files = largest_files[:5]

        # O espaço recuperável considera apenas cópias excedentes de conteúdo idêntico.
        # Os arquivos não são apagados nem movidos por esta análise.
        duplicate_groups = find_duplicate_groups(directory)
        duplicate_extra_count = 0
        duplicate_reclaimable = 0
        duplicate_rows = []
        for paths in duplicate_groups:
            try:
                sizes = [os.path.getsize(path) for path in paths]
                common_size = min(sizes)
                duplicate_extra_count += max(0, len(paths) - 1)
                duplicate_reclaimable += common_size * max(0, len(paths) - 1)
                for path in paths:
                    duplicate_rows.append((path, common_size, len(paths)))
            except OSError:
                continue

        window = tk.Toplevel(self.root)
        window.title("Painel de estatísticas | Organizador de Arquivos")
        window.geometry("1040x760")
        window.minsize(800, 650)
        window.configure(bg=self.BG)
        window.transient(self.root)

        header = tk.Frame(window, bg=self.BG)
        header.pack(fill="x", padx=22, pady=(20, 14))
        tk.Label(header, text="PAINEL DE ESTATÍSTICAS", bg=self.BG, fg=self.TEXT,
                 font=("Segoe UI", 17, "bold")).pack(anchor="w")
        tk.Label(header, text=directory, bg=self.BG, fg=self.MUTED,
                 font=("Segoe UI", 9), wraplength=950, justify="left").pack(anchor="w", pady=(5, 0))

        cards = tk.Frame(window, bg=self.BG)
        cards.pack(fill="x", padx=22, pady=(0, 14))
        for col in range(4):
            cards.grid_columnconfigure(col, weight=1, uniform="stat_cards")

        stats = [
            ("TOTAL DE ARQUIVOS", f"{total_files:,}".replace(",", ".")),
            ("ESPAÇO OCUPADO", self.format_size(total_size)),
            ("CATEGORIAS UTILIZADAS", str(sum(1 for value in counts.values() if value > 0))),
            ("ESPAÇO EM CÓPIAS EXCEDENTES", self.format_size(duplicate_reclaimable)),
        ]
        for col, (label, value) in enumerate(stats):
            card = self._card(cards)
            card.grid(row=0, column=col, sticky="nsew", padx=(0 if col == 0 else 4, 0 if col == 3 else 4))
            tk.Label(card, text=label, bg=self.PANEL, fg=self.MUTED,
                     font=("Segoe UI", 7, "bold"), wraplength=180, justify="left").pack(anchor="w", padx=10, pady=(12, 5))
            tk.Label(card, text=value, bg=self.PANEL, fg=self.TEXT,
                     font=("Segoe UI", 14, "bold"), wraplength=180).pack(anchor="w", padx=10, pady=(0, 12))

        duplicate_note = tk.Label(window,
            text=f"Cópias excedentes identificadas: {duplicate_extra_count}. O espaço é uma estimativa e nenhum arquivo foi alterado.",
            bg=self.BG, fg=self.MUTED, font=("Segoe UI", 9), anchor="w", justify="left")
        duplicate_note.pack(fill="x", padx=24, pady=(0, 10))

        body = tk.Frame(window, bg=self.BG)
        body.pack(fill="both", expand=True, padx=22, pady=(0, 12))
        category_card = self._card(body)
        category_card.pack(fill="both", expand=True, side="left", padx=(0, 7))
        tk.Label(category_card, text="ARQUIVOS POR CATEGORIA", bg=self.PANEL, fg="#BBA8E8",
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=14, pady=(13, 8))

        chart = tk.Canvas(category_card, bg=self.PANEL, highlightthickness=0, height=300)
        chart.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Barras horizontais com quantidade e percentual de cada categoria.
        def draw_chart(_event=None):
            chart.delete("all")
            width = max(chart.winfo_width(), 340)
            row_height = 25
            max_count = max(counts.values(), default=0) or 1
            label_width = 105
            value_width = 80
            bar_width = max(50, width - label_width - value_width - 24)
            for index, (category, count) in enumerate(counts.items()):
                y = 12 + index * row_height
                percentage = (count / total_files * 100) if total_files else 0
                chart.create_text(4, y + 7, text=category, anchor="w", fill=self.TEXT,
                                  font=("Segoe UI", 8))
                x0 = label_width
                chart.create_rectangle(x0, y, x0 + bar_width, y + 13, fill="#292438", outline="")
                filled = bar_width * count / max_count
                if count:
                    chart.create_rectangle(x0, y, x0 + filled, y + 13, fill=self.PURPLE, outline="")
                chart.create_text(x0 + bar_width + 7, y + 7,
                                  text=f"{count} ({percentage:.1f}%)", anchor="w",
                                  fill=self.MUTED, font=("Segoe UI", 8))

        chart.bind("<Configure>", draw_chart)

        largest_card = self._card(body)
        largest_card.pack(fill="both", expand=True, side="left", padx=(7, 0))
        tk.Label(largest_card, text="5 MAIORES ARQUIVOS", bg=self.PANEL, fg="#BBA8E8",
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=14, pady=(13, 8))
        if largest_files:
            for size, path in largest_files:
                item_frame = tk.Frame(largest_card, bg=self.PANEL)
                item_frame.pack(fill="x", padx=12, pady=7)
                tk.Label(item_frame, text=os.path.basename(path), bg=self.PANEL, fg=self.TEXT,
                         font=("Segoe UI", 9, "bold"), anchor="w", wraplength=300,
                         justify="left").pack(fill="x")
                tk.Label(item_frame, text=f"{self.format_size(size)} • {os.path.relpath(path, directory)}",
                         bg=self.PANEL, fg=self.MUTED, font=("Segoe UI", 8), anchor="w",
                         wraplength=300, justify="left").pack(fill="x", pady=(2, 0))
        else:
            tk.Label(largest_card, text="Nenhum arquivo encontrado.", bg=self.PANEL,
                     fg=self.MUTED, font=("Segoe UI", 9)).pack(anchor="w", padx=14, pady=8)

        footer = tk.Frame(window, bg=self.BG)
        footer.pack(fill="x", padx=22, pady=(0, 18))
        tk.Label(footer, text="Análise somente de leitura. A comparação de duplicados pode levar tempo em pastas grandes.",
                 bg=self.BG, fg=self.MUTED, font=("Segoe UI", 8), wraplength=550,
                 justify="left").pack(side="left")
        self._button(footer, "Exportar CSV", lambda: self.export_statistics_csv(
            directory, counts, sizes_by_category, total_files, total_size,
            duplicate_extra_count, duplicate_reclaimable, largest_files, duplicate_rows
        ), "blue").pack(side="right", padx=(8, 0))
        self._button(footer, "Fechar", window.destroy, "secondary").pack(side="right")
        self.add_log(f"Painel de estatísticas aberto: {total_files} arquivo(s), {self.format_size(total_size)}; cópias excedentes: {duplicate_extra_count}.")

    # Exporta resumo, categorias, maiores arquivos e grupos duplicados em CSV.
    def export_statistics_csv(self, directory, counts, sizes_by_category, total_files,
                              total_size, duplicate_extra_count, duplicate_reclaimable,
                              largest_files, duplicate_rows):
        destination = filedialog.asksaveasfilename(
            parent=self.root,
            title="Exportar relatório de estatísticas",
            defaultextension=".csv",
            initialfile="relatorio_estatisticas.csv",
            filetypes=[("Arquivo CSV", "*.csv")]
        )
        if not destination:
            return

        try:
            # utf-8-sig facilita a abertura do arquivo no Excel com acentos corretos.
            with open(destination, "w", newline="", encoding="utf-8-sig") as file:
                writer = csv.writer(file, delimiter=";")
                writer.writerow(["RELATÓRIO DE ESTATÍSTICAS"])
                writer.writerow(["Pasta analisada", directory])
                writer.writerow(["Total de arquivos", total_files])
                writer.writerow(["Espaço ocupado (bytes)", total_size])
                writer.writerow(["Espaço ocupado (legível)", self.format_size(total_size)])
                writer.writerow(["Cópias excedentes", duplicate_extra_count])
                writer.writerow(["Espaço estimado em cópias excedentes (bytes)", duplicate_reclaimable])
                writer.writerow([])
                writer.writerow(["ARQUIVOS POR CATEGORIA"])
                writer.writerow(["Categoria", "Quantidade", "Percentual", "Tamanho (bytes)", "Tamanho (legível)"])
                for category, count in counts.items():
                    percentage = (count / total_files * 100) if total_files else 0
                    writer.writerow([category, count, f"{percentage:.2f}%", sizes_by_category[category], self.format_size(sizes_by_category[category])])
                writer.writerow([])
                writer.writerow(["5 MAIORES ARQUIVOS"])
                writer.writerow(["Arquivo", "Caminho relativo", "Tamanho (bytes)", "Tamanho (legível)"])
                for size, path in largest_files:
                    writer.writerow([os.path.basename(path), os.path.relpath(path, directory), size, self.format_size(size)])
                writer.writerow([])
                writer.writerow(["ARQUIVOS EM GRUPOS DUPLICADOS"])
                writer.writerow(["Caminho relativo", "Tamanho aproximado do grupo (bytes)", "Arquivos no grupo"])
                for path, size, group_count in duplicate_rows:
                    writer.writerow([os.path.relpath(path, directory), size, group_count])
            self.add_log(f"Relatório CSV exportado: {destination}")
            messagebox.showinfo("Exportação concluída", "O relatório de estatísticas foi salvo em CSV.")
        except OSError as error:
            messagebox.showerror("Erro na exportação", f"Não foi possível salvar o relatório.\n{error}")

    # Mostra metadados e, quando possível, uma miniatura do arquivo selecionado.
    def on_file_selected(self, event=None):
        selection = self.file_tree.selection()
        if not selection:
            return
        item = self.preview_items.get(selection[0])
        if not item:
            return

        source = item["source"]
        extension = os.path.splitext(source)[1].lower()
        self.current_photo = None
        self.image_label.config(image="", text="")

        try:
            size = os.path.getsize(source)
            size_text = self.format_size(size)
        except OSError:
            size_text = "Indisponível"

        try:
            stat = os.stat(source)
            created = datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M")
            modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
        except OSError:
            created, modified = "Indisponível", "Indisponível"
        details = (f"Nome: {item['filename']}\nLocal atual: {item.get('relative_source', item['filename'])}"
                   f"\nExtensão: {item['extension']}\nCategoria: {item['category']}"
                   f"\nTamanho: {size_text}\nCriado/registrado em: {created}\nModificado em: {modified}")

        # Só tenta criar miniatura quando a extensão pertence à categoria de imagens.
        if extension in CATEGORIES["Imagens"]:
            if Image is None or ImageTk is None:
                self.image_label.config(text="Para visualizar miniaturas, instale Pillow:\npip install Pillow")
                self.details_label.config(text=details)
                return
            try:
                with Image.open(source) as image:
                    image_format = image.format or extension.lstrip(".").upper()
                    dimensions = f"{image.width} × {image.height}"
                    exif_date = ""
                    try:
                        exif = image.getexif()
                        date_value = exif.get(36867) or exif.get(306)
                        if date_value:
                            exif_date = f"\nData da imagem (EXIF): {date_value}"
                    except Exception:
                        pass
                    # Reduz a imagem mantendo a proporção para caber no painel.
                    image.thumbnail((250, 300))
                    photo = ImageTk.PhotoImage(image.copy())
                self.current_photo = photo
                self.image_label.config(image=photo, text="")
                details += f"\nFormato: {image_format}\nDimensões: {dimensions} px" + exif_date
            except Exception as error:
                self.image_label.config(text=f"Não foi possível abrir esta imagem.\n{error}")
        else:
            self.image_label.config(text="Este arquivo não é uma imagem.\nSelecione uma imagem para ver a miniatura.")

        self.details_label.config(text=details)

    @staticmethod
    # Converte um tamanho em bytes para uma unidade mais fácil de ler.
    def format_size(size):
        units = ("B", "KB", "MB", "GB", "TB")
        value = float(size)
        for unit in units:
            if value < 1024 or unit == units[-1]:
                return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
            value /= 1024


    # Abre a janela de duplicados e permite separar cópias sem apagá-las.
    def show_duplicates(self):
        directory = self.folder_entry.get().strip()
        if not directory or not os.path.isdir(directory):
            messagebox.showwarning("Atenção", "Selecione uma pasta válida primeiro.")
            return
        # Informa no relatório que a comparação de conteúdo está começando.
        self.add_log("=== PROCURANDO ARQUIVOS DUPLICADOS (SHA-256) ===")
        try:
            groups = find_duplicate_groups(directory)
        except OSError as error:
            messagebox.showerror("Erro", f"Não foi possível analisar os arquivos: {error}")
            return

        window = tk.Toplevel(self.root)
        window.title("Detector de arquivos duplicados")
        window.geometry("900x560")
        window.configure(bg="#0D0B14")
        window.transient(self.root)
        tk.Label(window, text=f"Grupos de conteúdo idêntico encontrados: {len(groups)}",
                 bg="#0D0B14", fg="#F4F0FF", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=16, pady=(16, 6))
        tk.Label(window, text="Selecione um arquivo de um grupo para mantê-lo. Os outros arquivos desse grupo serão movidos para uma pasta de revisão, sem serem apagados.",
                 wraplength=850, justify="left", bg="#0D0B14", fg="#B8B2C9").pack(anchor="w", padx=16, pady=(0, 12))

        frame = tk.Frame(window, bg="#171421", highlightbackground="#30283F", highlightthickness=1)
        frame.pack(fill="both", expand=True, padx=16, pady=4)
        tree = ttk.Treeview(frame, columns=("size", "path"), show="tree headings", selectmode="browse", style="Dark.Treeview")
        tree.heading("#0", text="Grupo / arquivo")
        tree.heading("size", text="Tamanho")
        tree.heading("path", text="Caminho")
        tree.column("#0", width=210)
        tree.column("size", width=100, anchor="e")
        tree.column("path", width=470)
        scroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        # Mapeia os grupos e arquivos da tabela aos caminhos reais no disco.
        group_map = {}
        file_map = {}
        for number, paths in enumerate(groups, 1):
            group_id = tree.insert("", "end", text=f"Grupo {number} ({len(paths)} arquivos)", values=("", ""))
            group_map[group_id] = paths
            for path in paths:
                try:
                    size = self.format_size(os.path.getsize(path))
                except OSError:
                    size = "Indisponível"
                iid = tree.insert(group_id, "end", text=os.path.basename(path),
                                  values=(size, os.path.relpath(path, directory)))
                file_map[iid] = (group_id, path)
            tree.item(group_id, open=True)

        # Mantém uma cópia escolhida e move as demais para a pasta de revisão.
        def keep_selected():
            selected = tree.selection()
            if not selected or selected[0] not in file_map:
                messagebox.showwarning("Seleção necessária", "Selecione um arquivo dentro de um grupo para indicar qual deseja manter.", parent=window)
                return
            group_id, keep_path = file_map[selected[0]]
            paths = group_map[group_id]
            to_move = [path for path in paths if os.path.abspath(path) != os.path.abspath(keep_path)]
            if not to_move:
                return
            if not messagebox.askyesno("Confirmar", f"Manter '{os.path.basename(keep_path)}' e mover {len(to_move)} cópia(s) para '_Duplicados_para_revisar'? Os arquivos não serão apagados.", parent=window):
                return
            # Cria uma pasta de revisão: as cópias são preservadas, não apagadas.
            review_root = os.path.join(directory, "_Duplicados_para_revisar")
            moved = 0
            duplicate_moves = []
            for path in to_move:
                try:
                    relative = os.path.relpath(path, directory)
                    destination = os.path.join(review_root, relative)
                    os.makedirs(os.path.dirname(destination), exist_ok=True)
                    destination = generate_unique_path(destination)
                    # Registra origem e destino antes de atualizar o histórico.
                    shutil.move(path, destination)
                    duplicate_moves.append({"original": path, "destination": destination})
                    moved += 1
                    self.add_log(f"Duplicado separado: {relative} → {os.path.relpath(destination, directory)}")
                except (OSError, shutil.Error) as error:
                    self.add_log(f"Erro ao separar duplicado {path}: {error}")
            if duplicate_moves:
                # Registra os duplicados movidos para que o botão Desfazer possa restaurá-los.
                save_history(load_history(directory) + duplicate_moves, directory)
            messagebox.showinfo("Concluído", f"{moved} arquivo(s) movido(s) para a pasta de revisão.", parent=window)
            window.destroy()
            self.show_preview()

        buttons = tk.Frame(window, bg="#0D0B14")
        buttons.pack(fill="x", padx=16, pady=14)
        tk.Button(buttons, text="Manter selecionado e separar cópias", command=keep_selected, bg="#7C3AED", activebackground="#8B5CF6", fg="white", activeforeground="white", relief="flat", bd=0, padx=16, pady=9, cursor="hand2", font=("Segoe UI", 9, "bold")).pack(side="left")
        tk.Button(buttons, text="Fechar", command=window.destroy, bg="#272235", activebackground="#383047", fg="#E9E3F5", activeforeground="white", relief="flat", bd=0, padx=16, pady=9, cursor="hand2", font=("Segoe UI", 9)).pack(side="right")
        if not groups:
            tk.Label(window, text="Nenhum arquivo duplicado foi encontrado.", bg="#0D0B14", fg="#B8B2C9").pack(pady=8)
        self.add_log(f"Grupos de duplicados encontrados: {len(groups)}")

    # Solicita confirmação antes de mover os arquivos de verdade.
    def start_organization(self):
        directory = self.folder_entry.get().strip()
        if not directory:
            messagebox.showwarning("Atenção", "Selecione uma pasta primeiro.")
            return
        if not os.path.isdir(directory):
            messagebox.showerror("Erro", "A pasta selecionada não existe ou não pode ser acessada.")
            return
        # Exige confirmação porque a próxima etapa realmente move arquivos.
        confirmation = messagebox.askyesno("Confirmar organização", "Deseja organizar os arquivos desta pasta?")
        if not confirmation:
            return

        self.add_log("=== INICIANDO ORGANIZAÇÃO ===")
        try:
            moved_count, _ = organize_files(directory, self.add_log)
            self.add_log(f"=== ORGANIZAÇÃO CONCLUÍDA: {moved_count} arquivo(s) movido(s) ===")
            self.show_preview()
            messagebox.showinfo("Organização concluída", f"{moved_count} arquivo(s) foram organizados.")
        except Exception as error:
            self.add_log(f"Erro: {error}")
            messagebox.showerror("Erro", str(error))

    # Solicita confirmação e chama a rotina que restaura a organização anterior.
    def undo_organization(self):
        if not messagebox.askyesno("Desfazer operações", "Deseja desfazer as operações registradas no histórico desta pasta?"):
            return
        self.add_log("=== DESFAZENDO ORGANIZAÇÃO ===")
        directory = self.folder_entry.get().strip()
        if not directory or not os.path.isdir(directory):
            messagebox.showwarning("Atenção", "Selecione uma pasta válida primeiro.")
            return
        # Executa a restauração e recebe o resultado e uma mensagem para o usuário.
        success, message = undo_last_organization(directory, self.add_log)
        self.add_log(message)
        if success:
            messagebox.showinfo("Desfazer operações", message)
            self.show_preview()
        else:
            messagebox.showwarning("Desfazer operações", message)


# Ponto de entrada: cria a janela principal e inicia o ciclo de eventos do Tkinter.
if __name__ == "__main__":
    # Cria a janela principal do Tkinter.
    root = tk.Tk()
    # Instancia o aplicativo, que constrói a interface e conecta os botões.
    app = FileOrganizerApp(root)
    # Mantém a janela aberta e processa cliques, teclas e outros eventos.
    root.mainloop()
