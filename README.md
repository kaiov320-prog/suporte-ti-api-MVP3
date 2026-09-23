# Suporte TI — API

API REST para gerenciamento de chamados de suporte presencial de TI,
desenvolvida como parte do MVP da pós-graduação em Engenharia de Software.

Este módulo realiza as validações dos chamados, persiste os dados em
SQLite e consulta o serviço externo ViaCEP para obter endereços.

## Tecnologias

- Python 3.14
- Flask
- SQLite
- Requests
- Gunicorn
- Docker

As versões das dependências estão registradas em `requirements.txt`.

## Funcionalidades

- Criar, listar, consultar, atualizar e excluir chamados.
- Filtrar chamados por status e prioridade.
- Validar os dados recebidos.
- Consultar endereços por CEP.
- Verificar a disponibilidade da API e do banco.
- Persistir os dados em arquivo SQLite.

## Arquitetura

O sistema segue o cenário 1.1:

Interface → API própria → ViaCEP

A API própria também realiza a leitura e gravação no SQLite.

A interface e a API são executadas em containers separados.
O Nginx da interface encaminha as requisições `/api/` para o back-end.

Repositório da interface:
https://github.com/kaiov320-prog/suporte-ti-interface-MVP3

## Estrutura

```text
suporte-ti-api/
├── .dockerignore
├── .gitignore
├── app.py
├── database.py
├── Dockerfile
├── README.md
└── requirements.txt
```

A pasta `dados/` e o arquivo `chamados.db` são criados durante a execução.
Eles não devem ser enviados ao repositório.

## Pré-requisitos

Para executar com Docker:

- Docker Desktop instalado e em execução.
- Porta 5001 disponível.
- Internet para baixar a imagem, instalar dependências e consultar o ViaCEP.

Para executar localmente sem Docker:

- Python 3.14.
- Ambiente virtual e dependências instaladas.

Os comandos abaixo consideram macOS e terminal zsh/bash.

## Obter o projeto

Baixe o repositório pelo GitHub em **Code → Download ZIP** e extraia
os arquivos, ou utilize uma cópia local.

Abra um terminal na pasta que contém `app.py` e `Dockerfile`.

## Execução com Docker

### 1. Preparar a pasta do banco

```bash
mkdir -p dados
```

Essa etapa é necessária em uma cópia nova do repositório, pois a pasta
de dados não é versionada.

### 2. Construir a imagem

```bash
docker build -t suporte-ti-api .
```

### 3. Iniciar o container

```bash
docker run -d --name suporte-ti-api -p 5001:5001 --mount "type=bind,source=$(pwd)/dados,target=/app/dados" suporte-ti-api
```

O comando deve ser executado na raiz deste projeto.

A montagem conecta a pasta local `dados/` à pasta `/app/dados` do
container. O arquivo do banco permanece no computador mesmo quando o
container é removido, desde que a pasta local seja preservada.

O servidor utilizado no container é o Gunicorn.

### 4. Verificar a API

Acesse:

http://localhost:5001/api/health

Resposta esperada:

```json
{
  "banco": "conectado",
  "status": "ok"
}
```

### Comandos de gerenciamento

Consultar os containers ativos:

```bash
docker ps
```

Consultar os logs:

```bash
docker logs suporte-ti-api
```

Parar:

```bash
docker stop suporte-ti-api
```

Iniciar um container existente:

```bash
docker start suporte-ti-api
```

Reiniciar:

```bash
docker restart suporte-ti-api
```

### Aplicar alterações no código

Após modificar os arquivos, reconstrua a imagem e recrie o container:

```bash
docker build -t suporte-ti-api .
docker stop suporte-ti-api
docker rm suporte-ti-api
docker run -d --name suporte-ti-api -p 5001:5001 --mount "type=bind,source=$(pwd)/dados,target=/app/dados" suporte-ti-api
```

Utilize a mesma pasta `dados/` para manter os registros existentes.

## Execução local para desenvolvimento

Não execute a versão local e o container simultaneamente na porta 5001.

Se o container estiver em execução, pare-o:

```bash
docker stop suporte-ti-api
```

Crie e ative o ambiente virtual:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Instale as dependências:

```bash
python -m pip install -r requirements.txt
```

Inicie a API:

```bash
python app.py
```

O banco será inicializado automaticamente.

Para encerrar o servidor local, pressione **Control + C** no terminal.
O servidor iniciado por esse comando é destinado ao desenvolvimento.

## Configuração do banco

A variável de ambiente `DATABASE_PATH` define o caminho do banco.

- Execução local padrão: `dados/chamados.db` dentro do projeto.
- Container: `/app/dados/chamados.db`.

