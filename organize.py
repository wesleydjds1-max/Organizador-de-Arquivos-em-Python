import os
import shutil
import json
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext


# ============================================================
# CONFIGURAÇÕES
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


HISTORY_FILE = "historico_organizacao.json"


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def get_category(extension):
    """
    Retorna a categoria correspondente à extensão.
    Caso não encontre, retorna 'Outros'.
    """

    for category, extensions in CATEGORIES.items():

        if extension in extensions:
            return category

    return "Outros"


def generate_unique_path(destination):
    """
    Gera um novo caminho caso já exista um arquivo
    com o mesmo nome no destino.

    Exemplo:

    foto.jpg
    foto (1).jpg
    foto (2).jpg
    """

    if not os.path.exists(destination):
        return destination

    folder = os.path.dirname(destination)
    filename = os.path.basename(destination)

    name, extension = os.path.splitext(filename)

    counter = 1

    while True:

        new_filename = f"{name} ({counter}){extension}"

        new_destination = os.path.join(
            folder,
            new_filename
        )

        if not os.path.exists(new_destination):
            return new_destination

        counter += 1


def save_history(history):
    """
    Salva o histórico da organização em um arquivo JSON.
    """

    try:

        with open(
            HISTORY_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                history,
                file,
                indent=4,
                ensure_ascii=False
            )

    except OSError as error:

        print(
            f"Erro ao salvar histórico: {error}"
        )


