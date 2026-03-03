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

def extract_prompt_from_file(file_path, prompt_name):
    text = Path(file_path).read_text(encoding="utf-8")
    lines = text.split('\n')
    in_button = False
    is_target = False
    prompt_lines = []
    
    for line in lines:
        if line.strip() == '```button':
            in_button = True
            is_target = False
            prompt_lines = []
            continue
            
        if in_button:
            if line.startswith('name ') and prompt_name in line:
                is_target = True
                continue
            if line.startswith('type '):
                continue
            if line.startswith('action '):
                if is_target:
                    prompt_lines.append(line[7:])
                continue
                
            if line.strip() == '```':
                in_button = False
                if is_target:
                    return '\n'.join(prompt_lines).strip()
                continue
                
            if is_target:
                prompt_lines.append(line)
                
    return ""

def send_to_notebooklm(file_path):
    path = Path(file_path)
    if not path.exists():
        print(f"❌ Erro: Arquivo {file_path} não encontrado.")
        sys.exit(1)
        
    title = path.stem
    
    prompt_text = extract_prompt_from_file(file_path, 'DeepSearch')
    if not prompt_text:
        print(f"❌ Erro: Não foi possível encontrar o botão DeepSearch no arquivo {file_path}")
        sys.exit(1)

    prompt_deepsearch = prompt_text
    prompt_deepresearch = prompt_text
    
    prompt_genquest = extract_prompt_from_file(file_path, 'GenQuest')
    prompt_genquest_expert = extract_prompt_from_file(file_path, 'GenQuestExpert')
    
    # flag especial para ignorar as pesquisas do DeepSearch e focar apenas no Flashcards
    test_cards_only = "--test-cards" in sys.argv

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
            
            if test_cards_only:
                print("➡️ Modo --test-cards: Indo direto para o notebook hardcoded...")
                page.goto("https://notebooklm.google.com/notebook/a7970a7f-e08e-47bb-b725-1d4d119ecebb")
                page.wait_for_timeout(5000)
            else:
                page.goto("https://notebooklm.google.com/")
                page.wait_for_timeout(4000)
                
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
                
                # Modal de fontes abre...
                page.wait_for_timeout(3000)
                print("➡️ Pressionando 'Escape' para fechar a abinha inicial de fontes...")
                page.keyboard.press("Escape")
                page.wait_for_timeout(1000)
                
                print(f"➡️ Renomeando notebook para '{title}'...")
                
                # Tenta um "triple click" no título visível para focar e selecionar
                js_find_title = """() => {
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
                }"""
                box = page.evaluate(js_find_title)
                if box:
                    # Triple click para varrer tudo e selecionar o texto
                    page.mouse.click(box['x'], box['y'], click_count=3)
                    page.wait_for_timeout(500)
                    
                    # Digita no teclado naturalmente como um usuário (Angular capta isso)
                    page.keyboard.type(title, delay=20)
                    page.wait_for_timeout(500)
                    
                    # Tira o foco clicando no vazio
                    page.mouse.click(10, 10)
                    page.wait_for_timeout(1000)
                else:
                     print("⚠️ Untitled Notebook não encontrado para renomear.")
                
                # Escape de precaução caso o modal inicial esteja teimoso
                page.keyboard.press("Escape")
                page.wait_for_timeout(500)
            
            def do_search_and_import(prompt_text, step_name, wait_excluir=False, use_deep_research=False):
                print(f"➡️ [{step_name}] Clicando no botão de Adicionar Fonte...")
                
                # Clica no botão (+) ou "Adicionar fontes" 
                clicked_add = page.evaluate("""() => {
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
                    return false;
                }""")
                
                if not clicked_add:
                    print(f"⚠️ Aviso: Não conseguiu achar o botão Add Source. A tela de fontes já deve estar aberta.")
                
                page.wait_for_timeout(2000)
                
                print(f"⏳ [{step_name}] Aguardando a caixa web...")
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
                                    if(placeholder.includes('pesquise') || placeholder.includes('search') || placeholder.includes('web')) {
                                        if(!inp.disabled) {
                                            clearInterval(check);
                                            resolve(true);
                                            return;
                                        }
                                    }
                                }
                            }
                            if(attempts > 60) { clearInterval(check); resolve(false); }
                        }, 1000);
                    });
                }""")
                
                if wait_excluir:
                    print(f"⏳ [{step_name}] Verificando pesquisa anterior (Excluir)...")
                    page.evaluate("""() => {
                        return new Promise((resolve) => {
                            let attempts = 0;
                            let check = setInterval(() => {
                                attempts++;
                                const btns = Array.from(document.querySelectorAll('button, md-filled-button, md-elevated-button, md-text-button'));
                                for(let b of btns) {
                                    let txt = (b.textContent || '').toLowerCase().trim();
                                    if(txt === 'excluir' || txt === 'delete') {
                                        b.click();
                                        clearInterval(check);
                                        resolve(true);
                                        return;
                                    }
                                }
                                if(attempts >= 5) {
                                    clearInterval(check);
                                    resolve(false);
                                }
                            }, 1000);
                        });
                    }""")
                
                if use_deep_research:
                    print(f"➡️ [{step_name}] Mudando tipo para Deep Research...")
                    page.evaluate("""() => {
                        return new Promise((resolve) => {
                            const btns = Array.from(document.querySelectorAll('button, div[role="button"], md-text-button, md-outlined-button, md-filled-button'));
                            let clickedDropdown = false;
                            for(let b of btns) {
                                let txt = (b.textContent || '').toLowerCase().trim();
                                if(txt.includes('pesquisa rápida') || txt.includes('quick search')) {
                                    b.click();
                                    clickedDropdown = true;
                                    break;
                                }
                            }
                            if(!clickedDropdown) {
                                resolve(false);
                                return;
                            }
                            
                            setTimeout(() => {
                                const options = Array.from(document.querySelectorAll('md-menu-item, div[role="menuitem"], li, md-list-item, span'));
                                for(let opt of options) {
                                    let txt = (opt.textContent || '').toLowerCase();
                                    if((txt.includes('deep research') || txt.includes('pesquisa profunda')) && !txt.includes('pesquisa rápida')) {
                                        opt.click();
                                        resolve(true);
                                        return;
                                    }
                                }
                                resolve(false);
                            }, 1000);
                        });
                    }""")
                    page.wait_for_timeout(1000)

                print(f"➡️ [{step_name}] Preenchendo a caixa de pesquisa...")
                page.evaluate("""(text) => {
                    const inputs = document.querySelectorAll('input[type="text"], textarea');
                    for(let inp of inputs) {
                        let placeholder = (inp.getAttribute('placeholder') || '').toLowerCase();
                        if(placeholder.includes('pesquise') || placeholder.includes('search') || placeholder.includes('web')) {
                            inp.focus();
                            inp.value = '';
                            inp.value = text;
                            inp.dispatchEvent(new Event('input', { bubbles: true }));
                            inp.dispatchEvent(new Event('change', { bubbles: true }));
                            return true;
                        }
                    }
                    return false;
                }""", prompt_text)
                
                page.keyboard.press("Enter")
                print(f"⏳ [{step_name}] Aguardando a pesquisa concluir (esperando botão Importar habilitar)...")
                
                clicked_import = page.evaluate("""() => {
                    return new Promise((resolve) => {
                        let attempts = 0;
                        let check = setInterval(() => {
                            attempts++;
                            const btns = Array.from(document.querySelectorAll('button, md-filled-button, md-elevated-button, md-text-button'));
                            for(let b of btns) {
                                let txt = (b.textContent || '').toLowerCase();
                                if((txt.includes('importar') || txt.includes('import') || txt.includes('inserir')) && !txt.includes('fontes')) {
                                    if(!b.disabled && !b.hasAttribute('disabled')) {
                                        b.click();
                                        clearInterval(check);
                                        resolve(true);
                                        return;
                                    }
                                }
                            }
                            if(attempts >= 300) { // Timeout de 5 minutos
                                clearInterval(check);
                                resolve(false);
                            }
                        }, 1000);
                    });
                }""")
                
                if not clicked_import:
                    print(f"⚠️ Aviso: Botão Importar não foi clicado ou timeout de 5 minutos excedido.")
                
                print(f"⏳ [{step_name}] Importação rodando (15s)...")
                page.wait_for_timeout(15000) 

            if not test_cards_only:
                do_search_and_import(prompt_deepsearch, "DeepSearch (Fonte 1)")
                do_search_and_import(prompt_deepresearch, "DeepSearch (Fonte 2)", wait_excluir=True)
                do_search_and_import(prompt_deepsearch, "DeepResearch - Novo Tipo (Fonte 3)", wait_excluir=True, use_deep_research=True)
            else:
                print("⚠️ Modo --test-cards ativado. Pulando as importações de fontes.")
            
            # --- Etapa: Cartões Didáticos ---
            def do_flashcards(promptText, step_name):
                print(f"➡️ [{step_name}] Procurando lápis de 'Cartões didáticos'...")
                page.evaluate("""() => {
                    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
                    let node;
                    while(node = walker.nextNode()) {
                        let txt = node.textContent.trim().toLowerCase();
                        if(txt === 'cartões didáticos' || txt === 'flashcards' || txt.includes('cartões didáticos') || txt.includes('study guide')) {
                            let container = node.parentElement;
                            while(container && container.tagName !== 'BODY') {
                                const icons = container.querySelectorAll('.google-symbols, md-icon');
                                for(let icon of icons) {
                                    if(icon.textContent.includes('edit') || icon.textContent.includes('pencil') || icon.getAttribute('aria-label')?.includes('edit')) {
                                        let btn = icon.closest('button, md-icon-button, [role="button"]') || icon;
                                        btn.click();
                                        return true;
                                    }
                                }
                                container = container.parentElement;
                            }
                        }
                    }
                    return false;
                }""")
                page.wait_for_timeout(2000)
                
                print(f"➡️ [{step_name}] Configurando 'Número de cards' (menos) e 'Dificuldade' (difícil)...")
                page.evaluate("""() => {
                    const allButtons = Array.from(document.querySelectorAll('md-filter-chip, md-chip, button, div[role="button"], md-radio, label'));
                    for(let el of allButtons) {
                        let t = (el.textContent || '').trim().toLowerCase();
                        if(t === 'menos' || t === 'less') { el.click(); }
                        if(t === 'difícil' || t === 'hard' || t === 'dificult') { el.click(); }
                    }
                }""")
                page.wait_for_timeout(1000)
                
                print(f"➡️ [{step_name}] Colando o prompt e clicando em Salvar/Gerar...")
                page.evaluate("""(text) => {
                    const textareas = document.querySelectorAll('textarea');
                    let targetTa = null;
                    for(let ta of textareas) {
                        if(!ta.disabled && ta.getBoundingClientRect().height > 0) {
                            targetTa = ta;
                        }
                    }
                    if(targetTa) {
                        targetTa.focus();
                        targetTa.value = '';
                        targetTa.value = text;
                        targetTa.dispatchEvent(new Event('input', { bubbles: true }));
                        targetTa.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                }""", promptText)
                
                page.wait_for_timeout(1000)
                
                page.evaluate("""() => {
                    const btns = Array.from(document.querySelectorAll('button, md-filled-button, md-elevated-button, md-text-button'));
                    for(let b of btns) {
                        let txt = (b.textContent || '').trim().toLowerCase();
                        if(txt === 'salvar' || txt === 'save' || txt === 'gerar' || txt === 'generate' || txt === 'aplicar' || txt === 'apply') {
                            b.click();
                            return true;
                        }
                    }
                }""")
                print(f"⏳ [{step_name}] Aguardando 7s após salvar...")
                page.wait_for_timeout(7000)

            if prompt_genquest:
                do_flashcards(prompt_genquest, "Cartões Didáticos - GenQuest")
            if prompt_genquest_expert:
                do_flashcards(prompt_genquest_expert, "Cartões Didáticos - GenQuestExpert")
                
            print("✨ Sucesso Extremo com Cartões Didáticos!")
            
        except Exception as e:
            print(f"❌ Automação falhou. Erro capturado:\n{e}")
        finally:
            print("🏁 Fechando script (A aba continuará aberta).")

if __name__ == "__main__":
    import sys
    
    # Lida com o caso de múltiplos argumentos ou flags misturadas
    args = [arg for arg in sys.argv[1:] if not arg.startswith('--')]
    if not args:
        print("Uso do script: python send_to_notebooklm.py <caminho_da_nota.md> [--test-cards]")
        sys.exit(1)
        
    send_to_notebooklm(args[0])
