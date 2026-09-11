/** Terminal rendering of a VarianceReport. Kept apart from the analysis so the
 *  analysis stays testable. */
import { isStable, type VarianceReport } from "./schema.ts";

export function renderReport(report: VarianceReport): string {
  const lines: string[] = [];
  const parsedRuns = report.totalRuns - report.unparsable;

  lines.push(`Пуснати заявки:        ${report.totalRuns}`);
  lines.push(`Валиден JSON:          ${parsedRuns}`);
  lines.push(`Непарсващи отговори:   ${report.unparsable}`);
  lines.push(`Различни схеми:        ${report.distinctSchemas}`);
  lines.push("");

  lines.push("Групи по схема");
  let group = 1;
  for (const [, indices] of report.groups) {
    lines.push(`  схема ${group}: заявки ${indices.join(", ")}  (${indices.length}/${report.totalRuns})`);
    group += 1;
  }
  lines.push("");

  const pathWidth = Math.max(12, ...report.fields.map((f) => f.path.length));
  lines.push(`${"поле".padEnd(pathWidth)}  присъства  тип(ове)`);
  lines.push("-".repeat(pathWidth + 24));
  for (const field of report.fields) {
    const stable = isStable(field, parsedRuns);
    const marker = stable ? " " : "!";
    lines.push(
      `${marker}${field.path.padEnd(pathWidth - 1)}  ${String(field.present).padStart(6)}/${parsedRuns}   ${field.types.join("|")}`,
    );
  }
  lines.push("");
  lines.push("! = полето липсва в част от заявките или сменя типа си.");
  return lines.join("\n");
}
