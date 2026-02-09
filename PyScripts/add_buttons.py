#!/usr/bin/env python3
"""
Script para adicionar botões (plugin Buttons) nos arquivos .md de Disciplinas.
Cada botão copia o prompt completo com valores preenchidos dinamicamente.
"""

import re
from pathlib import Path


def load_prompts(prompts_dir: Path) -> dict[str, str]:
    """Carrega os templates de prompts."""
    prompts = {}
    for prompt_file in prompts_dir.glob("*.md"):
        name = prompt_file.stem
        content = prompt_file.read_text(encoding="utf-8")
        # Remove os delimitadores ```markdown e ```
        content = re.sub(r'^```(?:markdown)?\n', '', content)
        content = re.sub(r'\n```\s*$', '', content)
        prompts[name] = content.strip()
    return prompts


def clean_name(name: str) -> str:
    """Remove prefixo numérico e extensão do nome."""
    name = re.sub(r'\.md$', '', name)
    name = re.sub(r'^\d+\.\s*', '', name)
    name = re.sub(r'-$', '', name)
    return name.strip()


def extract_code_block(content: str) -> str | None:
    """Extrai o conteúdo do code block logo após o frontmatter."""
    frontmatter_end = content.find('---', 4)
    if frontmatter_end == -1:
        return None
    
    after_frontmatter = content[frontmatter_end + 3:].lstrip()
    
    if after_frontmatter.startswith('```'):
        match = re.match(r'^```\n(.*?)\n```', after_frontmatter, re.DOTALL)
        if match:
            return match.group(1).strip()
    return None


def get_file_info(filepath: Path, base_dir: Path, content: str):
    """Extrai disciplina, assunto e tópico do arquivo."""
    rel_path = filepath.relative_to(base_dir)
    parts = list(rel_path.parts)
    
    code_block = extract_code_block(content)
    
    if len(parts) == 2:
        disciplina = clean_name(parts[0])
        assunto = clean_name(parts[1])
        topico = code_block if code_block else clean_name(parts[1])
        return disciplina, assunto, topico
    elif len(parts) >= 3:
        disciplina = clean_name(parts[0])
        assunto = clean_name(parts[1])
        topico = code_block if code_block else clean_name(filepath.stem)
        return disciplina, assunto, topico
    else:
        return None, None, None


def fill_prompt(template: str, disciplina: str, assunto: str, topico: str, prompt_name: str) -> str:
    """Preenche o template com os valores."""
    result = template
    
    if prompt_name == "DeepSearch":
        result = re.sub(r'Para todos os tópicos citados, sem outros assuntos, são eles: <>', 
                       f'Para todos os tópicos citados, sem outros assuntos, são eles: {topico}', result)
        result = re.sub(r'do assunto: <>', f'do assunto: {assunto}', result)
        result = re.sub(r'da disciplina: <>', f'da disciplina: {disciplina}', result)
    else:
        result = re.sub(r'Tópico\(s\) deste notebook \(Somente esses\):\s*$', 
                       f'Tópico(s) deste notebook (Somente esses):\n{topico}', result)
    
    return result


def generate_buttons(prompts: dict, disciplina: str, assunto: str, topico: str) -> str:
    """Gera os blocos de botões."""
    buttons = []
    
    button_config = [
        ("DeepSearch", "🔍 DeepSearch"),
        ("GenQuest", "📝 GenQuest"),
        ("GenQuestExpert", "📝 GenQuestExpert"),
        ("GenVid", "🎬 GenVid"),
        ("GenVidExpert", "🎬 GenVidExpert"),
        ("GenVidPersonalization", "🎨 GenVidPersonalization"),
    ]
    
    for prompt_name, button_label in button_config:
        if prompt_name in prompts:
            if prompt_name == "GenVidPersonalization":
                # Este não precisa de substituição
                filled = prompts[prompt_name]
            else:
                filled = fill_prompt(prompts[prompt_name], disciplina, assunto, topico, prompt_name)
            
            # Escapa backticks triplos no conteúdo para não quebrar o botão
            filled_escaped = filled.replace('```', '~~~')
            
            button = f"""```button
name {button_label}
type copy
action {filled_escaped}
```"""
            buttons.append(button)
    
    return "\n\n".join(buttons)


def process_file(filepath: Path, base_dir: Path, prompts: dict) -> str:
    """Processa um arquivo .md."""
    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception as e:
        return f"error: {e}"
    
    if not content.startswith('---'):
        return "skipped: sem frontmatter"
    
    disciplina, assunto, topico = get_file_info(filepath, base_dir, content)
    if not disciplina:
        return "skipped: estrutura inválida"
    
    # Remove seção antiga se existir
    content = re.sub(r'\n?## 📋 Prompts.*', '', content, flags=re.DOTALL).rstrip()
    
    # Gera botões
    buttons = generate_buttons(prompts, disciplina, assunto, topico)
    
    # Adiciona seção de botões
    new_content = content + "\n\n## 📋 Prompts\n\n" + buttons + "\n"
    
    filepath.write_text(new_content, encoding="utf-8")
    return "ok"


def main():
    base_dir = Path(__file__).parent.parent / "DailyLearning" / "Disciplinas"
    prompts_dir = Path(__file__).parent.parent / "DailyLearning" / "Prompts"
    
    if not base_dir.exists():
        print(f"❌ Diretório não encontrado: {base_dir}")
        return
    
    if not prompts_dir.exists():
        print(f"❌ Diretório de prompts não encontrado: {prompts_dir}")
        return
    
    print("📂 Carregando prompts...")
    prompts = load_prompts(prompts_dir)
    print(f"   Prompts: {list(prompts.keys())}")
    
    stats = {"ok": 0, "skipped": 0, "error": 0}
    
    print("\n🔘 Adicionando botões...\n")
    
    for md_file in base_dir.rglob("*.md"):
        result = process_file(md_file, base_dir, prompts)
        
        if result == "ok":
            stats["ok"] += 1
            print(f"✅ {md_file.name}")
        elif result.startswith("skipped"):
            stats["skipped"] += 1
        else:
            stats["error"] += 1
            print(f"❌ {md_file.name}: {result}")
    
    print(f"\n📊 Resumo:")
    print(f"   ✅ Com botões: {stats['ok']}")
    print(f"   ⏭️  Pulados: {stats['skipped']}")
    print(f"   ❌ Erros: {stats['error']}")


if __name__ == "__main__":
    main()
