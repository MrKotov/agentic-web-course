/**
 * Not built yet. Spec: handover/01-course-site.spec.md, "Interactive components", item 2
 * ("Context budget. Drag files into a window, watch what fits and what falls out.").
 *
 * Ordered second by teaching value in the spec, after the prompt variance runner (item 1,
 * built — see PromptVarianceRunner.tsx). Build this once lecture 3 gets full content.
 */
export default function ContextBudgetPlaceholder(): React.ReactElement {
  return (
    <div className="course-todo" role="note">
      <p className="course-todo__label">TODO: контекстен бюджет</p>
      <p className="course-note">
        Плъзгане на файлове в прозорец с ограничен размер на контекста, за да се вижда кое
        влиза и кое отпада. Виж handover/01-course-site.spec.md, раздел „Interactive
        components“, точка 2. Не е построен в този проход.
      </p>
    </div>
  );
}
