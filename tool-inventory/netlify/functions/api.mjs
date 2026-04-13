import { getStore } from "@netlify/blobs";

const STORE_NAME = "tool-inventory";
const BLOB_KEY = "data";

const EMPTY_DATA = { tools: [], projects: [], history: [] };

function uid() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
}

async function getData(store) {
  const data = await store.get(BLOB_KEY, { type: "json" });
  return data || { ...EMPTY_DATA };
}

async function putData(store, data) {
  await store.setJSON(BLOB_KEY, data);
  return data;
}

function locationName(data, projectId) {
  if (!projectId) return "Warehouse";
  return data.projects.find(p => p.id === projectId)?.name || "Project";
}

export default async (req, context) => {
  const store = getStore(STORE_NAME);

  // GET → return all data
  if (req.method === "GET") {
    const data = await getData(store);
    return Response.json(data);
  }

  // POST → mutate
  if (req.method === "POST") {
    const body = await req.json();
    let data = await getData(store);

    switch (body.action) {
      case "addTool": {
        const tool = {
          id: uid(),
          name: body.name,
          type: body.type,
          projectId: null,
          createdAt: new Date().toISOString(),
        };
        data.tools.push(tool);
        break;
      }

      case "addToolsBulk": {
        for (const t of body.tools) {
          data.tools.push({
            id: uid(),
            name: t.name,
            type: t.type,
            projectId: null,
            createdAt: new Date().toISOString(),
          });
        }
        break;
      }

      case "deleteTool": {
        data.tools = data.tools.filter(t => t.id !== body.id);
        break;
      }

      case "addProject": {
        const project = {
          id: uid(),
          projectCode: body.projectCode,
          name: body.name,
          siteAddress: body.siteAddress || null,
          createdAt: new Date().toISOString(),
        };
        data.projects.push(project);
        break;
      }

      case "deleteProject": {
        // Return all tools to warehouse with history
        data.tools.forEach(t => {
          if (t.projectId === body.id) {
            const fromName = locationName(data, t.projectId);
            data.history.push({
              id: uid(),
              toolId: t.id,
              toolName: t.name,
              from: fromName,
              to: "Warehouse",
              movedBy: null,
              note: "Project deleted",
              date: new Date().toISOString(),
            });
            t.projectId = null;
          }
        });
        data.projects = data.projects.filter(p => p.id !== body.id);
        break;
      }

      case "moveTool": {
        const tool = data.tools.find(t => t.id === body.toolId);
        if (!tool) break;

        const fromName = locationName(data, tool.projectId);
        const toName = locationName(data, body.projectId);

        data.history.push({
          id: uid(),
          toolId: tool.id,
          toolName: tool.name,
          from: fromName,
          to: toName,
          movedBy: body.movedBy || null,
          note: body.note || null,
          date: new Date().toISOString(),
        });

        tool.projectId = body.projectId;
        break;
      }

      default:
        return Response.json({ error: "Unknown action" }, { status: 400 });
    }

    const updated = await putData(store, data);
    return Response.json(updated);
  }

  return Response.json({ error: "Method not allowed" }, { status: 405 });
};

export const config = {
  path: "/api/data",
};
