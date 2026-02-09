#!/usr/bin/env python3
"""
Script para adicionar frontmatter padrão em arquivos .md que não possuem,
e também adicionar o campo NotebookLM com valor padrão.

Aplica-se apenas aos arquivos em DailyLearning/Disciplinas.
"""

import re
from pathlib import Path

DEFAULT_FRONTMATTER = """---
iniciado: false
primeiro_contato:
R1: false
R2: false
R3: false
R4: false
NotebookLM: "{notebooklm_value}"
---
"""


def has_frontmatter(content: str) -> bool:
    """Verifica se o conteúdo tem frontmatter YAML válido."""
    return bool(re.match(r"^---\n.*?\n---", content, re.DOTALL))


def get_title_from_filename(filepath: Path) -> str:
    """Extrai o título do nome do arquivo sem extensão."""
    return filepath.stem


def add_frontmatter(filepath: Path) -> str:
    """
    Adiciona frontmatter padrão a um arquivo .md que não possui.
    Retorna: 'added', 'skipped' (já tem frontmatter).
    """
    content = filepath.read_text(encoding="utf-8")
    
    if has_frontmatter(content):
        return "skipped"
    
    title = get_title_from_filename(filepath)
    notebooklm_value = f"[{title}](<linkdonotebooklm>)"
    
    frontmatter = DEFAULT_FRONTMATTER.format(notebooklm_value=notebooklm_value)
    new_content = frontmatter + "\n" + content.lstrip()
    
    filepath.write_text(new_content, encoding="utf-8")
    return "added"


def main():
    base_dir = Path(__file__).parent.parent / "DailyLearning" / "Disciplinas"
    
    if not base_dir.exists():
        print(f"Erro: Diretório não encontrado: {base_dir}")
        return
    
    stats = {"added": 0, "skipped": 0}
    
    for md_file in base_dir.rglob("*.md"):
        result = add_frontmatter(md_file)
        stats[result] += 1
        
        if result == "added":
            print(f"➕ Frontmatter adicionado: {md_file.name}")
        else:
            print(f"⏭️  Pulado (já tem frontmatter): {md_file.name}")
    
    print(f"\n📊 Resumo:")
    print(f"   ➕ Frontmatter adicionado: {stats['added']}")
    print(f"   ⏭️  Pulados (já tinham): {stats['skipped']}")


if __name__ == "__main__":
    main()
