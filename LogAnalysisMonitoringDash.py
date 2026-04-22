import os
import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output
from dash import dash_table

DIRETORIO_LOGS = "DIRETORIO_RAIZ_DOS_LOGS"
LINHAS_CONTEXTO = 2

TIPOS_ERRO = {
    "Gson": ["ERROR GsonMapperUtil"],
    "CSV": ["ERROR CsvMapperUtil"],
    "Groovy": ["ERROR AbstractGroovyObject"],
    "Spring": ["ERROR DefaultErrorHandler"],
    "JMS": ["Setup of JMS message listener invoker failed for destination"],
    "CAMEL": ["exception CamelExceptionCaught"],
    "HTTP_400": ["Codigo de status HTTP 400"],
    "ORACLE": ["ORA-", "error code [1000]; ORA-"],
    "WARN": ["WARN"],
    "ERROR": ["ERROR:"]
}

ARQUIVO_SAIDA = "erros_encontrados.txt"

def identificar_tipo(linha):
    import re

    linha_lower = linha.lower()

    for tipo, padroes in TIPOS_ERRO.items():
        for p in padroes:

            if p.lower() in linha_lower:

                if tipo == "WARN":

                    # ignorar se tiver payload (pipes)
                    if "|" in linha:
                        return None

                    # ignorar se estiver dentro de palavras (ex: Twarn3, WARN123)
                    if re.search(r"\w+warn\w+", linha_lower):
                        return None

                    # só aceita WARN como palavra isolada
                    if not re.search(r"\bwarn\b", linha_lower):
                        return None

                return tipo

    return None


# REGRA DO SISTEMA
def identificar_sistema(caminho_arquivo):
    nome_arquivo = os.path.basename(caminho_arquivo).lower()

    # apenas classifica, NÃO altera nome do arquivo
    if "olapp.log" in nome_arquivo or "ol.log" in nome_arquivo:
        return "BOSS"
    else:
        return "ODE"


def processar_logs_dataframe():
    registros = []

    with open(ARQUIVO_SAIDA, "w", encoding="utf-8") as saida:

        for root, dirs, files in os.walk(DIRETORIO_LOGS):
            for file in files:
                caminho_arquivo = os.path.join(root, file)

                try:
                    with open(caminho_arquivo, "r", encoding="utf-8", errors="ignore") as f:
                        linhas = f.readlines()

                        i = 0
                        while i < len(linhas):
                            linha = linhas[i]
                            tipo = identificar_tipo(linha)

                            if tipo:
                                sistema = identificar_sistema(caminho_arquivo)

                                registros.append({
                                    "arquivo": caminho_arquivo,  # caminho completo
                                    "tipo": tipo,
                                    "sistema": sistema,
                                    "linha_num": i + 1,
                                    "mensagem": linha.strip()
                                })

                                saida.write(f"\n===== ARQUIVO: {caminho_arquivo} =====\n")
                                saida.write(f"Tipo: {tipo} | Sistema: {sistema}\n")
                                saida.write(f"Linha {i+1}: {linha}")

                                for j in range(1, LINHAS_CONTEXTO + 1):
                                    if i + j < len(linhas):
                                        saida.write(linhas[i + j])

                                saida.write("\n" + "="*80 + "\n")

                                i += LINHAS_CONTEXTO
                            i += 1

                except Exception as e:
                    print(f"Erro ao processar {caminho_arquivo}: {e}")

    return pd.DataFrame(registros)


# execução
df = processar_logs_dataframe()

print("Total de erros encontrados:", len(df))
print(f"Arquivo gerado: {ARQUIVO_SAIDA}")


#########################################################################################
# CRIAÇÃO DASHBOARD

AZUL = "#003A8F"
LARANJA = "#F39200"
FUNDO = "#1e1e1e"
TEXTO = "#FFFFFF"

LINHAS_CONTEXTO = 20
TAMANHO_MAX_ARQUIVO = 500_000_000

# ---------------- PREPARAÇÃO ----------------
df["arquivo_nome"] = df["arquivo"].apply(lambda x: os.path.basename(x))
df["diretorio"] = df["arquivo"].apply(lambda x: os.path.dirname(x))

lista_diretorios = sorted(df["diretorio"].unique())
lista_sistemas = sorted(df["sistema"].unique())

app = Dash(__name__)

app.layout = html.Div(style={
    "backgroundColor": FUNDO,
    "color": TEXTO,
    "padding": "20px",
    "width": "100%",
    "minHeight": "100vh"
}, children=[

    html.H1("DashBoard Logs ODE e BOSS", style={"textAlign": "center"}),

    # 🔍 FILTROS
    html.Div([
        dcc.Dropdown(
            id="filtro_diretorio",
            options=[{"label": d, "value": d} for d in lista_diretorios],
            placeholder="Filtrar por diretório",
            multi=True,
            style={"width": "48%"}
        ),

        dcc.Dropdown(
            id="filtro_sistema",
            options=[{"label": s, "value": s} for s in lista_sistemas],
            placeholder="Filtrar por sistema (ODE/BOSS)",
            multi=True,
            style={"width": "48%"}
        )
    ], style={"display": "flex", "gap": "10px", "marginBottom": "20px"}),

    #GRÁFICOS
    html.Div([
        dcc.Graph(id="grafico_tipo", style={"flex": "1"}),
        dcc.Graph(id="grafico_pizza", style={"flex": "1"})
    ], style={"display": "flex", "gap": "20px"}),

    html.H3("Buscar erro"),

    dcc.Input(
        id="busca",
        type="text",
        placeholder="Digite parte do erro...",
        style={
            "width": "100%",
            "maxWidth": "500px",
            "padding": "8px",
            "backgroundColor": "#2b2b2b",
            "color": "#FFFFFF",
            "border": "1px solid #555",
            "borderRadius": "6px"
        }
    ),

    html.H3("Detalhes dos Erros"),

    dash_table.DataTable(
        id="tabela",
        columns=[
            {"name": "Sistema", "id": "sistema"},
            {"name": "Diretório", "id": "diretorio"},
            {"name": "Arquivo", "id": "arquivo_nome"},
            {"name": "Tipo", "id": "tipo"},
            {"name": "Linha", "id": "linha_num"},
            {"name": "Mensagem", "id": "mensagem"}
        ],
        page_size=10,
        style_table={"overflowX": "auto"},
        style_cell={
            "backgroundColor": FUNDO,
            "color": TEXTO,
            "fontSize": "12px",
            "whiteSpace": "normal",
            "height": "auto",
            "maxWidth": "400px"
        },
        style_header={
            "backgroundColor": AZUL_CAIXA,
            "color": "white",
            "fontWeight": "bold"
        },
        row_selectable="single"
    ),

    html.H3("Detalhe do Log"),

    html.Div(id="detalhe_log")
])

