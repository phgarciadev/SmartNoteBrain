#!/usr/bin/env python3
"""
Script para remover prompts hardcoded e deixar apenas botões limpos.
Remove toda a seção ## 📋 Prompts Preenchidos com conteúdo extenso.
"""

import re
from pathlib import Path


def clean_file(filepath: Path) -> str:
    """Remove a seção de prompts do arquivo. Retorna status."""
    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception as e:
        return f"error: {e}"
    
    # Verifica se tem a seção para remover
    if "## 📋 Prompts Preenchidos" not in content:
        return "skipped: sem seção de prompts"
    
    # Remove tudo a partir de "## 📋 Prompts Preenchidos"
    pattern = r'\n?## 📋 Prompts Preenchidos.*'
    new_content = re.sub(pattern, '', content, flags=re.DOTALL).rstrip() + '\n'
    
    filepath.write_text(new_content, encoding="utf-8")
    return "ok"


def main():
    base_dir = Path(__file__).parent.parent / "DailyLearning" / "Disciplinas"
    
    if not base_dir.exists():
        print(f"❌ Diretório não encontrado: {base_dir}")
        return
    
    stats = {"ok": 0, "skipped": 0, "error": 0}
    
    print("🧹 Removendo prompts hardcoded...\n")
    
    for md_file in base_dir.rglob("*.md"):
        result = clean_file(md_file)
        
        if result == "ok":
            stats["ok"] += 1
            print(f"✅ Limpo: {md_file.name}")
        elif result.startswith("skipped"):
            stats["skipped"] += 1
        else:
            stats["error"] += 1
            print(f"❌ {md_file.name}: {result}")
    
    print(f"\n📊 Resumo:")
    print(f"   ✅ Limpos: {stats['ok']}")
    print(f"   ⏭️  Pulados: {stats['skipped']}")
    print(f"   ❌ Erros: {stats['error']}")


if __name__ == "__main__":
    main()