A aplicação cria a tabela caso ela não exista, preservando os registros
já armazenados.

## Rotas

| Método | Rota | Finalidade |
|---|---|---|
| GET | `/api/health` | Verificar API e conexão com o banco |
| GET | `/api/chamados` | Listar chamados |
| GET | `/api/chamados/{id}` | Consultar um chamado |
| POST | `/api/chamados` | Criar chamado |
| PUT | `/api/chamados/{id}` | Atualizar todos os campos editáveis |
| DELETE | `/api/chamados/{id}` | Excluir chamado |
| GET | `/api/cep/{cep}` | Consultar endereço no ViaCEP |

### Filtros

A listagem aceita os parâmetros opcionais `status` e `prioridade`.

Exemplo:

```text
http://localhost:5001/api/chamados?status=aberto&prioridade=alta
```

Os chamados são ordenados pelo identificador, do mais recente para o
mais antigo.

### Exemplo de criação ou atualização

Enviar o cabeçalho `Content-Type: application/json`.

```json
{
  "titulo": "Impressora sem conexão",
  "descricao": "A impressora da recepção não está conectando à rede.",
  "categoria": "impressora",
  "prioridade": "alta",
  "status": "aberto",
  "cep": "01001000",
  "logradouro": "Praça da Sé",
  "numero": "100",
  "complemento": "Sala de testes",
  "bairro": "Sé",
  "cidade": "São Paulo",
  "uf": "SP"
}
```

O método PUT exige todos os campos obrigatórios, assim como o POST.

### Valores aceitos

- Categoria: `hardware`, `software`, `rede`, `impressora`, `outros`.
- Prioridade: `baixa`, `media`, `alta`.
- Status: `aberto`, `em_atendimento`, `concluido`.
- UF: sigla válida de uma unidade federativa brasileira.
- CEP no cadastro: oito dígitos, com hífen opcional.
- CEP na rota de consulta: exatamente oito dígitos, sem hífen.

O complemento é opcional. Os demais campos do exemplo são obrigatórios.

O título exige pelo menos 3 caracteres e a descrição pelo menos 10.
Campos desconhecidos e valores inválidos são rejeitados.

### Respostas

- `200`: consulta ou atualização realizada.
- `201`: chamado criado.
- `204`: chamado excluído, sem corpo na resposta.
- `400`: dados ou filtros inválidos.
- `404`: chamado, CEP ou rota não encontrado.
- `405`: método HTTP não permitido.
- `413`: corpo da requisição acima do limite de 64 KiB.
- `500`: erro interno ou de acesso ao banco.
- `502`: falha de comunicação ou resposta inválida do ViaCEP.
- `504`: tempo de espera excedido na consulta ao ViaCEP.

Erros retornam JSON com a propriedade `erro`:

```json
{
  "erro": "Chamado não encontrado."
}
```

A listagem retorna:

```json
{
  "chamados": []
}
```

Cada chamado retornado inclui `id`, os campos de cadastro e as datas
`criado_em` e `atualizado_em`, geradas pelo SQLite em UTC.

## Integração com a interface

Inicie esta API antes de utilizar a interface.

No Docker Desktop, o Nginx da interface encaminha as chamadas para:

```text
http://host.docker.internal:5001
```

O navegador acessa a interface e suas rotas `/api/` pelo mesmo endereço:

http://localhost:8080

Consulte o README do repositório da interface para construir e iniciar
seu container.

## Serviço externo

A API consulta o ViaCEP:

```text
GET https://viacep.com.br/ws/{cep}/json/
```

Documentação oficial:
https://viacep.com.br/

O serviço é gratuito e sua consulta documentada não exige cadastro
ou chave de autenticação. A página consultada não informa uma licença
específica para o serviço.

Devem ser observadas as condições do provedor, incluindo a restrição
a consultas massivas para validação de bases locais.

Os dados são tratados pelo back-end e devolvidos à interface em JSON.
Não ocorre redirecionamento para outra aplicação.

## Verificações realizadas durante o desenvolvimento

- Cadastro e listagem pela interface.
- Edição de chamado e atualização dos contadores.
- Filtros de status e prioridade na interface.
- Exclusão e confirmação da ausência após recarregar a página.
- Consulta de CEP com retorno de endereço.
- Construção e inicialização do container do back-end.
- Consulta de saúde com conexão ao banco.
- Permanência de um chamado após reiniciar o container.

Essas verificações foram manuais. A revisão final ainda deve incluir
casos de erro e execução a partir dos arquivos publicados.

## Limites do escopo

O projeto não implementa autenticação, autorização, anexos
ou notificações. Os dados utilizados na demonstração são fictícios.