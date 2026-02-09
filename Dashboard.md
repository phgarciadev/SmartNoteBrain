# 📊 Dashboard de Estudos

```dataviewjs
const today = dv.date("today");
const todayStr = today.toFormat("yyyy-MM-dd");
dv.paragraph(`📅 **Hoje:** ${today.toFormat("dd/MM/yyyy")} (${today.weekdayLong})`);
```

---

## 🔥 Revisões para Hoje

```dataviewjs
const today = dv.date("today");

// Função para calcular próximo estudo
function calcProximoEstudo(page) {
    if (!page.primeiro_contato) return null;
    const pc = dv.date(page.primeiro_contato);
    if (!pc) return null;
    
    if (page.R4) return pc.plus({days: 112});
    if (page.R3) return pc.plus({days: 52});
    if (page.R2) return pc.plus({days: 22});
    if (page.R1) return pc.plus({days: 8});
    return pc.plus({days: 1});
}

const pages = dv.pages('"DailyLearning/Disciplinas"')
    .where(p => p.iniciado === true && p.primeiro_contato)
    .map(p => {
        const proximo = calcProximoEstudo(p);
        const materia = p.file.folder.split("/")[2] || "";
        const assunto = p.file.folder.split("/")[3] || materia;
        return {...p, proximo, materia, assunto};
    })
    .where(p => p.proximo && p.proximo <= today)
    .sort(p => p.proximo, 'asc');

if (pages.length === 0) {
    dv.paragraph("✅ **Nenhuma revisão pendente para hoje!**");
} else {
    dv.paragraph(`⚠️ **${pages.length} tópico(s) para revisar:**`);
    dv.table(
        ["Tópico", "Matéria", "Próximo Estudo", "Progresso"],
        pages.map(p => [
            p.file.link,
            p.materia.replace(/^\d+\.\s*/, ""),
            p.proximo.toFormat("dd/MM"),
            `${[p.R1, p.R2, p.R3, p.R4].filter(Boolean).length}/4`
        ])
    );
}
```

---

## 📈 Estatísticas Gerais

```dataviewjs
const pages = dv.pages('"DailyLearning/Disciplinas"').where(p => p.file.ext === "md");
const iniciados = pages.where(p => p.iniciado === true);

const total = pages.length;
const estudados = iniciados.length;
const pendentes = total - estudados;

// Contagem por revisão
const r1 = iniciados.where(p => p.R1 === true).length;
const r2 = iniciados.where(p => p.R2 === true).length;
const r3 = iniciados.where(p => p.R3 === true).length;
const r4 = iniciados.where(p => p.R4 === true).length;

dv.paragraph(`
| 📊 Métrica | Valor |
|------------|-------|
| 📚 Total de Tópicos | **${total}** |
| ✅ Estudados | **${estudados}** (${Math.round(estudados/total*100)}%) |
| ⏳ Não iniciados | **${pendentes}** |
| 🔁 R1 completadas | **${r1}** |
| 🔁 R2 completadas | **${r2}** |
| 🔁 R3 completadas | **${r3}** |
| 🔁 R4 completadas | **${r4}** |
`);
```

---

## 📚 Progresso por Matéria

```dataviewjs
const pages = dv.pages('"DailyLearning/Disciplinas"').where(p => p.file.ext === "md");

const materias = {};
for (const p of pages) {
    const materia = (p.file.folder.split("/")[2] || "Outros").replace(/^\d+\.\s*/, "");
    if (!materias[materia]) {
        materias[materia] = {total: 0, iniciados: 0, r4: 0};
    }
    materias[materia].total++;
    if (p.iniciado) materias[materia].iniciados++;
    if (p.R4) materias[materia].r4++;
}

const rows = Object.entries(materias)
    .sort((a, b) => b[1].total - a[1].total)
    .map(([nome, stats]) => {
        const pct = Math.round(stats.iniciados / stats.total * 100);
        const bar = "█".repeat(Math.floor(pct/10)) + "░".repeat(10 - Math.floor(pct/10));
        return [nome, stats.total, stats.iniciados, `${bar} ${pct}%`];
    });

dv.table(["Matéria", "Total", "Estudados", "Progresso"], rows);
```

---

## 🗓️ Últimos Estudos

```dataviewjs
const pages = dv.pages('"DailyLearning/Disciplinas"')
    .where(p => p.iniciado === true && p.primeiro_contato)
    .sort(p => p.primeiro_contato, 'desc')
    .limit(10);

dv.table(
    ["Tópico", "1º Contato", "R1", "R2", "R3", "R4"],
    pages.map(p => [
        p.file.link,
        dv.date(p.primeiro_contato)?.toFormat("dd/MM") || "-",
        p.R1 ? "✅" : "⬜",
        p.R2 ? "✅" : "⬜",
        p.R3 ? "✅" : "⬜",
        p.R4 ? "✅" : "⬜"
    ])
);
```

---

## 🚀 Ações Rápidas

```button
name 📋 Abrir RunBook
type link
action obsidian://open?vault=SmartNoteBrain&file=DailyLearning%2FRunBook
```

```button
name 🔄 Abrir Revisão Espaçada
type link
action obsidian://open?vault=SmartNoteBrain&file=DailyLearning%2FRevisao%20Espacada
```
