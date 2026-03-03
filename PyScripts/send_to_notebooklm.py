#!/usr/bin/env python3
"""
send_to_notebooklm.py — Envia a nota atual para o Google NotebookLM via RPA.

Dependências: pip install playwright && playwright install chromium
Requisito de Execução: 
Você PRECISA estar rodando o Google Chrome com a porta de depuração ativada.
Exemplo no Linux: google-chrome-stable --remote-debugging-port=9222 --user-data-dir=~/.config/google-chrome-debug

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
        debug_dir = Path.home() / ".config" / "google-chrome-debug"
        debug_dir.mkdir(parents=True, exist_ok=True)
        
        subprocess.Popen([
            "google-chrome-stable",
            "--remote-debugging-port=9222",
            f"--user-data-dir={debug_dir}"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
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

def get_prompt(prompt_name, materia, assunto, topic_full, other_topics):
    prompt_path = Path(f"/home/Pedro/Documentos/Obsidian/SmartNoteBrain/DailyLearning/Prompts/{prompt_name}.md")
    if not prompt_path.exists():
        return f"Conteúdo sobre {topic_full} de {materia} - {assunto}"
    
    text = prompt_path.read_text(encoding="utf-8")
    
    # Remove marcações markdown
    if text.startswith("```markdown\n"): text = text[12:]
    elif text.startswith("```markdown"): text = text[11:]
    if text.endswith("\n```\n"): text = text[:-5]
    elif text.endswith("\n```"): text = text[:-4]
    elif text.endswith("```"): text = text[:-3]
    
    text = text.replace("são eles: <>", f"são eles: {topic_full}")
    text = text.replace("do assunto: <>", f"do assunto: {assunto}")
    text = text.replace("da disciplina: <>", f"da disciplina: {materia}")
    
    others_str = "\n".join([f"- {t}" for t in other_topics])
    text = text.replace("<OTHER_TOPICS>", others_str)
    
    return text.strip()

def send_to_notebooklm(file_path):
    path = Path(file_path)
    if not path.exists():
        print(f"❌ Erro: Arquivo {file_path} não encontrado.")
        sys.exit(1)
        
    title = path.stem
    
    parts = path.parts
    try:
        idx_disc = parts.index("Disciplinas")
        materia_dir = parts[idx_disc+1]
        materia = materia_dir.split(". ", 1)[1] if ". " in materia_dir else materia_dir
        
        assunto_dir = parts[idx_disc+2]
        assunto = assunto_dir.split(". ", 1)[1] if ". " in assunto_dir else assunto_dir
        
        other_topics = []
        for f in path.parent.glob("*.md"):
            if f.name != path.name:
                other_topics.append(f.stem)
    except ValueError:
        materia = "Desconhecida"
        assunto = "Desconhecido"
        other_topics = []

    prompt_deepsearch = get_prompt("DeepSearch", materia, assunto, title, other_topics)
    prompt_deepresearch = get_prompt("DeepResearch", materia, assunto, title, other_topics)

    if not is_port_open(9222):
        print("⚠️ Chrome não está rodando na porta 9222.")
        if not start_chrome():
            print("❌ Falha crítica: Não foi possível iniciar e conectar ao Chrome.")
            sys.exit(1)
            
    print("🔌 Conectando ao Chrome na porta 9222...")
    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp("http://localhost:9222")
            context = browser.contexts[0]
            page = context.new_page()
            
            page.goto("https://notebooklm.google.com/")
            page.wait_for_timeout(3000)
            
            print("➡️ Procurando botão de 'Criar/Novo notebook'...")
            js_click_new = """() => {
                const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
                let node;
                while(node = walker.nextNode()) {
                    let txt = node.textContent.toLowerCase();
                    if(txt.includes('novo bloco') || txt.includes('new notebook') || txt.includes('create')) {
                        let parent = node.parentElement;
                        while(parent && parent.tagName !== 'BUTTON' && !parent.tagName.includes('-BUTTON') && parent.getAttribute('role') !== 'button') {
                            if(parent.tagName === 'BODY') break;
                            parent = parent.parentElement;
                        }
                        if(parent && parent.tagName !== 'BODY') { parent.click(); return true; }
                    }
                }
                const btn = document.querySelector('md-elevated-button, button.mat-mdc-unelevated-button');
                if(btn) { btn.click(); return true; }
                return false;
            }"""
            page.evaluate(js_click_new)
            
            # Quando clica em Novo, um modal se abre automaticamente. Esperamos ele carregar.
            page.wait_for_timeout(4000)
            
            print("➡️ Pressionando 'Escape' para fechar a abinha inicial de fontes...")
            page.keyboard.press("Escape")
            page.wait_for_timeout(1000)
            # Tenta clicar no X caso o Escape falhe
            page.evaluate("""() => {
                const closeBtns = Array.from(document.querySelectorAll('button, md-icon-button'));
                for(let b of closeBtns) {
                    if((b.getAttribute('aria-label')||'').match(/close|fechar/i) || (b.textContent||'').match(/close/i)) {
                        b.click(); return true;
                    }
                }
                const icons = Array.from(document.querySelectorAll('.google-symbols'));
                for(let i of icons) {
                   if(i.textContent.includes('close')) {
                       if(i.parentElement) { i.parentElement.click(); return true; }
                   }
                }
            }""")
            page.wait_for_timeout(1000)
            
            print(f"➡️ Renomeando notebook para '{title}'...")
            box = page.evaluate("""() => {
                const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
                let node;
                while(node = walker.nextNode()) {
                    let txt = node.textContent.trim().toLowerCase();
                    if(txt === 'untitled notebook' || txt === 'bloco de notas sem título' || txt === 'notebook sem título') {
                        let parent = node.parentElement;
                        if(parent) { 
                            const rect = parent.getBoundingClientRect();
                            return {x: rect.x + rect.width/2, y: rect.y + rect.height/2};
                        }
                    }
                }
                return null;
            }""")
            
            if box:
                page.mouse.click(box['x'], box['y'])
                page.wait_for_timeout(500)
                
                # Tenta jogar o valor direto num input ativo, se houver
                foco_input = page.evaluate("""(newTitle) => {
                    if (document.activeElement && (document.activeElement.tagName === 'INPUT' || document.activeElement.tagName === 'TEXTAREA')) {
                        document.activeElement.value = newTitle;
                        document.activeElement.dispatchEvent(new Event('input', { bubbles: true }));
                        document.activeElement.dispatchEvent(new Event('change', { bubbles: true }));
                        return true;
                    }
                    return false;
                }""", title)
                
                if not foco_input:
                    # Tenta 3 backspaces rapidos como fallback seguro
                    for _ in range(25):
                        page.keyboard.press("Backspace")
                    page.keyboard.type(title, delay=10)
                
                page.keyboard.press("Enter")
                page.mouse.click(0, 0)  # Tira o foco
            else:
                print("⚠️ Não achei o elemento Untitled Notebook para clicar. Apenas focado no DOM.")
            page.wait_for_timeout(1000)
            
            def do_search_and_import(prompt_text, step_name):
                print(f"➡️ [{step_name}] Clicando no botão de Adicionar Fonte...")
                
                # Clica no botão (+) ou "Adicionar fontes" (geralmente lado esquerdo)
                page.evaluate("""() => {
                    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
                    let node;
                    while(node = walker.nextNode()) {
                        let txt = node.textContent.trim().toLowerCase();
                        if(txt.includes('adicionar fonte') || txt.includes('add source') || txt === 'web' || txt === 'site' || txt === 'sites') {
                            let parent = node.parentElement;
                            while(parent && parent.tagName !== 'BUTTON' && !parent.tagName.includes('-BUTTON')) {
                                if(parent.tagName === 'BODY') break;
                                parent = parent.parentElement;
                            }
                            if(parent && parent.tagName !== 'BODY') { parent.click(); return true; }
                        }
                    }
                    const icons = Array.from(document.querySelectorAll('.google-symbols'));
                    for(let i of icons) {
                        if(i.textContent === 'add') {
                            if(i.parentElement) { i.parentElement.click(); return true;}
                        }
                    }
                }""")
                
                print(f"⏳ [{step_name}] Aguardando a caixa de pesquisa web ser liberada pelo sistema...")
                # O Google bloqueia novas pesquisas enquanto a anterior ainda está baixando/processando.
                # Esse JS vai rodar num loop por até 60 segundos esperando a barra liberar.
                liberado = page.evaluate("""() => {
                    return new Promise((resolve) => {
                        let attempts = 0;
                        let check = setInterval(() => {
                            attempts++;
                            let bodyText = document.body.textContent.toLowerCase();
                            if(!bodyText.includes('temporariamente desativada') && !bodyText.includes('temporarily disabled')) {
                                const inputs = document.querySelectorAll('input[type="text"], textarea');
                                for(let inp of inputs) {
                                    let placeholder = (inp.getAttribute('placeholder') || '').toLowerCase();
                                    if(placeholder.includes('pesquise novas fontes') || placeholder.includes('search') || placeholder.includes('web')) {
                                        if(!inp.disabled) {
                                            clearInterval(check);
                                            resolve(true);
                                            return;
                                        }
                                    }
                                }
                            }
                            if(attempts > 60) { clearInterval(check); resolve(false); } // Max 60 seg
                        }, 1000);
                    });
                }""")
                
                if not liberado:
                    print(f"⚠️ Aviso: A barra de pesquisa não liberou a tempo. Prosseguindo forçadamente...")
                else:
                    page.wait_for_timeout(1000)
                    
                print(f"➡️ [{step_name}] Preenchendo a caixa de pesquisa na Web...")
                page.evaluate("""(text) => {
                    const inputs = document.querySelectorAll('input[type="text"], textarea');
                    for(let inp of inputs) {
                        let placeholder = (inp.getAttribute('placeholder') || '').toLowerCase();
                        if(placeholder.includes('pesquise novas fontes') || placeholder.includes('search') || placeholder.includes('web')) {
                            inp.focus();
                            inp.value = text;
                            inp.dispatchEvent(new Event('input', { bubbles: true }));
                            inp.dispatchEvent(new Event('change', { bubbles: true }));
                            return true;
                        }
                    }
                    return false;
                }""", prompt_text)
                
                # Executa a pesquisa
                page.keyboard.press("Enter")
                page.wait_for_timeout(5000) # Esperar a pesquisa exibir os resultados
                
                print(f"➡️ [{step_name}] Clicando no botão principal 'Importar fontes'...")
                page.evaluate("""() => {
                    const btns = Array.from(document.querySelectorAll('button, md-filled-button, md-elevated-button, md-text-button'));
                    for(let b of btns) {
                        let txt = (b.textContent || '').toLowerCase();
                        if((txt.includes('importar fontes') || txt.includes('import sources')) && !b.disabled) {
                            b.click(); return true;
                        }
                    }
                    
                    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
                    let node;
                    while(node = walker.nextNode()) {
                        let txt = node.textContent.toLowerCase();
                        if(txt.includes('importar fonte') || txt.includes('import source')) {
                            let parent = node.parentElement;
                            while(parent && parent.tagName !== 'BUTTON' && !parent.tagName.includes('-BUTTON')) {
                                parent = parent.parentElement;
                            }
                            if(parent && !parent.disabled) { parent.click(); return true; }
                        }
                    }
                }""")
                
                print(f"⏳ [{step_name}] Processamento da pesquisa iniciado na nuvem...")
                page.wait_for_timeout(2000) # Apenas uma pausa leve antes do próximo ciclo

            # Executa a Sequência Completa
            do_search_and_import(prompt_deepsearch, "DeepSearch (Fonte 1)")
            
            do_search_and_import(prompt_deepresearch, "DeepResearch (Fonte 2)")
            
            print("✨ Sucesso Extremo! O NotebookLM concluiu o fluxo mestre avançado.")
            
        except Exception as e:
            print(f"❌ Automação falhou. Erro capturado:\n{e}")
            
        finally:
            print("🏁 Fechando script (A aba continuará aberta).")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso do script: python send_to_notebooklm.py <caminho_da_nota.md>")
        sys.exit(1)
    
    send_to_notebooklm(sys.argv[1])
