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
    button_type = None
    prompt_lines = []
    
    for line in lines:
        if line.strip() == '```button':
            in_button = True
            is_target = False
            button_type = None
            prompt_lines = []
            continue
            
        if in_button:
            if line.startswith('name ') and prompt_name in line:
                is_target = True
                continue
            if line.startswith('type '):
                button_type = line[5:].strip()
                continue
            if line.startswith('action '):
                if is_target and button_type == 'copy':
                    prompt_lines.append(line[7:])
                continue
                
            if line.strip() == '```':
                in_button = False
                if is_target and button_type == 'copy':
                    return '\n'.join(prompt_lines).strip()
                continue
                
            if is_target and button_type == 'copy':
                prompt_lines.append(line)
                
    return ""

def send_to_notebooklm(file_path):
    import re
    path = Path(file_path)
    if not path.exists():
        print(f"❌ Erro: Arquivo {file_path} não encontrado.")
        sys.exit(1)
        
    title = path.stem
    try:
        parts = path.parts
        if "Disciplinas" in parts:
            idx = parts.index("Disciplinas")
            rel_parts = parts[idx+1:]
            
            nums = []
            for p in rel_parts:
                m = re.match(r'^(\d+)\.', p)
                if m:
                    nums.append(m.group(1))
            
            if nums:
                clean_name = re.sub(r'^\d+\.\s*', '', title).strip()
                title = f"{'.'.join(nums)} - {clean_name}"
    except Exception as e:
        print(f"⚠️ Aviso: Não foi possível estruturar o título hierárquico. Usando o original ({title}). Erro: {e}")

    
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
    test_video_only = "--test-video" in sys.argv
    
    only_genquest = "--only-genquest" in sys.argv
    only_genquest_expert = "--only-genquest-expert" in sys.argv
    only_genvid = "--only-genvid" in sys.argv
    only_genvid_expert = "--only-genvid-expert" in sys.argv
    only_search = "--only-search" in sys.argv
    only_deepresearch = "--only-deepresearch" in sys.argv
    is_specific_action = only_genquest or only_genquest_expert or only_genvid or only_genvid_expert or only_search or only_deepresearch
    
    saved_url = None
    text = path.read_text(encoding="utf-8")
    import re
    match = re.search(r'^NotebookLM:\s*"?([^"\n]+)"?', text, flags=re.MULTILINE | re.IGNORECASE)
    if match:
        extracted = match.group(1).strip()
        if "https://notebooklm.google.com" in extracted:
            # Pega exatamente a URL caso ela esteja misturada com colchetes ou outras coisas
            url_match = re.search(r'(https://notebooklm\.google\.com[^\s>\]"\']+)', extracted)
            if url_match:
                saved_url = url_match.group(1)
        
    if is_specific_action:
        if not saved_url:
            print("❌ Erro: Não encontrei a URL do NotebookLM no frontmatter. Execute a geração completa primeiro.")
            sys.exit(1)
    elif not test_cards_only and not test_video_only:
        # Modo completo
        if saved_url:
            print(f"⚠️ Aviso: Este notebook já possui um link válido ({saved_url}). Execução completa abortada.")
            sys.exit(0)
    
    prompt_genvid = extract_prompt_from_file(file_path, 'GenVid')
    prompt_genvid_expert = extract_prompt_from_file(file_path, 'GenVidExpert')
    prompt_genvid_pers = extract_prompt_from_file(file_path, 'GenVidPersonalization')

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
            
            if is_specific_action and saved_url:
                print(f"➡️ Modo de ação específica ativado: Indo direto para o notebook salvo: {saved_url} ...")
                page.goto(saved_url)
                page.wait_for_timeout(5000)
            elif test_cards_only or test_video_only:
                print("➡️ Modo de teste ativado: Indo direto para o notebook hardcoded...")
                page.goto("https://notebooklm.google.com/notebook/a7970a7f-e08e-47bb-b725-1d4d119ecebb")
                page.wait_for_timeout(5000)
            else:
                page.goto("https://notebooklm.google.com/")
                #MVP3
                print("⏳ Aguardando a página inicial carregar (pesquisando botão de Criar/Novo notebook)...")
                js_click_new = """() => {
                    return new Promise((resolve) => {
                        let attempts = 0;
                        let check = setInterval(() => {
                            attempts++;
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
                                    if(parent && parent.tagName !== 'BODY' && !parent.disabled && parent.offsetWidth > 0) { 
                                        parent.click(); 
                                        clearInterval(check);
                                        resolve(true); 
                                        return; 
                                    }
                                }
                            }
                            
                            const btn = document.querySelector('md-elevated-button, button.mat-mdc-unelevated-button');
                            if(btn && !btn.disabled && btn.offsetWidth > 0) { 
                                btn.click(); 
                                clearInterval(check);
                                resolve(true); 
                                return; 
                            }
                            
                            if (attempts >= 90) { // Timeout de 45 segundos
                                clearInterval(check);
                                resolve(false);
                            }
                        }, 500);
                    });
                }"""
                page.evaluate(js_click_new)
                
                # Tempo adicional pro modal de adicionar fontes ser renderizado após clicar
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
                
                # JÁ CAPTURAMOS A URL AGORA E SALVAMOS NO FRONTMATTER
                url_final = page.url
                print(f"🔗 URL Inicial do Notebook: {url_final}")
                
                try:
                    import re
                    text = path.read_text(encoding="utf-8")
                    if text.startswith("---"):
                        parts = text.split("---", 2)
                        if len(parts) >= 3:
                            frontmatter = parts[1]
                            if re.search(r'^NotebookLM:.*$', frontmatter, flags=re.MULTILINE | re.IGNORECASE):
                                new_frontmatter = re.sub(r'^NotebookLM:.*$', f'NotebookLM: "{url_final}"', frontmatter, flags=re.MULTILINE | re.IGNORECASE)
                            else:
                                if not frontmatter.endswith('\n'):
                                    frontmatter += '\n'
                                new_frontmatter = frontmatter + f'NotebookLM: "{url_final}"\n'
                                
                            new_text = f"---{new_frontmatter}---" + parts[2]
                            path.write_text(new_text, encoding="utf-8")
                            print("📝 URL salva com sucesso no frontmatter do arquivo.")
                except Exception as e:
                    print(f"⚠️ Aviso: Não foi possível salvar a URL no frontmatter. Erro: {e}")
            
            def do_search_and_import(prompt_text, step_name, use_deep_research=False):
                print(f"➡️ [{step_name}] Clicando no botão de Adicionar Fonte...")
                
                # Clica no botão (+) ou "Adicionar fontes" 
                clicked_add = page.evaluate("""() => {
                    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
                    let node;
                    while(node = walker.nextNode()) {
                        let txt = node.textContent.trim().toLowerCase();
                        if(txt.includes('adicionar fonte') || txt.includes('add source') || txt === 'web' || txt === 'site' || txt === 'sites') {
                            let parent = node.parentElement;
                            while(parent && parent.tagName !== 'BUTTON' && !parent.tagName.includes('-BUTTON') && parent.getAttribute('role') !== 'button') {
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
                
                print(f"⏳ [{step_name}] Aguardando a caixa web...")
                liberado = page.evaluate("""() => {
                    return new Promise((resolve) => {
                        let attempts = 0;
                        let check = setInterval(() => {
                            attempts++;
                            let bodyText = document.body.textContent.toLowerCase();
                            if(!bodyText.includes('temporariamente desativada') && !bodyText.includes('temporarily disabled')) {
                                const inputs = document.querySelectorAll('input, textarea');
                                for(let inp of inputs) {
                                    let placeholder = (inp.getAttribute('placeholder') || '').toLowerCase();
                                    let aria = (inp.getAttribute('aria-label') || '').toLowerCase();
                                    if(placeholder.includes('pesquise') || placeholder.includes('search') || placeholder.includes('web') || aria.includes('pesquise')) {
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
                
                print(f"➡️ [{step_name}] Preenchendo a caixa de pesquisa...")
                page.evaluate("""(text) => {
                    const inputs = document.querySelectorAll('input, textarea');
                    for(let inp of inputs) {
                        let placeholder = (inp.getAttribute('placeholder') || '').toLowerCase();
                        let aria = (inp.getAttribute('aria-label') || '').toLowerCase();
                        if(placeholder.includes('pesquise') || placeholder.includes('search') || placeholder.includes('web') || aria.includes('pesquise')) {
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
                
                page.wait_for_timeout(500)
                #MVP2
                if use_deep_research:
                    print(f"➡️ [{step_name}] Fechando modal central para focar na aba esquerda...")
                    page.keyboard.press("Escape")
                    page.wait_for_timeout(1000)
                    
                    print(f"➡️ [{step_name}] Mudando tipo para Deep Research...")
                    try:
                        # Usando locators dinâmicos do Playwright pois eles disparam eventos completos (click/mouse)
                        # o que é vital para o Angular Material (framework do NotebookLM) atualizar de fato.
                        
                        # Clicar no dropdown "Pesquisa rápida" (pegamos o primeiro que representa a aba lateral, em vez do modal central que fica no topo do z-index)
                        dropdown = page.locator("text=/Pesquisa r[áa]pida|Quick search/i").locator("visible=true").first
                        dropdown.click(timeout=5000)
                        page.wait_for_timeout(1000)
                        
                        # Clicar na opção "Deep Research" - Usando uma estratégia mais agressiva
                        print(f"➡️ [{step_name}] Selecionando opção 'Deep Research' no menu...")
                        
                        # 1. Tenta via Locator padrão do Playwright (mais seguro se funcionar)
                        try:
                            deep_option = page.locator("[role='menuitem']").filter(has_text=re.compile(r"Deep Research", re.I)).locator("visible=true").first
                            deep_option.click(timeout=3000)
                        except:
                            # 2. Fallback para Javascript caso o locator falhe (Material menus podem ser chatos)
                            print(f"🔄 [{step_name}] Fallback: Tentando selecionar 'Deep Research' via JS...")
                            page.evaluate("""() => {
                                const items = Array.from(document.querySelectorAll('[role="menuitem"], .mat-mdc-menu-item, button, span'));
                                for (let item of items) {
                                    if (item.textContent.includes('Deep Research')) {
                                        item.click();
                                        return true;
                                    }
                                }
                                return false;
                            }""")
                        
                        page.wait_for_timeout(1500)
                    except Exception as e:
                        print(f"⚠️ Aviso: Falha ao mudar para Deep Research: {e}")
                    
                    # Garantir que a perda de foco não impeça a submissão (Enter)
                    print(f"➡️ [{step_name}] Refocando a caixa de pesquisa...")
                    page.evaluate("""() => {
                        const inputs = document.querySelectorAll('input, textarea');
                        for(let inp of inputs) {
                            let placeholder = (inp.getAttribute('placeholder') || '').toLowerCase();
                            let aria = (inp.getAttribute('aria-label') || '').toLowerCase();
                            if(placeholder.includes('pesquise') || placeholder.includes('search') || placeholder.includes('web') || aria.includes('pesquise')) {
                                inp.focus();
                                return true;
                            }
                        }
                    }""")
                    page.wait_for_timeout(500)
                
                print(f"➡️ [{step_name}] Enviando termo de pesquisa (Enter/Submit)...")
                page.keyboard.press("Enter")
                page.wait_for_timeout(500)
                
                # Clica alternativamente na setinha azul de pesquisar (submit) caso o Enter resulte em nada.
                page.evaluate("""() => {
                    const icons = Array.from(document.querySelectorAll('.google-symbols, md-icon'));
                    for(let icon of icons) {
                        if(icon.textContent.includes('arrow_forward')) {
                            let btn = icon.closest('button, [role="button"], md-icon-button, md-filled-icon-button');
                            if (btn && !btn.disabled && btn.offsetWidth > 0) {
                                btn.click();
                            }
                        }
                    }
                }""")
                
                print(f"⏳ [{step_name}] Aguardando a pesquisa concluir (esperando botão Importar habilitar)...")
                
                clicked_import = page.evaluate("""() => {
                    return new Promise((resolve) => {
                        let attempts = 0;
                        const check = setInterval(() => {
                            attempts++;
                            
                            // 1. Busca ampla por botões ou elementos que contêm o texto de importação
                            const allElements = Array.from(document.querySelectorAll('button, md-filled-button, md-elevated-button, md-text-button, [role="button"], .mat-mdc-button, .mdc-button, div, span'));
                            
                            for(let el of allElements) {
                                let txt = (el.textContent || '').trim().toLowerCase();
                                // Se o texto contém exatamente "+ importar" ou "importar" e é visível
                                if((txt === 'importar' || txt === '+ importar' || (txt.includes('importar') && !txt.includes('fontes'))) && el.offsetWidth > 0) {
                                    
                                    // Sobe para achar o elemento clicável caso seja um span/div interno
                                    let clickable = el;
                                    let depth = 0;
                                    while(clickable && depth < 5) {
                                        const style = window.getComputedStyle(clickable);
                                        if(clickable.tagName === 'BUTTON' || clickable.getAttribute('role') === 'button' || style.cursor === 'pointer' || clickable.tagName.includes('-BUTTON')) {
                                            if(!clickable.disabled && !clickable.hasAttribute('disabled')) {
                                                console.log('✅ Botão Importar/Inserir encontrado e clicado:', txt);
                                                clickable.click();
                                                
                                                // Dispara eventos manuais para garantir que o framework (Angular) sinta o clique
                                                clickable.dispatchEvent(new MouseEvent('mousedown', {bubbles: true}));
                                                clickable.dispatchEvent(new MouseEvent('mouseup', {bubbles: true}));
                                                
                                                clearInterval(check);
                                                resolve(true);
                                                return;
                                            }
                                        }
                                        clickable = clickable.parentElement;
                                        depth++;
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
                    print(f"❌ Erro Crítico: Botão Importar não foi clicado no tempo limite. Abortando para evitar erros na pipeline.")
                    sys.exit(1)
                
                # Aguarda um pouco para o loader (SVG animado ou spinner) dar as caras
                print(f"⏳ [{step_name}] Clique realizado. Aguardando 2s para início do processamento...")
                page.wait_for_timeout(2000)
                
                print(f"⏳ [{step_name}] Importação em curso. Aguardando indicadores de carregamento (incluindo SVGs animados) sumirem...")
                loading_done = page.evaluate("""() => {
                    return new Promise((resolve) => {
                        let stableCount = 0;
                        let attempts = 0;
                        const STABLE_THRESHOLD = 5; // ~2.5s de estabilidade
                        const MAX_ATTEMPTS = 600;   // 5 min timeout
                        
                        const check = setInterval(() => {
                            attempts++;
                            
                            // 1. Loaders tradicionais
                            const loaders = Array.from(document.querySelectorAll(
                                'md-circular-progress, md-linear-progress, ' +
                                '[role="progressbar"], ' +
                                'mat-spinner, mat-progress-bar, mat-progress-spinner, ' +
                                '.mat-mdc-progress-spinner, .mdc-circular-progress'
                            ));
                            
                            let hasVisibleLoader = false;
                            for (const el of loaders) {
                                const rect = el.getBoundingClientRect();
                                const style = window.getComputedStyle(el);
                                if (rect.width > 0 && rect.height > 0 && style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0') {
                                    hasVisibleLoader = true;
                                    break;
                                }
                            }
                            
                            // 2. "SVGs animados" (Detecção de rotação ou tags animate)
                            if (!hasVisibleLoader) {
                                const svgs = document.querySelectorAll('svg');
                                for (const svg of svgs) {
                                    const rect = svg.getBoundingClientRect();
                                    const style = window.getComputedStyle(svg);
                                    
                                    // Se o SVG está visível e parece estar animando
                                    if (rect.width > 0 && rect.height > 1 && style.display !== 'none' && style.visibility !== 'hidden') {
                                        const hasAnimateTag = svg.querySelector('animate, animateTransform, animateMotion');
                                        const hasRotationCSS = style.animationName && style.animationName !== 'none';
                                        
                                        // No NotebookLM, loaders de fonte costumam ser SVGs que rodam ou pulsam
                                        if (hasAnimateTag || hasRotationCSS) {
                                            hasVisibleLoader = true;
                                            break;
                                        }
                                    }
                                }
                            }
                            
                            if (!hasVisibleLoader) {
                                stableCount++;
                                if (stableCount >= STABLE_THRESHOLD) {
                                    clearInterval(check);
                                    resolve(true);
                                    return;
                                }
                            } else {
                                stableCount = 0; // Ainda carregando...
                            }
                            
                            if (attempts >= MAX_ATTEMPTS) {
                                clearInterval(check);
                                resolve(false);
                            }
                        }, 500);
                    });
                }""")
                
                if loading_done:
                    print(f"✅ [{step_name}] Todos os indicadores de carregamento sumiram. Pronto para a próxima ação.")
                else:
                    print(f"⚠️ [{step_name}] Timeout de 5 minutos atingido aguardando carregamentos. Prosseguindo...")

            if not test_cards_only and not test_video_only and not is_specific_action:
                do_search_and_import(prompt_deepsearch, "DeepSearch (Fonte 1)")
                do_search_and_import(prompt_deepresearch, "DeepSearch (Fonte 2)")
                
                # Recarrega a página antes da 3ª pesquisa (Deep Research)
                print("🔄 Recarregando a página antes da pesquisa Deep Research...")
                
                # Traz a página para frente e clica em uma região neutra para forçar o browser 
                # a tirar a tab de "background throttle" (engasgo de inatividade)
                try:
                    page.bring_to_front()
                    page.mouse.click(10, 10)
                except:
                    pass
                
                try:    
                    page.reload(timeout=15000, wait_until="commit")
                except Exception as e:
                    print(f"⚠️ Aviso ao recarregar aba: {e}")
                
                # Outro clique para garantir que a página renderize e continue o onLoad
                try: page.mouse.click(10, 50)
                except: pass
                
                try: page.wait_for_load_state("domcontentloaded", timeout=10000)
                except: pass
                
                page.wait_for_timeout(3000)
                
                print("➡️ Tentando fechar modal central pós-recarga (Escape / Clique)...")
                try:
                    page.keyboard.press("Escape")
                    page.wait_for_timeout(500)
                    page.mouse.click(5, 5) # Clique na quina fora do modal
                    page.wait_for_timeout(500)
                    page.keyboard.press("Escape")
                    page.wait_for_timeout(500)
                    page.evaluate("""() => {
                        const icons = Array.from(document.querySelectorAll('.google-symbols, md-icon'));
                        for(let icon of icons) {
                            if(icon.textContent.includes('close') || icon.textContent.includes('clear')) {
                                let btn = icon.closest('button, [role="button"], md-icon-button');
                                if (btn && !btn.disabled && btn.offsetWidth > 0) {
                                    btn.click();
                                }
                            }
                        }
                    }""")
                    page.wait_for_timeout(1000)
                except Exception as e:
                    print(f"⚠️ Erro ao tentar fechar modal: {e}")

                print("⏳ Aguardando a página estabilizar após recarga...")
                page.evaluate("""() => {
                    return new Promise((resolve) => {
                        let stableCount = 0;
                        let attempts = 0;
                        const check = setInterval(() => {
                            attempts++;
                            const loaders = Array.from(document.querySelectorAll(
                                'md-circular-progress, md-linear-progress, ' +
                                '[role="progressbar"], ' +
                                'mat-spinner, mat-progress-bar, mat-progress-spinner, ' +
                                '.mat-mdc-progress-spinner, .mdc-circular-progress'
                            ));
                            let hasLoader = false;
                            for (const el of loaders) {
                                const rect = el.getBoundingClientRect();
                                const style = window.getComputedStyle(el);
                                if (rect.width > 0 && rect.height > 0 && 
                                    style.display !== 'none' && 
                                    style.visibility !== 'hidden' &&
                                    style.opacity !== '0') {
                                    hasLoader = true;
                                    break;
                                }
                            }
                            if (!hasLoader) {
                                stableCount++;
                                if (stableCount >= 4) { clearInterval(check); resolve(true); return; }
                            } else { stableCount = 0; }
                            if (attempts >= 120) { clearInterval(check); resolve(false); }
                        }, 500);
                    });
                }""")
                print("✅ Página recarregada e estabilizada. Iniciando Deep Research...")
                
                do_search_and_import(prompt_deepsearch, "DeepResearch - Novo Tipo (Fonte 3)", use_deep_research=True)
            elif only_search or only_deepresearch:
                if only_search:
                    do_search_and_import(prompt_deepsearch, "Só Search (Fonte 1)")
                if only_deepresearch:
                    print("🔄 Estabilizando página para Deep Research isolado...")
                    try:
                        page.bring_to_front()
                        page.mouse.click(10, 10)
                        page.wait_for_timeout(1000)
                        page.keyboard.press("Escape") # Fecha o modal central se existir
                        page.wait_for_timeout(1000)
                    except: pass
                    
                    do_search_and_import(prompt_deepsearch, "Só DeepResearch (Fonte 3)", use_deep_research=True)
            else:
                print("⚠️ Modo de teste ou ação única ativado. Pulando as importações de fontes.")
            
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

            if not test_video_only and not only_genvid and not only_genvid_expert:
                if prompt_genquest and (not is_specific_action or only_genquest):
                    do_flashcards(prompt_genquest, "Cartões Didáticos - GenQuest")
                if prompt_genquest_expert and (not is_specific_action or only_genquest_expert):
                    do_flashcards(prompt_genquest_expert, "Cartões Didáticos - GenQuestExpert")
                    
                print("✨ Sucesso Extremo com Cartões Didáticos!")
            
            # --- Etapa: Resumo em Vídeo ---
            def do_video(prompt_video, prompt_pers, step_name):
                print(f"➡️ [{step_name}] Procurando botão de 'Resumo em Vídeo'...")
                page.evaluate("""() => {
                    const allButtons = Array.from(document.querySelectorAll('button, div[role="button"], md-text-button, md-elevated-button, md-outlined-button, md-filled-button, div.card, div'));
                    for(let el of allButtons) {
                        let t = (el.textContent || '').trim().toLowerCase();
                        if(t === 'resumo em vídeo' || t === 'video overview') {
                            if(el.tagName === 'BUTTON' || el.getAttribute('role') === 'button' || el.tagName.includes('-BUTTON')) {
                                el.click(); 
                                return true;
                            }
                        }
                    }
                
                    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
                    let node;
                    while(node = walker.nextNode()) {
                        let txt = node.textContent.trim().toLowerCase();
                        if(txt === 'resumo em vídeo' || txt === 'video overview' || txt.includes('resumo em vídeo')) {
                            let parent = node.parentElement;
                            let btn = parent.closest('button, [role="button"], md-filled-button, md-elevated-button');
                            if(btn) { btn.click(); return true; }
                            parent.click();
                            return true;
                        }
                    }
                    return false;
                }""")
                page.wait_for_timeout(2000)
                
                print(f"➡️ [{step_name}] Selecionando 'Personalizado'...")
                page.evaluate("""() => {
                    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
                    let node;
                    while(node = walker.nextNode()) {
                        let txt = node.textContent.trim().toLowerCase();
                        if(txt === 'personalizado' || txt === 'custom') {
                            let parent = node.parentElement;
                            let btn = parent.closest('button, [role="button"], div.card, md-radio');
                            if(btn) { btn.click(); return true; }
                            parent.click();
                            return true;
                        }
                    }
                    return false;
                }""")
                page.wait_for_timeout(1000)
                
                print(f"➡️ [{step_name}] Colando prompts de vídeo...")
                page.evaluate("""(data) => {
                    const textareas = Array.from(document.querySelectorAll('textarea')).filter(ta => !ta.disabled && ta.getBoundingClientRect().height > 0);
                    
                    let taPers = null;
                    let taVideo = null;
                    
                    for (let ta of textareas) {
                        let parentText = (ta.parentElement?.parentElement?.parentElement?.textContent || '').toLowerCase();
                        let placeholder = (ta.getAttribute('placeholder') || '').toLowerCase();
                        let ariaLabel = (ta.getAttribute('aria-label') || '').toLowerCase();
                        
                        let combined = parentText + " " + placeholder + " " + ariaLabel;
                        
                        if (combined.includes('estilo visual') || combined.includes('visual style')) {
                             taPers = ta;
                        } else if (combined.includes('apresentadores') || combined.includes('concentrar') || combined.includes('focus') || combined.includes('presenters') || combined.includes('aspectos')) {
                             taVideo = ta;
                        }
                    }
                    
                    if(taPers) {
                        taPers.focus();
                        taPers.value = '';
                        taPers.value = data.pers;
                        taPers.dispatchEvent(new Event('input', { bubbles: true }));
                        taPers.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                    if(taVideo) {
                        taVideo.focus();
                        taVideo.value = '';
                        taVideo.value = data.video;
                        taVideo.dispatchEvent(new Event('input', { bubbles: true }));
                        taVideo.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                    
                    if (!taPers && !taVideo && textareas.length >= 2) {
                        textareas[0].focus();
                        textareas[0].value = '';
                        textareas[0].value = data.pers;
                        textareas[0].dispatchEvent(new Event('input', { bubbles: true }));
                        textareas[0].dispatchEvent(new Event('change', { bubbles: true }));
                        
                        textareas[1].focus();
                        textareas[1].value = '';
                        textareas[1].value = data.video;
                        textareas[1].dispatchEvent(new Event('input', { bubbles: true }));
                        textareas[1].dispatchEvent(new Event('change', { bubbles: true }));
                    }
                }""", {"pers": prompt_pers, "video": prompt_video})
                
                page.wait_for_timeout(1000)
                
                print(f"➡️ [{step_name}] Clicando em Gerar/Criar...")
                page.evaluate("""() => {
                    const btns = Array.from(document.querySelectorAll('button, md-filled-button, md-elevated-button, md-text-button'));
                    for(let b of btns) {
                        let txt = (b.textContent || '').trim().toLowerCase();
                        if(txt === 'gerar' || txt === 'generate' || txt === 'salvar' || txt === 'apply' || txt === 'criar' || txt === 'create') {
                            if (!b.disabled && !b.hasAttribute('disabled')) {
                                b.click();
                                return true;
                            }
                        }
                    }
                }""")
                print(f"⏳ [{step_name}] Aguardando 10s após gerar...")
                page.wait_for_timeout(10000)

            if not test_cards_only and not only_genquest and not only_genquest_expert:
                if prompt_genvid and prompt_genvid_pers and (not is_specific_action or only_genvid):
                    do_video(prompt_genvid, prompt_genvid_pers, "Vídeo - GenVid")
                if prompt_genvid_expert and prompt_genvid_pers and (not is_specific_action or only_genvid_expert):
                    do_video(prompt_genvid_expert, prompt_genvid_pers, "Vídeo - GenVidExpert")
    
                print("✨ Sucesso Extremo com Vídeos!")
            
            if not is_specific_action and not test_cards_only and not test_video_only:
                print("✨ Fluxo de automação finalizado!")
            
        except Exception as e:
            print(f"❌ Automação falhou. Erro capturado:\n{e}")
        finally:
            print("🏁 Fechando script (A aba continuará aberta).")

if __name__ == "__main__":
    import sys
    
    # Lida com o caso de múltiplos argumentos ou flags misturadas
    args = [arg for arg in sys.argv[1:] if not arg.startswith('--')]
    if not args:
        print("Uso do script: python send_to_notebooklm.py <caminho_da_nota.md> [--test-cards] [--test-video]")
        sys.exit(1)
        
    send_to_notebooklm(args[0])
