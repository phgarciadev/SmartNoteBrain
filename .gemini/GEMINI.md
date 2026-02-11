# SmartNoteBrain — Instruções para Agente

## 1. O que é este repositório

Este repositório é um **vault do Obsidian** — um sistema de notas interligadas baseado em Markdown, com plugins, metadados (frontmatter YAML) e automações via scripts Python. Ele organiza o estudo pessoal de um estudante com foco em vestibulares (FUVEST, UNICAMP, ENEM).

**Obsidian NÃO é um editor de Markdown comum.** Ele interpreta sintaxes próprias, plugins de comunidade e estruturas específicas. Antes de editar qualquer arquivo `.md`, considere como o Obsidian vai renderizar o resultado.

---

## 2. Estrutura do Vault

```
SmartNoteBrain/
├── .obsidian/              ← Configurações do Obsidian (NÃO editar manualmente)
├── DailyLearning/
│   ├── Disciplinas/        ← Notas de estudo organizadas por matéria/assunto/tópico
│   │   ├── 1. Língua Portuguesa/
│   │   │   ├── 1. Leitura e Interpretação/
│   │   │   │   ├── 1. Níveis.md
│   │   │   │   └── ...
│   │   │   └── ...
│   │   └── ...
│   ├── Prompts/            ← Templates de prompts para IA (DeepSearch, GenQuest, etc.)
│   ├── Prompts.canvas      ← Canvas visual dos prompts
│   ├── Revisao Espacada.base
│   ├── RunBook.base
│   └── Cronograma de Estudos.md
├── PyScripts/              ← Scripts de automação reutilizáveis
│   ├── 🛠️ PyScripts — Documentação e Ferramentas.md
│   ├── add_buttons.py
│   ├── add_frontmatter.py
│   └── ...
├── Dashboard.md            ← Dashboard principal com DataviewJS
└── .gemini/                ← Este diretório
```

### Hierarquia das notas

As notas dentro de `Disciplinas/` seguem uma hierarquia rígida:

| Nível       | O que é                                 | Exemplo                          |
|-------------|----------------------------------------|----------------------------------|
| Disciplina  | Pasta raiz da matéria                  | `1. Língua Portuguesa/`          |
| Assunto     | Subpasta com macroconteúdo             | `1. Leitura e Interpretação/`    |
| Tópico      | Arquivo `.md` — unidade real de estudo | `1. Níveis.md`                   |

Cada `.md` possui frontmatter YAML com campos de controle de estudo (`iniciado`, `primeiro_contato`, `R1`~`R4`, `NotebookLM`).

---

## 3. Obsidian Markdown — Sintaxe e Renderização

### Regras fundamentais

- **Obsidian estende o Markdown padrão.** Wikilinks (`[[nota]]`), callouts (`> [!type]`), embeds (`![[arquivo]]`), e blocos de código com funcionalidade de plugin são renderizados de forma especial.
- **Nunca insira HTML bruto** a menos que seja absolutamente necessário. Obsidian renderiza Markdown nativo de forma muito melhor.
- **Frontmatter YAML** (`---` no topo) é obrigatório em notas de estudo. Não removê-lo, não alterar a estrutura sem pedir.

### Sintaxes específicas do Obsidian

```markdown
# Links internos
[[nome-da-nota]]
[[pasta/nota|Texto exibido]]

# Embeds
![[nota-embedada]]
![[imagem.png]]

# Callouts
> [!note] Título
> Conteúdo do callout

# Tags
#tag-exemplo

# DataviewJS (plugin Dataview)
```dataviewjs
dv.pages('"pasta"').where(p => p.campo === true)
```​

# Botões (plugin Buttons)
```button
name Texto do Botão
type copy
action Conteúdo copiado ao clicar
```​
```

### Plugin Buttons — Atenção especial

Os blocos `` ```button `` são o formato principal para prompts copiáveis nas notas de estudo. Regras:

1. O conteúdo inteiro do `action` é copiado **literalmente** ao clicar.
2. **Não use `` ``` `` (backticks triplos) dentro do `action`** — isso quebra o bloco. O script `add_buttons.py` já converte para `~~~` automaticamente.
3. Cada botão é um bloco `` ```button ... ``` `` independente.
4. Ao gerar botões programaticamente, sempre use o formato exato mostrado acima.

---

## 4. Plugins Instalados

Antes de modificar qualquer funcionalidade, **pesquise a documentação do plugin específico** para entender sintaxe, limitações e comportamento.

