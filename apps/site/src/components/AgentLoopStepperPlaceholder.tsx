/**
 * Deliberately NOT built. Spec: handover/01-course-site.spec.md, "Interactive components",
 * item 5 ("Agent loop stepper. … Check VoltAgent's console first. If its execution traces
 * are good enough to present from, do not build this.").
 *
 * This is gate-zero item 4 (docs/gate-zero.md): "VoltAgent console — are its execution
 * traces presentable? If yes, the agent-loop stepper is never built. It is the most
 * expensive component on the site." That check has not happened yet (status: not started).
 * Building this component now would risk throwing the work away, so it stays a stub until
 * item 4 is resolved one way or the other.
 */
export default function AgentLoopStepperPlaceholder(): React.ReactElement {
  return (
    <div className="course-todo" role="note">
      <p className="course-todo__label">Блокирано: стъпков агентен цикъл</p>
      <p className="course-note">
        Изчаква проверка на конзолата на VoltAgent (docs/gate-zero.md, точка 4). Ако
        нейните изпълнителски трасета са достатъчно добри за презентиране, този компонент
        изобщо не се строи — той е най-скъпият компонент в сайта. Не пипайте, докато точка
        4 не бъде разрешена.
      </p>
    </div>
  );
}
