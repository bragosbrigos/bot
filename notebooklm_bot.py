#!/usr/bin/env python3
"""
Bot para automatizar quiz do NotebookLM usando Playwright e Ollama (IA local).
"""

import json
import os
import re
from datetime import datetime

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import requests


# Configurações
OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "qwen2.5:3b"
NOTEBOOKLM_URL = "https://notebooklm.google.com"

# Diretórios
REPORTS_DIR = "reports"
SCREENSHOTS_DIR = "screenshots"


def create_directories():
    """Cria as pastas reports/ e screenshots/ se não existirem."""
    os.makedirs(REPORTS_DIR, exist_ok=True)
    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)


def get_timestamp():
    """Retorna timestamp formatado para nomes de arquivo."""
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def save_screenshot(page, prefix="print"):
    """Salva screenshot da página."""
    timestamp = get_timestamp()
    filename = f"{prefix}_{timestamp}.png"
    filepath = os.path.join(SCREENSHOTS_DIR, filename)
    page.screenshot(path=filepath)
    print(f"Screenshot salvo em: {filepath}")
    return filepath


def query_ollama(prompt):
    """Envia prompt para Ollama e retorna resposta JSON."""
    url = f"{OLLAMA_URL}/api/generate"
    
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        result = response.json()
        return result.get("response", "")
    except requests.exceptions.RequestException as e:
        print(f"Erro ao comunicar com Ollama: {e}")
        raise


def parse_ai_response(response_text):
    """Parse da resposta JSON da IA."""
    try:
        # Tentar extrair JSON do texto
        match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
        if match:
            response_text = match.group()
        
        data = json.loads(response_text)
        
        if "letra" not in data:
            raise ValueError("Resposta da IA não contém campo 'letra'")
        
        letra = data["letra"].strip().upper()
        explicacao = data.get("explicacao", "Sem explicação.")
        
        return letra, explicacao
    except json.JSONDecodeError as e:
        print(f"Erro ao parsear JSON da IA: {e}")
        print(f"Texto recebido: {response_text}")
        raise


def extract_question_data(page):
    """Extrai pergunta e alternativas da questão atual."""
    try:
        # Esperar o conteúdo da questão carregar
        page.wait_for_selector("quiz-question", timeout=5000)
    except PlaywrightTimeoutError:
        pass
    
    # Extrair texto da pergunta
    pergunta = ""
    try:
        pergunta_el = page.query_selector(".question-text")
        if pergunta_el:
            pergunta = pergunta_el.inner_text().strip()
        else:
            # Tentar outros seletores comuns
            for selector in ["[data-test='question-text']", ".question-prompt", "h2", "h3"]:
                el = page.query_selector(selector)
                if el:
                    pergunta = el.inner_text().strip()
                    break
    except Exception:
        pass
    
    # Extrair alternativas
    alternativas = {}
    letras_validas = ["A", "B", "C", "D", "E", "F"]
    
    try:
        # Tentar encontrar opções de múltipla escolha
        options = page.query_selector_all(".option-item, .multiple-choice-option, [role='radio'], .option")
        
        for i, opt in enumerate(options[:6]):  # Máximo 6 alternativas
            try:
                text = opt.inner_text().strip()
                if text:
                    # Tentar extrair letra inicial (A), B), C., etc.
                    match = re.match(r'^([A-F])[\)\.\s]', text, re.IGNORECASE)
                    if match:
                        letra = match.group(1).upper()
                        conteudo = text[2:].strip() if len(text) > 2 else text
                    else:
                        letra = letras_validas[i]
                        conteudo = text
                    
                    alternativas[letra] = conteudo
            except Exception:
                continue
        
        # Se não encontrou por selector, tentar por texto
        if not alternativas:
            page_content = page.content()
            for letra in letras_validas:
                padrao = rf'{letra}[\)\.\s]([^\n]+)'
                matches = re.findall(padrao, page_content, re.IGNORECASE)
                if matches and letra not in alternativas:
                    alternativas[letra] = matches[0].strip()[:200]
    except Exception:
        pass
    
    return pergunta, alternativas


