#!/usr/bin/env python3
"""
send_to_notebooklm.py — Envia a nota atual para o Google NotebookLM via RPA.

Dependências: pip install playwright && playwright install chromium
Requisito de Execução: 
Você PRECISA estar rodando o Google Chrome com a porta de depuração ativada.
Exemplo no Linux: google-chrome-stable --remote-debugging-port=9222

Uso:
    python3 PyScripts/send_to_notebooklm.py "caminho/do/arquivo.md"
"""

import sys
import time
import socket
import subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright

def is_port_open(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def start_chrome():
    print("🚀 Iniciando o Google Chrome com modo de depuração ativado...")
    try:
        # Chrome bloqueia porta de depuração no perfil padrão por segurança.
        # Precisamos passar uma pasta de perfil dedicada para automação.
        debug_dir = Path.home() / ".config" / "google-chrome-debug"
        debug_dir.mkdir(parents=True, exist_ok=True)
        
        subprocess.Popen([
            "google-chrome-stable",
            "--remote-debugging-port=9222",
            f"--user-data-dir={debug_dir}"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Aguarda até o Chrome abrir a porta
        sucesso = False
        for _ in range(15):
            if is_port_open(9222):
                sucesso = True
                break
            time.sleep(0.5)
            
        return sucesso
    except FileNotFoundError:
        print("❌ 'google-chrome-stable' não encontrado no sistema!")
        return False

def send_to_notebooklm(file_path):
    path = Path(file_path)
    if not path.exists():
        print(f"❌ Erro: Arquivo {file_path} não encontrado.")
        sys.exit(1)
        
    content = path.read_text(encoding="utf-8")
    title = path.stem

    if not is_port_open(9222):
        print("⚠️ Chrome não está rodando na porta 9222.")
        if not start_chrome():
            print("❌ Falha crítica: Não foi possível iniciar e conectar ao Chrome.")
            print("Certifique-se de que o Google Chrome está totalmente fechado antes de rodar o script.")
            sys.exit(1)
            
    print("� Conectando ao Chrome na porta 9222...")
    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp("http://localhost:9222")
        except Exception as e:
            print("❌ Falha ao conectar. O Chrome deve estar fechado antes para que possamos injetar a flag.")
            print(f"Detalhe: {e}")
            sys.exit(1)
            
        print("✅ Conectado! Abrindo NotebookLM...")
        context = browser.contexts[0]
        page = context.new_page()
        
        try:
            page.goto("https://notebooklm.google.com/")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(3000)
            
            print("➡️ Clicando em 'Criar/Novo notebook'...")
            # Em Material Design Web 3, os botões são <md-elevated-button> ou <button> com text-content oculto
            # O get_by_role('button') interage melhor com shadow DOMs que o text=
            btn_novo = page.get_by_role("button", name="Novo bloco de notas", exact=False)
            if not btn_novo.is_visible():
                btn_novo = page.get_by_role("button", name="New notebook", exact=False)
            if not btn_novo.is_visible():
                # Tenta localizar pela div de classe de container se as arias falharem
                btn_novo = page.locator("md-elevated-button").first
                
            btn_novo.wait_for(state="visible", timeout=10000)
            btn_novo.click()
            
            page.wait_for_timeout(2000)
            
            print("➡️ Abrindo opção de colar texto (Texto Copiado) ...")
            # Procura por qualquer elemento que tenha Copy/Paste no texto ou aria
            btn_texto = page.get_by_text("Texto copiado", exact=False)
            if not btn_texto.is_visible():
                btn_texto = page.get_by_text("Copied text", exact=False)
            if not btn_texto.is_visible():
                btn_texto = page.locator("text=/texto/i").nth(1) # fallback
                
            btn_texto.wait_for(state="visible", timeout=5000)
            btn_texto.click()
            
            page.wait_for_timeout(1000)
            print("➡️ Digitando título do tópico e colando o conteúdo...")
            
            # Localizar textarea principal ou input de texto multiline
            textarea = page.locator("textarea").first
            textarea.wait_for(state="visible", timeout=3000)
            textarea.fill(content)
            
            # Título: geralmente é o primeiro input text
            inputs = page.locator("input[type='text']").all()
            for inp in inputs:
                if inp.is_visible():
                    inp.fill(title)
                    break
            
            page.wait_for_timeout(500)
            
            print("➡️ Finalizando Inserção no Notebook...")
            btn_inserir = page.get_by_role("button", name="Inserir", exact=False)
            if not btn_inserir.is_visible():
                btn_inserir = page.get_by_role("button", name="Insert", exact=False)
            if not btn_inserir.is_visible():
                btn_inserir = page.locator("text=/inserir|insert/i").first
                
            btn_inserir.wait_for(state="visible", timeout=3000)
            btn_inserir.click()
            
            print("✨ Sucesso! O NotebookLM está carregando as fontes dessa nota.")
            # Espera um tempinho para ver o loading começar
            page.wait_for_timeout(5000)
            
        except Exception as e:
            print(f"❌ Automação falhou. A interface do Google pode ter mudado.")
            print(f"    Erro capturado: {e}")
            
        finally:
            print("🏁 Fechando script (A aba continuará aberta no seu Chrome para você usar o NotebookLM).")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso do script: python send_to_notebooklm.py <caminho_da_nota.md>")
        sys.exit(1)
    
    send_to_notebooklm(sys.argv[1])
