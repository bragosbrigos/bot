# Bot NotebookLM - Automação de Quiz com IA Local

Bot em Python para automatizar flashcards e quizzes do NotebookLM usando Playwright e Ollama (IA local).

## Requisitos

- Python 3.8+
- Ollama instalado e rodando localmente
- Navegador Chromium (instalado automaticamente pelo Playwright)

## Instalação

### 1. Instalar dependências Python

```bash
pip install -r requirements.txt
```

### 2. Instalar browsers do Playwright

```bash
playwright install chromium
```

### 3. Instalar e configurar Ollama

Baixe e instale o Ollama em: https://ollama.com/

Após instalar, baixe o modelo recomendado:

```bash
ollama pull qwen2.5:3b
```

Ou use outro modelo de sua preferência.

### 4. Iniciar o Ollama

Certifique-se que o Ollama está rodando:

```bash
ollama serve
```

O bot se conectará em `http://localhost:11434` por padrão.

## Execução

```bash
python notebooklm_bot.py
```

## Como usar

1. Execute o script
2. O navegador Chromium será aberto em modo visível
3. Faça login manualmente no NotebookLM
4. Navegue até a página/quiz desejada
5. Pressione **ENTER** no terminal para iniciar a automação

O bot irá:
- Clicar automaticamente em todos os botões "Entendi" dos flashcards
- Tirar um screenshot após os flashcards
- Para cada questão do quiz:
  - Extrair pergunta e alternativas
  - Enviar para a IA local via Ollama
  - Clicar na alternativa recomendada
  - Avançar para próxima questão
- Tirar screenshot final ao terminar
- Gerar relatório em TXT na pasta `reports/`

## Estrutura de pastas

O bot cria automaticamente:
- `reports/` - Relatórios em TXT
- `screenshots/` - Screenshots da execução

## Configurações

Edite as variáveis no início do arquivo `notebooklm_bot.py`:

```python
OLLAMA_URL = "http://localhost:11434"      # URL do Ollama
OLLAMA_MODEL = "qwen2.5:3b"                # Modelo da IA
NOTEBOOKLM_URL = "https://notebooklm.google.com"
```

## Formato da resposta da IA

A IA deve retornar JSON neste formato:

```json
{
  "letra": "B",
  "explicacao": "Explicação curta."
}
```

## Comportamento em caso de erro

- Se a IA não retornar JSON válido: execução é interrompida
- Se a letra retornada não existir nas alternativas: execução é interrompida
- Erros críticos são exibidos no terminal

## Notas

- Não há login automático (segurança)
- Não há fallback para respostas
- O navegador roda em modo visível para acompanhamento
