"""API REST para gerenciamento de chamados de suporte de TI."""

import re
import sqlite3

import requests
from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

from database import conectar, inicializar_banco


app = Flask(__name__)
app.json.ensure_ascii = False
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024

inicializar_banco()

CAMPOS = (
    "titulo",
    "descricao",
    "categoria",
    "prioridade",
    "status",
    "cep",
    "logradouro",
    "numero",
    "complemento",
    "bairro",
    "cidade",
    "uf",
)

LIMITES = {
    "titulo": 120,
    "descricao": 2000,
    "categoria": 30,
    "prioridade": 20,
    "status": 30,
    "cep": 9,
    "logradouro": 200,
    "numero": 20,
    "complemento": 100,
    "bairro": 100,
    "cidade": 100,
    "uf": 2,
}

CATEGORIAS = {"hardware", "software", "rede", "impressora", "outros"}
PRIORIDADES = {"baixa", "media", "alta"}
STATUS = {"aberto", "em_atendimento", "concluido"}

UFS = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO",
    "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI",
    "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
}


def validar_chamado():
    """Valida os dados recebidos antes de gravar no banco."""
    if not request.is_json:
        raise ValueError("Envie os dados no formato JSON.")

    dados = request.get_json()

    if not isinstance(dados, dict):
        raise ValueError("O corpo da requisição deve ser um objeto JSON.")

    campos_extras = set(dados) - set(CAMPOS)
    if campos_extras:
        raise ValueError(
            "Campos desconhecidos: " + ", ".join(sorted(campos_extras))
        )

    resultado = {}

    for campo in CAMPOS:
        valor = dados.get(campo, "")

        if not isinstance(valor, str):
            raise ValueError(f"O campo '{campo}' deve ser um texto.")

        valor = valor.strip()

        if campo != "complemento" and not valor:
            raise ValueError(f"O campo '{campo}' é obrigatório.")

        if len(valor) > LIMITES[campo]:
            raise ValueError(
                f"O campo '{campo}' aceita até {LIMITES[campo]} caracteres."
            )

        resultado[campo] = valor

    if len(resultado["titulo"]) < 3:
        raise ValueError("O título deve ter pelo menos 3 caracteres.")

    if len(resultado["descricao"]) < 10:
        raise ValueError("A descrição deve ter pelo menos 10 caracteres.")

    if resultado["categoria"] not in CATEGORIAS:
        raise ValueError("Categoria inválida.")

    if resultado["prioridade"] not in PRIORIDADES:
        raise ValueError("Prioridade inválida.")

    if resultado["status"] not in STATUS:
        raise ValueError("Status inválido.")

    if not re.fullmatch(r"[0-9]{5}-?[0-9]{3}", resultado["cep"]):
        raise ValueError("O CEP deve conter oito dígitos.")

    resultado["cep"] = resultado["cep"].replace("-", "")
    resultado["uf"] = resultado["uf"].upper()

    if resultado["uf"] not in UFS:
        raise ValueError("UF inválida.")

    return resultado


@app.errorhandler(ValueError)
def tratar_validacao(erro):
    return jsonify({"erro": str(erro)}), 400


@app.errorhandler(HTTPException)
def tratar_erro_http(erro):
    mensagens = {
        400: "Requisição inválida. Confira o JSON enviado.",
        404: "Rota não encontrada.",
        405: "Método HTTP não permitido nesta rota.",
        413: "O conteúdo enviado ultrapassa o tamanho permitido.",
        415: "Envie o conteúdo no formato JSON.",
    }

    resposta = erro.get_response()
    resposta.data = app.json.dumps(
        {"erro": mensagens.get(erro.code, erro.description)}
    )
    resposta.content_type = "application/json"
    return resposta


@app.errorhandler(sqlite3.Error)
def tratar_erro_banco(erro):
    app.logger.exception("Erro ao acessar o SQLite.")
    return jsonify({"erro": "Não foi possível acessar o banco de dados."}), 500


@app.errorhandler(500)
def tratar_erro_interno(erro):
    return jsonify({"erro": "Ocorreu um erro interno no servidor."}), 500


@app.get("/api/health")
def verificar_saude():
    with conectar() as conexao:
        conexao.execute("SELECT 1").fetchone()

    return jsonify({"status": "ok", "banco": "conectado"})


