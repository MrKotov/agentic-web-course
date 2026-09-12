/**
 * Not built yet. Spec: handover/01-course-site.spec.md, "Interactive components", item 6
 * ("MCP handshake inspector. Shows tools/list and the selection decision.").
 *
 * The hand-rolled MCP server this would visualise already exists and runs (no site
 * component needed to follow along live): apps/examples/02-mcp-server/demo/ping-server.ts,
 * driven by apps/examples/02-mcp-server/demo/server-demo.ts, which prints every raw
 * JSON-RPC message sent and received. Build this once lecture 2 needs more than that.
 */
export default function McpHandshakeInspectorPlaceholder(): React.ReactElement {
  return (
    <div className="course-todo" role="note">
      <p className="course-todo__label">TODO: инспектор на MCP ръкостискане</p>
      <p className="course-note">
        Показва <code className="course-mono">tools/list</code> и решението за избор на
        инструмент. Виж handover/01-course-site.spec.md, раздел „Interactive components“,
        точка 6. Дотогава демото в apps/examples/02-mcp-server/demo/ показва суровите
        JSON-RPC съобщения от терминала.
      </p>
    </div>
  );
}
