
#include <stdio.h>
#include <string.h>

#define MAX_CARTAS 100

typedef struct {
    char estado[50];
    char codigo[10];
    char nomeCidade[100];
    int populacao;
    float pib; // em bilhões
    float area; // km²
    int pontosTuristicos;
    float densidadePopulacional;
    float pibPerCapita;
} Carta;

int main() {
    int n;
    Carta cartas[MAX_CARTAS];

    printf("Quantas cartas deseja cadastrar? ");
    scanf("%d", &n);
    getchar(); // limpar buffer

    for (int i = 0; i < n; i++) {
        printf("\n--- Cadastro da carta %d ---\n", i + 1);

        printf("Digite o Estado: ");
        fgets(cartas[i].estado, sizeof(cartas[i].estado), stdin);
        cartas[i].estado[strcspn(cartas[i].estado, "\n")] = 0;

        printf("Digite o Código: ");
        fgets(cartas[i].codigo, sizeof(cartas[i].codigo), stdin);
        cartas[i].codigo[strcspn(cartas[i].codigo, "\n")] = 0;

        printf("Digite o Nome da Cidade: ");
        fgets(cartas[i].nomeCidade, sizeof(cartas[i].nomeCidade), stdin);
        cartas[i].nomeCidade[strcspn(cartas[i].nomeCidade, "\n")] = 0;

        printf("Digite a População: ");
        scanf("%d", &cartas[i].populacao);

        printf("Digite o PIB (em bilhões): ");
        scanf("%f", &cartas[i].pib);

        printf("Digite a Área (km²): ");
        scanf("%f", &cartas[i].area);

        printf("Digite o Número de Pontos Turísticos: ");
        scanf("%d", &cartas[i].pontosTuristicos);

        getchar(); // limpar buffer

        // cálculos
        cartas[i].densidadePopulacional = cartas[i].populacao / cartas[i].area;
        cartas[i].pibPerCapita = (cartas[i].pib * 1000000000.0) / cartas[i].populacao;
    }

    printf("\n===== Cartas Cadastradas =====\n");
    for (int i = 0; i < n; i++) {
        printf("Estado: %s | Código: %s | Cidade: %s\n", cartas[i].estado, cartas[i].codigo, cartas[i].nomeCidade);
        printf("População: %d | PIB: %.2f bilhões | Área: %.2f km² | Pontos turísticos: %d\n",
               cartas[i].populacao, cartas[i].pib, cartas[i].area, cartas[i].pontosTuristicos);
        printf("Densidade Populacional: %.2f hab/km² | PIB per Capita: %.2f\n\n",
               cartas[i].densidadePopulacional, cartas[i].pibPerCapita);
    }

    return 0;
}