| Plugin                | Uso no vault                                              |
|-----------------------|----------------------------------------------------------|
| **Buttons**           | Botões clicáveis nos `.md` (copiar prompts, executar comandos) |
| **Dataview**          | Queries e dashboards dinâmicos com DataviewJS            |
| **Shell Commands**    | Execução de scripts Python via botões dentro do Obsidian |
| **Templater**         | Templates dinâmicos para novas notas                     |
| **Obsidian Git**      | Backup automático via Git                                |
| **Meta Bind**         | Binding de metadados interativos                         |
| **Metadata Menu**     | Interface para gerenciar frontmatter                     |
| **Calendar**          | Visualização de calendário                               |
| **Homepage**          | Define a nota inicial ao abrir o vault                   |
| **Periodic PARA**     | Organização periódica de notas                           |
| **Ink**               | Escrita manual / desenho                                 |

> **OBRIGATÓRIO:** Sempre que trabalhar com algo que envolva um plugin do Obsidian (sintaxe de botão, query Dataview, template Templater, etc.), **pesquise antes** a documentação oficial do plugin na web. Não assuma que o comportamento é igual a Markdown padrão.

---

## 5. Scripts Python — Política de Organização

### Scripts reutilizáveis → `PyScripts/`

Scripts que automatizam processos recorrentes do vault vão em `PyScripts/`. Regras:

1. **Documentar** no arquivo `🛠️ PyScripts — Documentação e Ferramentas.md` localizado na mesma pasta.
2. Incluir na documentação: o que o script faz, como executar, e se possível um botão Obsidian para execução rápida.
3. Usar `Path(__file__).parent.parent` como referência para o root do vault.
4. Toda leitura/escrita de arquivo deve usar `encoding="utf-8"`.
5. Scripts devem ser **idempotentes** — rodar múltiplas vezes não deve duplicar ou corromper conteúdo.

### Scripts descartáveis / uso único → `temp/`

Scripts para tarefas pontuais (migração, limpeza ocasional, análise rápida) vão na pasta `temp/` na raiz do vault. Estes:

- Não precisam de documentação formal.
- Devem ser descartados após uso.
- Não devem alterar a estrutura do vault permanentemente sem confirmação.

### Convenções gerais para scripts

- **Nunca mover, renomear ou criar pastas** dentro de `Disciplinas/` — a estrutura de pastas é fixa e gerenciada manualmente.
- Scripts modificam apenas o **conteúdo** dos arquivos `.md`, nunca sua localização.
- Sempre que adicionar/remover seções em arquivos, usar regex ou marcadores claros para facilitar re-execução (idempotência).
- Antes de escrever o arquivo, remover a versão antiga da seção que será adicionada.

---

## 6. Templates de Prompts

Os templates ficam em `DailyLearning/Prompts/` e são arquivos `.md` com o conteúdo encapsulado em um bloco `` ```markdown ... ``` ``.

### Placeholders nos templates

| Placeholder/Padrão                                        | Substituído por                  |
|----------------------------------------------------------|----------------------------------|
| `<>` após "são eles:", "do assunto:", "da disciplina:"   | Tópico, assunto, disciplina (DeepSearch) |
| `Tópico(s) deste notebook (Somente esses):` (linha vazia após) | Nome do tópico (outros prompts)  |
| `<OTHER_TOPICS>`                                          | Lista de outros tópicos da mesma pasta |

### Lógica de extração do tópico

1. Se o arquivo `.md` começa com um **code block** logo após o frontmatter, o conteúdo desse code block é o tópico.
2. Caso contrário, o **nome do arquivo** (sem prefixo numérico e extensão) é o tópico.

---

## 7. Pesquisa Obrigatória

Ao trabalhar neste vault, **pesquise na web** antes de implementar qualquer coisa que envolva:

- Sintaxe de plugins do Obsidian (Buttons, Dataview, Templater, Meta Bind, etc.)
- Comportamento de renderização do Obsidian (callouts, embeds, CSS classes)
- Frontmatter YAML e como o Obsidian e plugins o interpretam
- APIs de community plugins (DataviewJS, Templater scripts)
- Qualquer funcionalidade que não seja Markdown padrão

**Não assuma.** A documentação do Obsidian e dos plugins é a fonte de verdade.

---

## 8. Checklist antes de modificar o vault

- [ ] Entendi qual plugin ou funcionalidade está envolvida?
- [ ] Pesquisei a documentação/sintaxe relevante?
- [ ] O script/alteração é idempotente (pode rodar de novo sem estragar)?
- [ ] Scripts reutilizáveis estão em `PyScripts/` e documentados?
- [ ] Scripts descartáveis estão em `temp/`?
- [ ] Não estou criando, movendo ou renomeando pastas dentro de `Disciplinas/`?
- [ ] O formato de saída é compatível com o Obsidian (botões, callouts, frontmatter válido)?
