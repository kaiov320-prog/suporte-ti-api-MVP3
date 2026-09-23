"""Configuração e inicialização do banco SQLite."""

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path


# Por padrão, o banco ficará em dados/chamados.db.
# No Docker, DATABASE_PATH permitirá definir o caminho no volume.
PASTA_PROJETO = Path(__file__).resolve().parent

CAMINHO_BANCO = Path(
    os.environ.get(
        "DATABASE_PATH",
        str(PASTA_PROJETO / "dados" / "chamados.db"),
    )
)


@contextmanager
def conectar():
    """Abre uma conexão e garante seu fechamento ao finalizar."""
    CAMINHO_BANCO.parent.mkdir(parents=True, exist_ok=True)

    conexao = sqlite3.connect(str(CAMINHO_BANCO), timeout=10)
    conexao.row_factory = sqlite3.Row

    try:
        yield conexao
        conexao.commit()
    except Exception:
        conexao.rollback()
        raise
    finally:
        conexao.close()


def inicializar_banco():
    """Cria a tabela caso ainda não exista, preservando os dados."""
    with conectar() as conexao:
        conexao.execute(
            """
            CREATE TABLE IF NOT EXISTS chamados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo TEXT NOT NULL,
                descricao TEXT NOT NULL,
                categoria TEXT NOT NULL
                    CHECK (
                        categoria IN (
                            'hardware', 'software', 'rede',
                            'impressora', 'outros'
                        )
                    ),
                prioridade TEXT NOT NULL
                    CHECK (prioridade IN ('baixa', 'media', 'alta')),
                status TEXT NOT NULL DEFAULT 'aberto'
                    CHECK (
                        status IN (
                            'aberto', 'em_atendimento', 'concluido'
                        )
                    ),
                cep TEXT NOT NULL
                    CHECK (
                        length(cep) = 8
                        AND cep NOT GLOB '*[^0-9]*'
                    ),
                logradouro TEXT NOT NULL,
                numero TEXT NOT NULL,
                complemento TEXT NOT NULL DEFAULT '',
                bairro TEXT NOT NULL,
                cidade TEXT NOT NULL,
                uf TEXT NOT NULL CHECK (length(uf) = 2),
                criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


if __name__ == "__main__":
    inicializar_banco()
    print(f"Banco inicializado em: {CAMINHO_BANCO}")