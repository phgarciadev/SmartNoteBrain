#!/usr/bin/env python3
"""
Script para atualizar arquivos .md em Disciplinas/:
1. Remove a seção antiga '## 📋 Prompts Preenchidos' e todo conteúdo abaixo
2. Adiciona callouts com prompts preenchidos dinamicamente

Lógica de extração:
- Arquivo normal (dentro de subpasta): tópico = filename, assunto = pasta pai
- Arquivo especial (direto na disciplina): tópico = conteúdo do code block, assunto = filename
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
    # Remove extensão .md
    name = re.sub(r'\.md$', '', name)
    # Remove prefixo numérico como "1. " ou "10. "
    name = re.sub(r'^\d+\.\s*', '', name)
    # Remove "-" no final (alguns arquivos têm)
    name = re.sub(r'-$', '', name)
    return name.strip()


def extract_code_block(content: str) -> str | None:
    """Extrai o conteúdo do code block logo após o frontmatter."""
    # Encontra o fim do frontmatter
    frontmatter_end = content.find('---', 4)
    if frontmatter_end == -1:
        return None
    
    after_frontmatter = content[frontmatter_end + 3:].lstrip()
    
    # Verifica se começa com code block
    if after_frontmatter.startswith('```'):
        match = re.match(r'^```\n(.*?)\n```', after_frontmatter, re.DOTALL)
        if match:
            return match.group(1).strip()
    return None


def get_file_info(filepath: Path, base_dir: Path):
    """
    Extrai disciplina, assunto e tópico do arquivo.
    Retorna: (disciplina, assunto, topico, is_special)
    """
    content = filepath.read_text(encoding="utf-8")
    rel_path = filepath.relative_to(base_dir)
    parts = list(rel_path.parts)
    
    # Verifica se tem code block com tópicos
    code_block = extract_code_block(content)
    
    if len(parts) == 2:
        # Arquivo especial: diretamente na pasta da disciplina
        # Ex: Disciplinas/11. Artes/1. História da Arte.md
        disciplina = clean_name(parts[0])
        assunto = clean_name(parts[1])
        topico = code_block if code_block else clean_name(parts[1])
        return disciplina, assunto, topico, True
    elif len(parts) >= 3:
        # Arquivo normal: dentro de subpasta
        # Ex: Disciplinas/1. Língua Portuguesa/1. Leitura e Interpretação/1. Níveis.md
        disciplina = clean_name(parts[0])
        assunto = clean_name(parts[1])
        topico = code_block if code_block else clean_name(filepath.stem)
        return disciplina, assunto, topico, bool(code_block)
    else:
        return None, None, None, False


def remove_old_prompts(content: str) -> str:
    """Remove a seção antiga de prompts preenchidos."""
    # Remove tudo a partir de "## 📋 Prompts Preenchidos"
    pattern = r'\n?## 📋 Prompts Preenchidos.*'
    return re.sub(pattern, '', content, flags=re.DOTALL).rstrip() + '\n'


def generate_callouts(prompts: dict, disciplina: str, assunto: str, topico: str) -> str:
    """Gera os callouts com prompts preenchidos."""
    callouts = []
    
    # DeepSearch - formato especial
    if 'DeepSearch' in prompts:
        ds_content = prompts['DeepSearch']
        ds_content = re.sub(r'Para todos os tópicos citados, sem outros assuntos, são eles: <>', 
                           f'Para todos os tópicos citados, sem outros assuntos, são eles: {topico}', ds_content)
        ds_content = re.sub(r'do assunto: <>', f'do assunto: {assunto}', ds_content)
        ds_content = re.sub(r'da disciplina: <>', f'da disciplina: {disciplina}', ds_content)
        callouts.append(f"> [!example]- 🔍 DeepSearch\n> ```\n> {ds_content}\n> ```")
    
    # GenQuest
    if 'GenQuest' in prompts:
        gq_content = prompts['GenQuest']
        gq_content = re.sub(r'Tópico\(s\) deste notebook \(Somente esses\):\s*$', 
                           f'Tópico(s) deste notebook (Somente esses):\n{topico}', gq_content)
        callouts.append(f"> [!example]- 📝 GenQuest\n> ```\n> {gq_content}\n> ```")
    
    # GenQuestExpert
    if 'GenQuestExpert' in prompts:
        gqe_content = prompts['GenQuestExpert']
        gqe_content = re.sub(r'Tópico\(s\) deste notebook \(Somente esses\):\s*$', 
                            f'Tópico(s) deste notebook (Somente esses):\n{topico}', gqe_content)
        callouts.append(f"> [!example]- 📝 GenQuestExpert\n> ```\n> {gqe_content}\n> ```")
    
    # GenVid
    if 'GenVid' in prompts:
        gv_content = prompts['GenVid']
        gv_content = re.sub(r'Tópico\(s\) deste notebook \(Somente esses\):\s*$', 
                           f'Tópico(s) deste notebook (Somente esses):\n{topico}', gv_content)
        callouts.append(f"> [!example]- 🎬 GenVid\n> ```\n> {gv_content}\n> ```")
    
    # GenVidExpert
    if 'GenVidExpert' in prompts:
        gve_content = prompts['GenVidExpert']
        gve_content = re.sub(r'Tópico\(s\) deste notebook \(Somente esses\):\s*$', 
                            f'Tópico(s) deste notebook (Somente esses):\n{topico}', gve_content)
        callouts.append(f"> [!example]- 🎬 GenVidExpert\n> ```\n> {gve_content}\n> ```")
    
    # GenVidPersonalization - copia a mesma referência para todos
    if 'GenVidPersonalization' in prompts:
        gvp_content = prompts['GenVidPersonalization']
        callouts.append(f"> [!example]- 🎨 GenVidPersonalization\n> ```\n> {gvp_content}\n> ```")
    
    return "\n\n".join(callouts)


def process_file(filepath: Path, base_dir: Path, prompts: dict) -> str:
    """Processa um arquivo .md. Retorna status."""
    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception as e:
        return f"error: {e}"
    
    # Verifica se tem frontmatter
    if not content.startswith('---'):
        return "skipped: sem frontmatter"
    
    disciplina, assunto, topico, is_special = get_file_info(filepath, base_dir)
    if not disciplina:
        return "skipped: estrutura inválida"
    
    # Remove prompts antigos
    content = remove_old_prompts(content)
    
    # Gera novos callouts
    callouts = generate_callouts(prompts, disciplina, assunto, topico)
    
    # Adiciona seção no final
    new_content = content + "\n## 📋 Prompts Preenchidos\n\n" + callouts + "\n"
    
    filepath.write_text(new_content, encoding="utf-8")
    
    return f"ok (special)" if is_special else "ok"


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
    print(f"   Prompts carregados: {list(prompts.keys())}")
    
    stats = {"ok": 0, "ok (special)": 0, "skipped": 0, "error": 0}
    
    print("\n📝 Processando arquivos...\n")
    
    for md_file in base_dir.rglob("*.md"):
        result = process_file(md_file, base_dir, prompts)
        
        if result == "ok":
            stats["ok"] += 1
            print(f"✅ {md_file.name}")
        elif result == "ok (special)":
            stats["ok (special)"] += 1
            print(f"✅ {md_file.name} (code block)")
        elif result.startswith("skipped"):
            stats["skipped"] += 1
            print(f"⏭️  {md_file.name}: {result}")
        else:
            stats["error"] += 1
            print(f"❌ {md_file.name}: {result}")
    
    print(f"\n📊 Resumo:")
    print(f"   ✅ Atualizados (normal): {stats['ok']}")
    print(f"   ✅ Atualizados (special): {stats['ok (special)']}")
    print(f"   ⏭️  Pulados: {stats['skipped']}")
    print(f"   ❌ Erros: {stats['error']}")


if __name__ == "__main__":
    main()