def load_history():
    """
    Carrega o histórico salvo.
    """

    if not os.path.exists(HISTORY_FILE):
        return []

    try:

        with open(
            HISTORY_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except (
        OSError,
        json.JSONDecodeError
    ):

        return []


# ============================================================
# PRÉ-VISUALIZAÇÃO
# ============================================================

def preview_files(directory):
    """
    Analisa os arquivos da pasta sem movê-los.

    Retorna uma lista contendo:
    nome do arquivo,
    categoria
    e destino previsto.
    """

    if not os.path.isdir(directory):

        raise FileNotFoundError(
            "O diretório informado não existe."
        )

    preview = []

    try:

        items = os.listdir(directory)

    except OSError as error:

        raise OSError(
            f"Não foi possível acessar a pasta:\n{error}"
        )

    for filename in items:

        file_path = os.path.join(
            directory,
            filename
        )

        # Ignorar diretórios
        if os.path.isdir(file_path):
            continue

        # Descobrir extensão
        _, extension = os.path.splitext(
            filename
        )

        extension = extension.lower()

        # Descobrir categoria
        category = get_category(
            extension
        )

        # Definir pasta de destino
        category_folder = os.path.join(
            directory,
            category
        )

        # Definir destino do arquivo
        destination = os.path.join(
            category_folder,
            filename
        )

        # Evitar conflitos
        destination = generate_unique_path(
            destination
        )

        preview.append({
            "filename": filename,
            "category": category,
            "destination": destination
        })

    return preview


# ============================================================
# ORGANIZAÇÃO
# ============================================================

def organize_files(directory, log_callback):
    """
    Organiza os arquivos da pasta.

    Retorna:
    quantidade de arquivos movidos
    histórico das movimentações
    """

    if not os.path.isdir(directory):

        raise FileNotFoundError(
            "O diretório informado não existe."
        )

    moved_files = []
    moved_count = 0

    try:

        items = os.listdir(directory)

    except OSError as error:

        raise OSError(
            f"Não foi possível acessar a pasta:\n{error}"
        )

    for filename in items:

        file_path = os.path.join(
            directory,
            filename
        )

        # Ignorar diretórios
        if os.path.isdir(file_path):
            continue

        # Descobrir extensão
        _, extension = os.path.splitext(
            filename
        )

        extension = extension.lower()

        # Descobrir categoria
        category = get_category(
            extension
        )

        # Criar pasta da categoria
        category_folder = os.path.join(
            directory,
            category
        )

        os.makedirs(
            category_folder,
            exist_ok=True
        )

        # Definir destino
        destination = os.path.join(
            category_folder,
            filename
        )

        # Evitar conflito
        destination = generate_unique_path(
            destination
        )

        try:

            shutil.move(
                file_path,
                destination
            )

            moved_files.append({
                "original": file_path,
                "destination": destination
            })

            moved_count += 1

            new_filename = os.path.basename(
                destination
            )

            if new_filename == filename:

                log_callback(
                    f"✓ {filename} → {category}"
                )

            else:

                log_callback(
                    f"✓ {filename} → "
                    f"{category}/{new_filename}"
                )

        except OSError as error:

            log_callback(
                f"✗ Erro ao mover "
                f"{filename}: {error}"
            )

    # Salvar histórico
    if moved_files:
        save_history(moved_files)

    return moved_count, moved_files


# ============================================================
# DESFAZER
# ============================================================

def undo_last_organization(log_callback):
    """
    Desfaz a última organização registrada.
    """

    history = load_history()

    if not history:

        return (
            False,
            "Nenhuma organização para desfazer."
        )

    restored_count = 0

    for operation in reversed(history):

        original = operation["original"]
        destination = operation["destination"]

        # Verificar se o arquivo ainda existe
        if not os.path.exists(destination):

            log_callback(
                f"✗ Arquivo não encontrado: "
                f"{destination}"
            )

            continue

        try:

            # Não sobrescrever um arquivo existente
            if os.path.exists(original):

                log_callback(
                    f"✗ Não foi possível restaurar: "
                    f"{os.path.basename(original)}"
                )

                continue

            shutil.move(
                destination,
                original
            )

            restored_count += 1

            log_callback(
                f"↩ Restaurado: "
                f"{os.path.basename(original)}"
            )

        except OSError as error:

            log_callback(
                f"✗ Erro ao restaurar arquivo: "
                f"{error}"
            )

    # Limpar histórico
    try:

        if os.path.exists(HISTORY_FILE):
            os.remove(HISTORY_FILE)

    except OSError:
        pass

    return (
        True,
        f"{restored_count} arquivo(s) restaurado(s)."
    )


# ============================================================
# INTERFACE GRÁFICA
# ============================================================

class FileOrganizerApp:

    def __init__(self, root):

        self.root = root

        self.root.title(
            "Organizador de Arquivos"
        )

        self.root.geometry(
            "760x560"
        )

        self.root.minsize(
            680,
            480
        )

        self.selected_directory = ""

        self.create_interface()


    # --------------------------------------------------------
    # CRIAR INTERFACE
    # --------------------------------------------------------

    def create_interface(self):

        # Título
        title = tk.Label(
            self.root,
            text="Organizador de Arquivos",
            font=("Segoe UI", 22, "bold")
        )

        title.pack(
            pady=(20, 5)
        )


        # Subtítulo
        subtitle = tk.Label(
            self.root,
            text=(
                "Organize seus arquivos "
                "automaticamente por categoria."
            ),
            font=("Segoe UI", 10)
        )

        subtitle.pack(
            pady=(0, 20)
        )


        # ----------------------------------------------------
        # SELEÇÃO DE PASTA
        # ----------------------------------------------------

        folder_frame = tk.Frame(
            self.root
        )

        folder_frame.pack(
            fill="x",
            padx=30
        )


        self.folder_entry = tk.Entry(
            folder_frame,
            font=("Segoe UI", 10)
        )

        self.folder_entry.pack(
            side="left",
            fill="x",
            expand=True,
            ipady=7
        )


        select_button = tk.Button(
            folder_frame,
            text="Escolher pasta",
            command=self.select_folder,
            font=("Segoe UI", 10),
            padx=10
        )

        select_button.pack(
            side="left",
            padx=(10, 0),
            ipady=2
        )


        # ----------------------------------------------------
        # BOTÕES
        # ----------------------------------------------------

        button_frame = tk.Frame(
            self.root
        )

        button_frame.pack(
            pady=15
        )


        preview_button = tk.Button(
            button_frame,
            text="Pré-visualizar",
            command=self.show_preview,
            font=("Segoe UI", 10),
            padx=15,
            pady=8
        )

        preview_button.pack(
            side="left",
            padx=5
        )


        organize_button = tk.Button(
            button_frame,
            text="Organizar arquivos",
            command=self.start_organization,
            font=("Segoe UI", 10, "bold"),
            padx=15,
            pady=8
        )

        organize_button.pack(
            side="left",
            padx=5
        )


        undo_button = tk.Button(
            button_frame,
            text="Desfazer",
            command=self.undo_organization,
            font=("Segoe UI", 10),
            padx=15,
            pady=8
        )

        undo_button.pack(
            side="left",
            padx=5
        )


        # ----------------------------------------------------
        # RELATÓRIO
        # ----------------------------------------------------

        log_label = tk.Label(
            self.root,
            text="Relatório:",
            font=("Segoe UI", 11, "bold")
        )

        log_label.pack(
            anchor="w",
            padx=30,
            pady=(5, 5)
        )


        self.log_text = scrolledtext.ScrolledText(
            self.root,
            height=18,
            font=("Consolas", 9),
            state="disabled"
        )

        self.log_text.pack(
            fill="both",
            expand=True,
            padx=30,
            pady=(0, 20)
        )


    # --------------------------------------------------------
    # SELECIONAR PASTA
    # --------------------------------------------------------

    def select_folder(self):

        directory = filedialog.askdirectory(
            title="Selecione a pasta que deseja organizar"
        )

        if directory:

            self.selected_directory = directory

            self.folder_entry.delete(
                0,
                tk.END
            )

            self.folder_entry.insert(
                0,
                directory
            )

            self.add_log(
                f"Pasta selecionada: {directory}"
            )


    # --------------------------------------------------------
    # ADICIONAR MENSAGEM AO RELATÓRIO
    # --------------------------------------------------------

    def add_log(self, message):

        self.log_text.config(
            state="normal"
        )

        self.log_text.insert(
            tk.END,
            message + "\n"
        )

        self.log_text.see(
            tk.END
        )

        self.log_text.config(
            state="disabled"
        )


    # --------------------------------------------------------
    # PRÉ-VISUALIZAÇÃO
    # --------------------------------------------------------

    def show_preview(self):

        directory = self.folder_entry.get().strip()

        if not directory:

            messagebox.showwarning(
                "Atenção",
                "Selecione uma pasta primeiro."
            )

            return


        try:

            preview = preview_files(
                directory
            )

            self.add_log("")
            self.add_log(
                "=== PRÉ-VISUALIZAÇÃO ==="
            )


            if not preview:

                self.add_log(
                    "Nenhum arquivo encontrado."
                )

                return


            for item in preview:

                filename = item["filename"]
                category = item["category"]

                destination = item["destination"]

                destination_name = os.path.basename(
                    destination
                )

                if destination_name == filename:

                    self.add_log(
                        f"{filename} → {category}"
                    )

                else:

                    self.add_log(
                        f"{filename} → "
                        f"{category}/{destination_name}"
                    )


            self.add_log("")

            self.add_log(
                f"{len(preview)} arquivo(s) "
                "serão organizados."
            )


        except Exception as error:

            messagebox.showerror(
                "Erro",
                str(error)
            )


    # --------------------------------------------------------
    # ORGANIZAR
    # --------------------------------------------------------

    def start_organization(self):

        directory = self.folder_entry.get().strip()

        if not directory:

            messagebox.showwarning(
                "Atenção",
                "Selecione uma pasta primeiro."
            )

            return


        if not os.path.isdir(directory):

            messagebox.showerror(
                "Erro",
                "A pasta selecionada não existe."
            )

            return


        confirmation = messagebox.askyesno(
            "Confirmar organização",
            (
                "Deseja organizar os arquivos "
                "desta pasta?"
            )
        )

        if not confirmation:
            return


        self.add_log("")
        self.add_log(
            "=== INICIANDO ORGANIZAÇÃO ==="
        )


        try:

            moved_count, _ = organize_files(
                directory,
                self.add_log
            )

            self.add_log("")

            self.add_log(
                f"=== ORGANIZAÇÃO CONCLUÍDA ==="
            )

            self.add_log(
                f"{moved_count} arquivo(s) "
                "movido(s)."
            )


            messagebox.showinfo(
                "Organização concluída",
                (
                    f"{moved_count} arquivo(s) "
                    "foram organizados."
                )
            )


        except Exception as error:

            self.add_log(
                f"✗ Erro: {error}"
            )

            messagebox.showerror(
                "Erro",
                str(error)
            )


    # --------------------------------------------------------
    # DESFAZER
    # --------------------------------------------------------

    def undo_organization(self):

        confirmation = messagebox.askyesno(
            "Desfazer organização",
            (
                "Deseja desfazer a última "
                "organização?"
            )
        )

        if not confirmation:
            return


        self.add_log("")
        self.add_log(
            "=== DESFAZENDO ORGANIZAÇÃO ==="
        )


        success, message = undo_last_organization(
            self.add_log
        )


        self.add_log(message)


        if success:

            messagebox.showinfo(
                "Desfazer",
                message
            )

        else:

            messagebox.showwarning(
                "Desfazer",
                message
            )


# ============================================================
# INICIALIZAÇÃO DO PROGRAMA
# ============================================================

if __name__ == "__main__":

    root = tk.Tk()

    app = FileOrganizerApp(
        root
    )

    root.mainloop()