def click_option_by_letter(page, letter):
    """Clica na alternativa correspondente à letra."""
    letters = ["A", "B", "C", "D", "E", "F"]
    
    try:
        index = letters.index(letter.upper())
    except ValueError:
        return False
    
    try:
        options = page.query_selector_all(".option-item, .multiple-choice-option, [role='radio'], .option")
        if index < len(options):
            options[index].click()
            return True
    except Exception:
        pass
    
    # Tentar clique por texto da letra
    try:
        page.click(f"text={letter})")
        return True
    except Exception:
        pass
    
    try:
        page.click(f"text={letter}.")
        return True
    except Exception:
        pass
    
    return False


def click_next_button(page):
    """Clica no botão 'Próxima'."""
    try:
        # Procurar botão com texto exato "Próxima"
        next_btn = page.locator('button:has-text("Próxima"), button:has-text("próxima"), [text="Próxima"]')
        if next_btn.count() > 0:
            next_btn.first.click()
            return True
    except Exception:
        pass
    
    # Tentar outros seletores
    try:
        for selector in ['button:has-text("Next")', '[data-test="next-button"]', '.next-button']:
            btn = page.locator(selector)
            if btn.count() > 0:
                btn.first.click()
                return True
    except Exception:
        pass
    
    return False


def click_entendi_button(page):
    """Clica no botão 'Entendi' enquanto existir."""
    clicked_count = 0
    
    while True:
        try:
            # Seletor específico para o botão Entendi conforme especificação
            entendi_btn = page.locator('button[aria-label="Entendi"]').first
            
            if entendi_btn.count() == 0:
                break
            
            entendi_btn.click()
            clicked_count += 1
            print(f"Botão 'Entendi' clicado ({clicked_count} vezes)")
            
            # Pequena pausa para animação
            page.wait_for_timeout(500)
            
        except Exception:
            break
    
    return clicked_count


def generate_report(questions_log):
    """Gera relatório em TXT."""
    timestamp = get_timestamp()
    filename = f"relatorio_{timestamp}.txt"
    filepath = os.path.join(REPORTS_DIR, filename)
    
    current_datetime = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("RELATÓRIO DO QUIZ\n")
        f.write(f"Data: {current_datetime}\n")
        f.write("\n")
        
        for i, q in enumerate(questions_log, 1):
            f.write(f"Questão {i}\n")
            f.write("\n")
            f.write(f"Pergunta: {q['pergunta']}\n")
            f.write("\n")
            f.write("Alternativas:\n")
            for letra, texto in q['alternativas'].items():
                f.write(f"{letra}) {texto}\n")
            f.write("\n")
            f.write(f"Resposta: {q['resposta']}\n")
            f.write("\n")
            f.write(f"Explicação: {q['explicacao']}\n")
            f.write("\n")
            f.write("\n")
    
    print(f"Relatório salvo em: {filepath}")
    return filepath


