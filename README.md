# Painel "Indicadores do Projeto" (Flask)

Réplica web, em Python, do relatório Power BI do projeto ColaboraGov/ColaboraLab,
alimentada diretamente pela planilha `Entregas_DTI.xlsx`.

## Como executar

```bash
pip install -r requirements.txt
python app.py
# abrir http://127.0.0.1:5000
```

## De onde vêm os dados

O painel baixa a planilha pelo link do SharePoint definido em `LINK_PLANILHA`
(em `app.py`), no máximo a cada 5 minutos, e guarda a cópia em `dados/Entregas_DTI.xlsx`.
Se o link falhar (sem internet, link exigindo login etc.), continua usando essa cópia
local e mostra o aviso "usando cópia local" no cabeçalho.

- **Testar o link:** `python testar_link.py`
- **Buscar na hora:** passe o mouse sobre o cabeçalho e clique em **Buscar dados agora**.
- **Mudar o intervalo:** variável de ambiente `INTERVALO` (segundos).
- **Usar só o arquivo local:** deixe `LINK_PLANILHA = ""` em `app.py`. Nesse modo o
  painel relê o arquivo quando ele muda e o cabeçalho mostra **Atualizar planilha**
  para enviar uma nova versão.

## Páginas

| Rota          | Página                  | Fonte na planilha                         |
|---------------|-------------------------|-------------------------------------------|
| `/`           | Visão Geral             | Entregas, Frentes, Atividades, Oficinas   |
| `/oficinas`   | Oficinas Colaborativas  | Oficinas, Entregas_por_Oficinas           |
| `/atividades` | Entregas por Atividades | Entregas, Atividades                      |
| `/reacao`     | Avaliação de Reação     | Avaliacao_Reacao                          |
| `/impacto`    | Avaliação de Impacto    | Avaliacao_Impacto                         |
| `/api/dados`  | JSON com todos os dados | —                                         |

As segmentações (caixas de seleção) filtram cartões, gráficos e tabelas da página.
Na página de atividades, clicar numa barra também seleciona a atividade.
Tabelas podem ser ordenadas clicando no cabeçalho.

## Logotipos

Coloque os arquivos em `static/img/` com estes nomes para substituir os textos do rodapé:
`colaboragov.png`, `colaboralab.png`, `itrac.png`, `unb.png`.

## Estrutura

```
app.py              rotas Flask e upload da planilha
dados.py            leitura do .xlsx, normalização e nuvem de palavras
templates/          base (cabeçalho, menu, rodapé) + uma página por tela
static/css/         estilo do painel
static/js/painel.js funções de gráficos, segmentações e tabelas
static/vendor/      Plotly.js e wordcloud2.js (funciona sem internet)
```