# ---------------- CALLBACK PRINCIPAL ----------------
@app.callback(
    Output("tabela", "data"),
    Output("grafico_tipo", "figure"),
    Output("grafico_pizza", "figure"),
    Input("busca", "value"),
    Input("filtro_diretorio", "value"),
    Input("filtro_sistema", "value"),
    Input("grafico_tipo", "clickData"),
    Input("grafico_pizza", "clickData"),
)
def atualizar_tela(busca, diretorios, sistemas, click_barra, click_pizza):

    df_filtrado = df.copy()

    # 🔍 filtros padrão
    if diretorios:
        df_filtrado = df_filtrado[df_filtrado["diretorio"].isin(diretorios)]

    if sistemas:
        df_filtrado = df_filtrado[df_filtrado["sistema"].isin(sistemas)]

    if busca:
        df_filtrado = df_filtrado[
            df_filtrado["mensagem"].str.contains(busca, case=False, na=False)
        ]

    # FILTRO POR CLIQUE NO GRÁFICO
    tipo_selecionado = None

    if click_barra:
        tipo_selecionado = click_barra["points"][0]["x"]

    elif click_pizza:
        tipo_selecionado = click_pizza["points"][0]["label"]

    if tipo_selecionado:
        df_filtrado = df_filtrado[df_filtrado["tipo"] == tipo_selecionado]

    #agregação
    dados_tipo = df_filtrado["tipo"].value_counts().reset_index()
    dados_tipo.columns = ["tipo", "quantidade"]

    #PALETA CAIXA
    cores_base = [AZUL_CAIXA, LARANJA_CAIXA]
    cores_extra = ["#4CAF50", "#E53935", "#8E24AA", "#00ACC1", "#FDD835"]
    paleta = cores_base + cores_extra

    cores_final = (paleta * ((len(dados_tipo) // len(paleta)) + 1))[:len(dados_tipo)]

    #gráfico barras
    fig_tipo = px.bar(
        dados_tipo,
        x="tipo",
        y="quantidade",
        title="Erros por Tipo",
        color="tipo",
        text="quantidade"
    )

    fig_tipo.update_traces(
    texttemplate="%{text:.0f}",
    textposition="outside"
    )

    fig_tipo.update_layout(
        uniformtext_minsize=8,
        uniformtext_mode="hide",
        margin=dict(t=60)
    )

        #gráfico pizza
    fig_pie = px.pie(
            dados_tipo,
            names="tipo",
            values="quantidade",
            hole=0.4,
            color_discrete_sequence=cores_final
        )

    for fig in [fig_tipo, fig_pie]:
        fig.update_layout(
            paper_bgcolor=FUNDO,
            plot_bgcolor=FUNDO,
            font=dict(color=TEXTO),
            title_x=0.5,
            showlegend=True
        )

    #evitar quebra layout
    df_filtrado["mensagem"] = df_filtrado["mensagem"].apply(
        lambda x: str(x)[:150] + "..."
    )

    return df_filtrado.to_dict("records"), fig_tipo, fig_pie


# ---------------- CALLBACK DETALHE ----------------
@app.callback(
    Output("detalhe_log", "children"),
    Input("tabela", "selected_rows"),
    Input("tabela", "data")
)
def mostrar_detalhe(selected_rows, rows):

    if not selected_rows:
        return "Selecione uma linha para ver mais detalhes"

    row = rows[selected_rows[0]]
    caminho = os.path.join(row["diretorio"], row["arquivo_nome"])

    try:
        i = row["linha_num"] - 1
        inicio = max(i - 5, 0)   # um pouco mais de contexto antes
        fim = i + LINHAS_CONTEXTO

        trecho_linhas = []

        #leitura (sem carregar tudo na memória)
        with open(caminho, "r", encoding="utf-8", errors="ignore") as f:
            for idx, linha in enumerate(f):

                if idx > fim:
                    break

                if idx >= inicio:
                    if idx == i:
                        trecho_linhas.append(
                            html.Span(
                                f">>> ERRO AQUI >>> {linha}",
                                style={
                                    "color": "red",
                                    "fontWeight": "bold",
                                    "backgroundColor": "#330000"
                                }
                            )
                        )
                    else:
                        trecho_linhas.append(html.Span(linha))

        return html.Pre(
            trecho_linhas,
            style={
                "whiteSpace": "pre-wrap",
                "backgroundColor": "#111",
                "padding": "10px",
                "border": "1px solid #444",
                "maxHeight": "500px",
                "overflowY": "scroll"
            }
        )

    except Exception as e:
        return f"Erro ao abrir arquivo: {e}"

# ---------------- RUN ----------------
app.run(debug=True, port=8052)
