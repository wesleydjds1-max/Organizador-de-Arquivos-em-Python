
# 🌍 Super Trunfo de Países (Projeto em C)

Este projeto foi desenvolvido como desafio acadêmico para praticar a linguagem C.  
Ele implementa um sistema de **cadastro de cartas do jogo Super Trunfo**, com o tema **Países**.

Cada carta contém:
- Estado
- Código
- Nome da cidade
- População
- PIB
- Área
- Número de pontos turísticos
- **Densidade populacional** (calculada automaticamente)
- **PIB per capita** (calculado automaticamente)

## 🎯 Objetivos do Projeto
- Implementar um programa em C para cadastrar cartas.
- Aplicar **operadores matemáticos** para cálculos de atributos derivados.
- Utilizar **entrada e saída de dados** em C.
- Fixar os conceitos de **variáveis, operadores e funções**.

## 🚀 Como executar o projeto

1. **Clone o repositório (ou baixe os arquivos):**
   ```bash
   git clone https://github.com/seu-usuario/seu-repositorio.git
   cd seu-repositorio
   ```

2. **Compile o programa em C:**
   - Linux/macOS:
     ```bash
     gcc main.c -o super_trunfo
     ```
   - Windows (usando MinGW ou outro compilador):
     ```bash
     gcc main.c -o super_trunfo.exe
     ```

3. **Execute o programa:**
   - Linux/macOS:
     ```bash
     ./super_trunfo
     ```
   - Windows:
     ```bash
     super_trunfo.exe
     ```

## 🖼️ Exemplo de uso

```
Quantas cartas deseja cadastrar? 2

--- Cadastro da carta 1 ---
Digite o Estado: RJ
Digite o Código: A01
Digite o Nome da Cidade: Rio de Janeiro
Digite a População: 6000000
Digite o PIB (em bilhões): 400
Digite a Área (km²): 1200
Digite o Número de Pontos Turísticos: 20

--- Cadastro da carta 2 ---
Digite o Estado: SP
Digite o Código: B02
Digite o Nome da Cidade: São Paulo
Digite a População: 12000000
Digite o PIB (em bilhões): 800
Digite a Área (km²): 1520
Digite o Número de Pontos Turísticos: 30

===== Cartas Cadastradas =====
Estado: RJ | Código: A01 | Cidade: Rio de Janeiro
População: 6000000 | PIB: 400.00 bilhões | Área: 1200.00 km² | Pontos turísticos: 20
Densidade Populacional: 5000.00 hab/km² | PIB per Capita: 66666.67

Estado: SP | Código: B02 | Cidade: São Paulo
População: 12000000 | PIB: 800.00 bilhões | Área: 1520.00 km² | Pontos turísticos: 30
Densidade Populacional: 7894.74 hab/km² | PIB per Capita: 66666.67
```
