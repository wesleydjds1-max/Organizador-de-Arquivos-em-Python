import os
import shutil

# Definição das categorias e extensões correspondentes
CATEGORIES = {
    "Imagens": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg"],
    "Documentos": [".pdf", ".doc", ".docx", ".txt", ".odt", ".rtf"],
    "Planilhas": [".xls", ".xlsx", ".ods", ".csv"],
    "Apresentações": [".ppt", ".pptx", ".odp"],
    "Áudios": [".mp3", ".wav", ".aac", ".ogg"],
    "Vídeos": [".mp4", ".avi", ".mov", ".mkv", ".wmv"],
    "Compactados": [".zip", ".rar", ".tar", ".gz", ".7z"],
    "Executáveis": [".exe", ".msi", ".sh", ".bat", ".apk"],
    "Códigos": [".py", ".c", ".cpp", ".java", ".js", ".html", ".css", ".php"],
    "Outros": []
}

def organize_files(directory):
    """
    Organiza os arquivos em pastas de acordo com sua extensão.
    """
    if not os.path.isdir(directory):
        print("O diretório informado não existe.")
        return

    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)

        # Ignorar diretórios
        if os.path.isdir(file_path):
            continue

        # Identificar a extensão do arquivo
        _, extension = os.path.splitext(filename)
        extension = extension.lower()

        # Encontrar a categoria do arquivo
        moved = False
        for category, extensions in CATEGORIES.items():
            if extension in extensions:
                category_folder = os.path.join(directory, category)
                os.makedirs(category_folder, exist_ok=True)
                shutil.move(file_path, os.path.join(category_folder, filename))
                print(f"Movido: {filename} → {category}")
                moved = True
                break

        # Caso não se encaixe em nenhuma categoria
        if not moved:
            other_folder = os.path.join(directory, "Outros")
            os.makedirs(other_folder, exist_ok=True)
            shutil.move(file_path, os.path.join(other_folder, filename))
            print(f"Movido: {filename} → Outros")

if __name__ == "__main__":
    print("=== Organizador de Arquivos ===")
    target_dir = input("Digite o caminho da pasta a ser organizada: ").strip()
    organize_files(target_dir)
    print("Organização concluída! ✅")
