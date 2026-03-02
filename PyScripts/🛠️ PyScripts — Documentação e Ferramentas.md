
Scripts Python para automação do vault Obsidian.

---

## 📦 Scripts Disponíveis

### 1. `add_frontmatter.py`
Adiciona frontmatter padrão em arquivos `.md` que não possuem.

**Campos adicionados:**
- `iniciado: false`
- `primeiro_contato:`
- `R1` a `R4: false`
- `NotebookLM: "[Título](<linkdonotebooklm>)"`

```button
name ▶️ Executar add_frontmatter.py
type command
action Shell commands: Execute: python3 add_frontmatter.py
```

---

### 2. `add_notebooklm_field.py`
Preenche o campo `NotebookLM` vazio com valor padrão.

- Se já preenchido → pula
- Se vazio → preenche com `[Título](<linkdonotebooklm>)`

```button
name ▶️ Executar add_notebooklm_field.py
type command
action Shell commands: Execute: python3 add_notebooklm_field.py
```

---

### 3. `add_buttons.py`
Adiciona botões do plugin Buttons com prompts preenchidos dinamicamente.

**Botões gerados:**
- 🔍 DeepSearch
- 📝 GenQuest / GenQuestExpert
- 🎬 GenVid / GenVidExpert
- 🎨 GenVidPersonalization

```button
name ▶️ Executar add_buttons.py
type command
action Shell commands: Execute: python3 add_buttons.py
```

---

### 4. `generate_dashboard.py`
Gera `Dashboard.html` na raiz do vault — um dashboard visual estilo Notion com dark theme.

**Dados exibidos (lidos do frontmatter):**
- Estatísticas gerais (total, estudados, R1–R4)
- Progresso geral com barra animada
- Revisões pendentes (revisão espaçada)
- Progresso por disciplina
- Últimos tópicos estudados
- Links rápidos (RunBook, Revisão Espaçada, Disciplinas)

```button
name ▶️ Gerar Dashboard HTML
type command
action Shell commands: Execute: python3 generate_dashboard.py
```

---



## 📁 Estrutura de Pastas

```
SmartNoteBrain/
├── DailyLearning/
│   ├── Disciplinas/          ← Arquivos .md processados
│   ├── Prompts/              ← Templates de prompts
│   ├── RunBook.base
│   └── Revisao Espacada.base
└── PyScripts/                ← Scripts Python
    ├── README.md             ← Este arquivo
    ├── add_frontmatter.py
    ├── add_notebooklm_field.py
    ├── add_buttons.py
    └── clean_prompts.py
```

---

## 🔄 Workflow Típico

1. **Novo arquivo .md criado** → Executar `add_frontmatter.py`
2. **Preencher NotebookLM** → Executar `add_notebooklm_field.py`
3. **Adicionar botões** → Executar `add_buttons.py`

---

## ⚠️ Requisitos

- **Plugin Shell commands** (para botões de execução)
- **Plugin Buttons** (para botões de cópia nos arquivos)
- **Python 3.10+**
