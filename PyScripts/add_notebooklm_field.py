#!/usr/bin/env python3
"""
Script para adicionar campo NotebookLM com valor padrão em todos os .md
do diretório DailyLearning/Disciplinas.

Formato: NotebookLM: "[Título do arquivo](<linkdonotebooklm>)"
"""

import os
import re
from pathlib import Path


def get_title_from_filename(filepath: Path) -> str:
    """Extrai o título do nome do arquivo sem extensão."""
    return filepath.stem


def add_notebooklm_field(filepath: Path) -> str:
    """
    Adiciona ou preenche o campo NotebookLM ao frontmatter YAML de um arquivo .md.
    Retorna: 'added', 'filled', 'skipped', ou 'no_frontmatter'.
    """
    content = filepath.read_text(encoding="utf-8")
    
    # Verifica se tem frontmatter YAML (---...---)
    frontmatter_pattern = re.compile(r"^---\n(.*?)\n---", re.DOTALL)
    match = frontmatter_pattern.match(content)
    
    if not match:
        return "no_frontmatter"
    
    title = get_title_from_filename(filepath)
    default_value = f'"[{title}](<linkdonotebooklm>)"'
    
    frontmatter_content = match.group(1)
    
    # Padrão para detectar NotebookLM com ou sem valor
    notebooklm_pattern = re.compile(r'^(NotebookLM:)\s*(.*)$', re.MULTILINE)
    notebooklm_match = notebooklm_pattern.search(frontmatter_content)
    
    if notebooklm_match:
        existing_value = notebooklm_match.group(2).strip()
        # Se já tem valor preenchido (não vazio e não é placeholder), pula
        if existing_value and existing_value != '""' and existing_value != "''":
            return "skipped"
        # Se está vazio, preenche
        new_frontmatter_content = notebooklm_pattern.sub(
            f'NotebookLM: {default_value}', frontmatter_content
        )
        action = "filled"
    else:
        # Se não existe, adiciona
        new_frontmatter_content = f"{frontmatter_content}\nNotebookLM: {default_value}"
        action = "added"
    
    new_frontmatter = f"---\n{new_frontmatter_content}\n---"
    new_content = frontmatter_pattern.sub(new_frontmatter, content, count=1)
    
    filepath.write_text(new_content, encoding="utf-8")
    return action


def main():
    base_dir = Path(__file__).parent.parent / "DailyLearning" / "Disciplinas"
    
    if not base_dir.exists():
        print(f"Erro: Diretório não encontrado: {base_dir}")
        return
    
    stats = {"added": 0, "filled": 0, "skipped": 0, "no_frontmatter": 0}
    
    for md_file in base_dir.rglob("*.md"):
        result = add_notebooklm_field(md_file)
        stats[result] += 1
        
        if result == "added":
            print(f"➕ Adicionado: {md_file.name}")
        elif result == "filled":
            print(f"✏️  Preenchido (estava vazio): {md_file.name}")
        elif result == "skipped":
            print(f"⏭️  Pulado (já preenchido): {md_file.name}")
        else:
            print(f"❌ Sem frontmatter: {md_file.name}")
    
    print(f"\n📊 Resumo:")
    print(f"   ➕ Adicionados: {stats['added']}")
    print(f"   ✏️  Preenchidos: {stats['filled']}")
    print(f"   ⏭️  Pulados (já preenchidos): {stats['skipped']}")
    print(f"   ❌ Sem frontmatter: {stats['no_frontmatter']}")


if __name__ == "__main__":
    main()