def main():
    """Função principal do bot."""
    print("=" * 60)
    print("Bot NotebookLM - Automação com IA Local")
    print("=" * 60)
    
    # Criar diretórios
    create_directories()
    print(f"Diretórios criados: {REPORTS_DIR}/, {SCREENSHOTS_DIR}/")
    
    # Menu de seleção
    print("\n" + "=" * 60)
    print("SELECIONE O MODO DE AUTOMAÇÃO:")
    print("1 - Flashcards (clicar em 'Entendi')")
    print("2 - Quiz de múltipla escolha")
    print("=" * 60)
    
    while True:
        opcao = input("\nDigite a opção desejada (1 ou 2): ").strip()
        if opcao in ["1", "2"]:
            modo = "flashcards" if opcao == "1" else "quiz"
            break
        print("Opção inválida. Digite 1 ou 2.")
    
    # Instruções iniciais
    print("\n" + "=" * 60)
    print("INSTRUÇÕES:")
    print(f"1. O navegador será aberto em modo visível")
    print(f"2. Faça login manualmente no NotebookLM")
    print(f"3. Navegue até a página desejada")
    print(f"4. Pressione ENTER neste terminal para iniciar a automação")
    print(f"Modo selecionado: {modo.upper()}")
    print("=" * 60)
    
    input("\nPressione ENTER para continuar...")
    
    with sync_playwright() as p:
        # Inicializar navegador Chromium em modo visível
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        # Abrir NotebookLM
        print(f"\nAbrindo {NOTEBOOKLM_URL}...")
        page.goto(NOTEBOOKLM_URL)
        
        print("\nAguardando usuário fazer login e navegar até a página...")
        print("Pressione ENTER quando estiver na página desejada...")
        input()
        
        # Lista para armazenar log das questões (apenas para modo quiz)
        questions_log = []
        
        if modo == "flashcards":
            # Modo Flashcards
            print("\n--- Processando flashcards (botão 'Entendi') ---")
            entendi_count = click_entendi_button(page)
            print(f"Total de botões 'Entendi' clicados: {entendi_count}")
            
            # Screenshot após flashcards
            print("\nTirando screenshot final...")
            save_screenshot(page, "print_flashcards")
            
        elif modo == "quiz":
            # Modo Quiz
            print("\n--- Iniciando quiz de múltipla escolha ---")
            question_number = 0
            
            while True:
                question_number += 1
                print(f"\n=== Questão {question_number} ===")
                
                # Extrair dados da questão
                pergunta, alternativas = extract_question_data(page)
                
                if not pergunta and not alternativas:
                    print("Nenhuma questão encontrada. Quiz pode ter terminado.")
                    question_number -= 1
                    break
                
                print(f"Pergunta: {pergunta[:100]}..." if len(pergunta) > 100 else f"Pergunta: {pergunta}")
                print(f"Alternativas encontradas: {list(alternativas.keys())}")
                
                if not alternativas:
                    print("ERRO: Nenhuma alternativa encontrada!")
                    print("Encerrando execução...")
                    break
                
                # Construir prompt para IA
                alternativas_text = "\n".join([f"{letra}) {texto}" for letra, texto in alternativas.items()])
                
                prompt = f"""Você é um assistente que responde questões de múltipla escolha.
Responda APENAS com JSON válido neste formato exato:
{{
  "letra": "X",
  "explicacao": "explicação curta"
}}

Regras:
- Escolha APENAS UMA alternativa correta
- Resposta deve ser curta e direta
- Explicação deve ser curta (máximo 2 frases)
- Retorne SOMENTE JSON válido, sem texto adicional

Pergunta: {pergunta}

Alternativas:
{alternativas_text}

Responda em JSON:"""

                # Consultar IA
                print("Consultando IA local (Ollama)...")
                try:
                    ai_response = query_ollama(prompt)
                    print(f"Resposta da IA: {ai_response[:150]}...")
                    
                    letra, explicacao = parse_ai_response(ai_response)
                    print(f"Letra escolhida: {letra}")
                    
                except Exception as e:
                    print(f"\nERRO CRÍTICO: Falha ao obter/processar resposta da IA: {e}")
                    print("Encerrando execução imediatamente.")
                    browser.close()
                    return
                
                # Validar letra retornada
                if letra not in alternativas:
                    print(f"\nERRO CRÍTICO: IA retornou letra inválida '{letra}'")
                    print(f"Alternativas válidas: {list(alternativas.keys())}")
                    print("Encerrando execução imediatamente.")
                    browser.close()
                    return
                
                # Clicar na alternativa
                print(f"Clicando na alternativa {letra}...")
                if not click_option_by_letter(page, letra):
                    print(f"ERRO: Não foi possível clicar na alternativa {letra}")
                    print("Encerrando execução...")
                    break
                
                page.wait_for_timeout(1000)
                
                # Salvar log da questão
                questions_log.append({
                    "pergunta": pergunta,
                    "alternativas": alternativas,
                    "resposta": letra,
                    "explicacao": explicacao
                })
                
                # Clicar em "Próxima"
                print("Tentando avançar para próxima questão...")
                if not click_next_button(page):
                    print("Botão 'Próxima' não encontrado. Quiz finalizado.")
                    break
                
                page.wait_for_timeout(1500)
            
            # Screenshot final
            print("\n--- Finalização ---")
            print("Tirando screenshot final...")
            save_screenshot(page, "print_final")
            
            # Gerar relatório
            if questions_log:
                print("\nGerando relatório...")
                generate_report(questions_log)
                print(f"\nTotal de questões respondidas: {len(questions_log)}")
            else:
                print("\nNenhuma questão foi respondida.")
        
        # Fechar navegador
        print("\nFechando navegador...")
        browser.close()
        
        print("\n" + "=" * 60)
        print("Automação concluída!")
        print("=" * 60)


if __name__ == "__main__":
    main()