@app.get("/api/chamados")
def listar_chamados():
    """Lista chamados, permitindo filtros opcionais pela API."""
    status = request.args.get("status", "").strip()
    prioridade = request.args.get("prioridade", "").strip()

    if status and status not in STATUS:
        raise ValueError("Filtro de status inválido.")

    if prioridade and prioridade not in PRIORIDADES:
        raise ValueError("Filtro de prioridade inválido.")

    consulta = "SELECT * FROM chamados WHERE 1 = 1"
    parametros = []

    if status:
        consulta += " AND status = ?"
        parametros.append(status)

    if prioridade:
        consulta += " AND prioridade = ?"
        parametros.append(prioridade)

    consulta += " ORDER BY id DESC"

    with conectar() as conexao:
        registros = conexao.execute(consulta, parametros).fetchall()

    return jsonify({"chamados": [dict(item) for item in registros]})


@app.get("/api/chamados/<int:chamado_id>")
def buscar_chamado(chamado_id):
    with conectar() as conexao:
        registro = conexao.execute(
            "SELECT * FROM chamados WHERE id = ?",
            (chamado_id,),
        ).fetchone()

    if registro is None:
        return jsonify({"erro": "Chamado não encontrado."}), 404

    return jsonify(dict(registro))


@app.post("/api/chamados")
def criar_chamado():
    dados = validar_chamado()

    # Os nomes das colunas vêm da constante CAMPOS.
    # Os valores recebidos são enviados como parâmetros SQL.
    colunas = ", ".join(CAMPOS)
    marcadores = ", ".join("?" for _ in CAMPOS)
    valores = tuple(dados[campo] for campo in CAMPOS)

    with conectar() as conexao:
        cursor = conexao.execute(
            f"INSERT INTO chamados ({colunas}) VALUES ({marcadores})",
            valores,
        )

        registro = conexao.execute(
            "SELECT * FROM chamados WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()

    return jsonify(dict(registro)), 201


@app.put("/api/chamados/<int:chamado_id>")
def atualizar_chamado(chamado_id):
    dados = validar_chamado()

    atribuicoes = ", ".join(f"{campo} = ?" for campo in CAMPOS)
    valores = tuple(dados[campo] for campo in CAMPOS) + (chamado_id,)

    with conectar() as conexao:
        cursor = conexao.execute(
            f"""
            UPDATE chamados
            SET {atribuicoes}, atualizado_em = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            valores,
        )

        if cursor.rowcount == 0:
            return jsonify({"erro": "Chamado não encontrado."}), 404

        registro = conexao.execute(
            "SELECT * FROM chamados WHERE id = ?",
            (chamado_id,),
        ).fetchone()

    return jsonify(dict(registro))


@app.delete("/api/chamados/<int:chamado_id>")
def excluir_chamado(chamado_id):
    with conectar() as conexao:
        cursor = conexao.execute(
            "DELETE FROM chamados WHERE id = ?",
            (chamado_id,),
        )

        if cursor.rowcount == 0:
            return jsonify({"erro": "Chamado não encontrado."}), 404

    return "", 204


@app.get("/api/cep/<cep>")
def consultar_cep(cep):
    if not re.fullmatch(r"[0-9]{8}", cep):
        raise ValueError("Informe um CEP com exatamente oito dígitos.")

    try:
        resposta = requests.get(
            f"https://viacep.com.br/ws/{cep}/json/",
            timeout=(3, 5),
        )
        resposta.raise_for_status()
    except requests.exceptions.Timeout:
        return jsonify(
            {"erro": "A consulta de CEP demorou para responder. Tente novamente."}
        ), 504
    except requests.exceptions.RequestException:
        app.logger.warning("Falha na comunicação com o ViaCEP.")
        return jsonify(
            {"erro": "O serviço de CEP está indisponível. Tente novamente."}
        ), 502

    try:
        endereco = resposta.json()
    except ValueError:
        return jsonify({"erro": "O serviço de CEP retornou dados inválidos."}), 502

    if not isinstance(endereco, dict):
        return jsonify({"erro": "O serviço de CEP retornou dados inválidos."}), 502

    if endereco.get("erro"):
        return jsonify({"erro": "CEP não encontrado."}), 404

    campos_endereco = ("cep", "logradouro", "bairro", "localidade", "uf")

    if any(
        not isinstance(endereco.get(campo, ""), str)
        for campo in campos_endereco
    ):
        return jsonify({"erro": "O serviço de CEP retornou dados inválidos."}), 502

    if not endereco.get("localidade") or endereco.get("uf") not in UFS:
        return jsonify({"erro": "O serviço de CEP retornou endereço incompleto."}), 502

    return jsonify({
        campo: endereco.get(campo, "")
        for campo in campos_endereco
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=False)