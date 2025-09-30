# 🗂️ Organizador de Arquivos em Python

Este é um **projeto prático em Python** que organiza automaticamente arquivos dentro de uma pasta, separando-os em categorias como **Imagens, Documentos, Áudios, Vídeos, Compactados**, entre outras.  

---

## 📌 Funcionalidades

- Identifica arquivos pela extensão.  
- Cria automaticamente pastas para cada categoria.  
- Move os arquivos para suas respectivas pastas.  
- Mantém os arquivos mais organizados de forma simples e rápida.  

---

## 📂 Categorias Suportadas

- **Imagens**: `.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp`, `.svg`  
- **Documentos**: `.pdf`, `.doc`, `.docx`, `.txt`, `.odt`, `.rtf`  
- **Planilhas**: `.xls`, `.xlsx`, `.ods`, `.csv`  
- **Apresentações**: `.ppt`, `.pptx`, `.odp`  
- **Áudios**: `.mp3`, `.wav`, `.aac`, `.ogg`  
- **Vídeos**: `.mp4`, `.avi`, `.mov`, `.mkv`, `.wmv`  
- **Compactados**: `.zip`, `.rar`, `.tar`, `.gz`, `.7z`  
- **Executáveis**: `.exe`, `.msi`, `.sh`, `.bat`, `.apk`  
- **Códigos**: `.py`, `.c`, `.cpp`, `.java`, `.js`, `.html`, `.css`, `.php`  
- **Outros**: qualquer extensão não listada acima.  

---

## 🚀 Como Executar

1. Certifique-se de ter o **Python 3** instalado.  
2. Baixe ou copie o arquivo _`organizer.py`._  
3. Abra o terminal e vá até a pasta onde está o script.  
4. Execute o comando: _```bash```
   ```python organizer.py```_
5. Digite o caminho da pasta que você deseja organizar.
6. Pronto! Seus arquivos estarão organizados automaticamente. ✅

---

## 💡 Exemplo de Uso

Suponha que você tenha uma pasta chamada Downloads cheia de arquivos.
Ao rodar o script e informar o caminho dela, será criada uma estrutura assim:

### Downloads
│
├── Imagens/
│   ├── foto.jpg
│   └── desenho.png
│
├── Documentos/
│   ├── contrato.pdf
│   └── resumo.docx
│
├── Vídeos/
│   └── filme.mp4
│
├── Outros/
│   └── arquivo.desconhecido

---

```bash```
   ```python organizer.py```

   ## 📜 Licença

Este projeto está sob a licença MIT.
Você pode usar, modificar e distribuir livremente.

✨ Projeto simples e útil para organizar arquivos automaticamente!


