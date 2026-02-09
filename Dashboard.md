---
cssclasses:
  - dashboard
---

# 📚 SmartNote Dashboard

```dataviewjs
const today = dv.date("today");
dv.span(`📅 **${today.toFormat("dd 'de' MMMM, yyyy")}** — ${today.weekdayLong}`);
```

---

## 🔥 Revisões de Hoje

> [!warning]+ ⚡ Pendentes para Revisar
>
> ```dataviewjs
> const today = dv.date("today");
>
> function calcProximoEstudo(page) {
>     if (!page.primeiro_contato) return null;
>     const pc = dv.date(page.primeiro_contato);
>     if (!pc) return null;
>     if (page.R4) return pc.plus({days: 112});
>     if (page.R3) return pc.plus({days: 52});
>     if (page.R2) return pc.plus({days: 22});
>     if (page.R1) return pc.plus({days: 8});
>     return pc.plus({days: 1});
> }
>
> const pages = dv.pages('"DailyLearning/Disciplinas"')
>     .where(p => p.iniciado && p.primeiro_contato)
>     .map(p => ({...p, proximo: calcProximoEstudo(p), materia: (p.file.folder.split("/")[2] || "").replace(/^\d+\.\s*/, "")}))
>     .where(p => p.proximo && p.proximo <= today)
>     .sort(p => p.proximo, 'asc');
>
> if (pages.length === 0) {
>     dv.paragraph("✅ **Parabéns! Nenhuma revisão pendente.**");
> } else {
>     dv.table(["📖 Tópico", "📚 Matéria", "📅 Data", "🔄"],
>         pages.slice(0, 8).map(p => [
>             p.file.link,
>             p.materia,
>             p.proximo.toFormat("dd/MM"),
>             `${[p.R1,p.R2,p.R3,p.R4].filter(Boolean).length}/4`
>         ])
>     );
>     if (pages.length > 8) dv.paragraph(`*...e mais ${pages.length - 8} tópicos*`);
> }
> ```

---

> [!info]+ 📊 Estatísticas
>
> ```dataviewjs
> const all = dv.pages('"DailyLearning/Disciplinas"').where(p => p.file.ext === "md");
> const ini = all.where(p => p.iniciado);
> const pct = Math.round(ini.length / all.length * 100);
>
> dv.paragraph(`
> **Total:** ${all.length} tópicos
> **Estudados:** ${ini.length} (${pct}%)
> **R1:** ${ini.where(p => p.R1).length} | **R2:** ${ini.where(p => p.R2).length}
> **R3:** ${ini.where(p => p.R3).length} | **R4:** ${ini.where(p => p.R4).length}
> `);
> ```

> [!success]+ 🏆 Progresso Geral
>
> ```dataviewjs
> const all = dv.pages('"DailyLearning/Disciplinas"').where(p => p.file.ext === "md");
> const ini = all.where(p => p.iniciado).length;
> const total = all.length;
> const pct = Math.round(ini / total * 100);
> const bars = Math.floor(pct / 5);
> const bar = "🟩".repeat(bars) + "⬜".repeat(20 - bars);
> dv.paragraph(`${bar}\n**${pct}%** concluído`);
> ```

---

## 📚 Top 5 Matérias

> [!note]+ 📝 Progresso por Disciplina
>
> ```dataviewjs
> const pages = dv.pages('"DailyLearning/Disciplinas"').where(p => p.file.ext === "md");
> const materias = {};
>
> for (const p of pages) {
>     const m = (p.file.folder.split("/")[2] || "Outros").replace(/^\d+\.\s*/, "");
>     if (!materias[m]) materias[m] = {t: 0, i: 0};
>     materias[m].t++;
>     if (p.iniciado) materias[m].i++;
> }
>
> const rows = Object.entries(materias)
>     .sort((a, b) => b[1].t - a[1].t)
>     .slice(0, 5)
>     .map(([n, s]) => {
>         const pct = Math.round(s.i / s.t * 100);
>         const bars = Math.floor(pct / 10);
>         return [n, s.t, s.i, "█".repeat(bars) + "░".repeat(10-bars) + ` ${pct}%`];
>     });
>
> dv.table(["Matéria", "Total", "✅", "Progresso"], rows);
> ```

---

## 🗓️ Últimos Estudados

> [!example]+ 📖 Recentes
>
> ```dataviewjs
> dv.table(["Tópico", "Data", "R1", "R2", "R3", "R4"],
>     dv.pages('"DailyLearning/Disciplinas"')
>         .where(p => p.iniciado && p.primeiro_contato)
>         .sort(p => p.primeiro_contato, 'desc')
>         .limit(5)
>         .map(p => [
>             p.file.link,
>             dv.date(p.primeiro_contato)?.toFormat("dd/MM") || "-",
>             p.R1 ? "✅" : "⬜", p.R2 ? "✅" : "⬜",
>             p.R3 ? "✅" : "⬜", p.R4 ? "✅" : "⬜"
>         ])
> );
> ```

---

## 🚀 Acesso Rápido

> [!tip]+ 🧭 Navegação
>
> | 📋 RunBook | 🔄 Revisão Espaçada | 📂 Disciplinas |
> |:---:|:---:|:---:|
> | [[DailyLearning/RunBook\|Abrir]] | [[DailyLearning/Revisao Espacada\|Abrir]] | [[DailyLearning/Disciplinas\|Explorar]] |
