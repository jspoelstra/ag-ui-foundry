"use client";

import React, { useEffect, useRef, useState } from "react";
import { CopilotKit, useCoAgent, useCopilotChat } from "@copilotkit/react-core";
import { CopilotChat } from "@copilotkit/react-ui";
import { Role, TextMessage } from "@copilotkit/runtime-client-gql";
import "@copilotkit/react-ui/styles.css";
import "./style.css";

interface Location {
  country: string;
  district: string;
  lat: number;
  long: number;
}

interface Component {
  type: string;
  description: string;
  environment_impact: string;
}

interface Project {
  name: string;
  description: string;
  location: Location;
  components: Component[];
}

type ProjectAgentState = Project;

const INITIAL_STATE: ProjectAgentState = {
  name: "New Project",
  description: "Outline the project scope, goals, and constraints.",
  location: {
    country: "",
    district: "",
    lat: 0,
    long: 0,
  },
  components: [
    {
      type: "",
      description: "",
      environment_impact: "",
    },
  ],
};

export default function ProjectPage() {
  useSuppressKnownToolLifecycleError();

  const agentName = process.env.NEXT_PUBLIC_AGENT_NAME ?? "ag-ui";
  const integrationId = "default";
  const chatTitle = "AI Project Assistant";
  const chatDescription = "Ask me to shape your project";
  const initialLabel = "Hi 👋 How can I help with your project?";

  return (
    <CopilotKit
      runtimeUrl={`/api/copilotkit/${integrationId}`}
      showDevConsole={false}
      agent={agentName}
    >
      <div className="min-h-screen w-full flex items-start justify-start bg-slate-50 p-6 project-layout">
        <div className="w-full flex flex-row gap-6">
          <div className="flex-1 min-w-0">
            <ProjectCard />
          </div>
          <div className="chat-column">
            <CopilotChat
              labels={{
                title: chatTitle,
                initial: initialLabel,
                placeholder: chatDescription,
              }}
            />
          </div>
        </div>
      </div>
    </CopilotKit>
  );
}

function useSuppressKnownToolLifecycleError() {
  useEffect(() => {
    const originalConsoleError = console.error;

    console.error = (...args: unknown[]) => {
      const firstArg = args[0];
      const message = typeof firstArg === "string" ? firstArg : "";

      if (
        message.includes("Cannot send 'TOOL_CALL_END' event") &&
        message.includes("A 'TOOL_CALL_START' event must be sent first")
      ) {
        return;
      }

      originalConsoleError(...args);
    };

    return () => {
      console.error = originalConsoleError;
    };
  }, []);
}

function ProjectCard() {
  const agentName = process.env.NEXT_PUBLIC_AGENT_NAME ?? "ag-ui";
  const { state: agentState, setState: setAgentState } = useCoAgent<ProjectAgentState>({
    name: agentName,
    initialState: INITIAL_STATE,
  });

  const [project, setProject] = useState<Project>(INITIAL_STATE);
  const { appendMessage, isLoading } = useCopilotChat();

  const updateProject = (partialProject: Partial<Project>) => {
    const nextProject: Project = {
      ...project,
      ...partialProject,
    };

    setAgentState({
      ...(agentState ?? INITIAL_STATE),
      ...nextProject,
    });

    setProject(nextProject);
  };

  const newProjectState = { ...project };
  const newChangedKeys: string[] = [];
  const changedKeysRef = useRef<string[]>([]);

  for (const key in project) {
    if (
      agentState &&
      (agentState as any)[key] !== undefined &&
      (agentState as any)[key] !== null
    ) {
      let agentValue = (agentState as any)[key];
      const projectValue = (project as any)[key];

      if (typeof agentValue === "string") {
        agentValue = agentValue.replace(/\\n/g, "\n");
      }

      if (JSON.stringify(agentValue) !== JSON.stringify(projectValue)) {
        (newProjectState as any)[key] = agentValue;
        newChangedKeys.push(key);
      }
    }
  }

  if (newChangedKeys.length > 0) {
    changedKeysRef.current = newChangedKeys;
  } else if (!isLoading) {
    changedKeysRef.current = [];
  }

  useEffect(() => {
    setProject(newProjectState);
  }, [JSON.stringify(newProjectState)]);

  const handleNameChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    updateProject({
      name: event.target.value,
    });
  };

  const handleDescriptionChange = (event: React.ChangeEvent<HTMLTextAreaElement>) => {
    updateProject({
      description: event.target.value,
    });
  };

  const handleLocationChange = (field: keyof Location, value: string | number) => {
    updateProject({
      location: {
        ...project.location,
        [field]: value,
      },
    });
  };

  const addComponent = () => {
    updateProject({
      components: [...project.components, { type: "", description: "", environment_impact: "" }],
    });
  };

  const updateComponent = (index: number, field: keyof Component, value: string) => {
    const updatedComponents = [...project.components];
    updatedComponents[index] = {
      ...updatedComponents[index],
      [field]: value,
    };
    updateProject({ components: updatedComponents });
  };

  const removeComponent = (index: number) => {
    const updatedComponents = [...project.components];
    updatedComponents.splice(index, 1);
    updateProject({ components: updatedComponents });
  };

  return (
    <form data-testid="project-card" className="project-card">
      <div className="project-header">
        <input
          type="text"
          value={project.name || ""}
          onChange={handleNameChange}
          className="project-title-input"
        />
      </div>

      <div className="section-container relative">
        {changedKeysRef.current.includes("description") && <Ping />}
        <h2 className="section-title">Project Description</h2>
        <textarea
          className="component-textarea"
          value={project.description || ""}
          onChange={handleDescriptionChange}
          placeholder="Describe the project scope, goals, and constraints."
        />
      </div>

      <div className="section-container relative">
        {changedKeysRef.current.includes("location") && <Ping />}
        <h2 className="section-title">Location</h2>
        <div className="field-grid">
          <div className="field-card">
            <div className="field-content">
              <input
                type="text"
                value={project.location.country || ""}
                onChange={(e) => handleLocationChange("country", e.target.value)}
                placeholder="Country"
                className="field-name-input"
              />
              <input
                type="text"
                value={project.location.district || ""}
                onChange={(e) => handleLocationChange("district", e.target.value)}
                placeholder="District"
                className="field-detail-input"
              />
            </div>
          </div>
          <div className="field-card">
            <div className="field-content">
              <label htmlFor="location-lat" className="field-label">
                Latitude
              </label>
              <input
                id="location-lat"
                type="number"
                value={project.location.lat ?? ""}
                onChange={(e) =>
                  handleLocationChange("lat", e.target.value === "" ? 0 : Number(e.target.value))
                }
                placeholder="Latitude"
                className="field-name-input coordinate-input"
              />
              <label htmlFor="location-long" className="field-label">
                Longitude
              </label>
              <input
                id="location-long"
                type="number"
                value={project.location.long ?? ""}
                onChange={(e) =>
                  handleLocationChange("long", e.target.value === "" ? 0 : Number(e.target.value))
                }
                placeholder="Longitude"
                className="field-name-input coordinate-input"
              />
            </div>
          </div>
        </div>
      </div>

      <div className="section-container relative">
        {changedKeysRef.current.includes("components") && <Ping />}
        <div className="section-header">
          <h2 className="section-title">Components</h2>
          <button type="button" className="add-component-button" onClick={addComponent}>
            + Add Component
          </button>
        </div>
        <div className="component-list">
          {project.components.map((component, index) => (
            <div key={index} className="component-item">
              <div className="component-index">{index + 1}</div>
              {index < project.components.length - 1 && <div className="component-line" />}
              <div className="component-content component-content-default">
                <div className="field-content">
                  <input
                    type="text"
                    value={component.type || ""}
                    onChange={(e) => updateComponent(index, "type", e.target.value)}
                    placeholder="Component type"
                    className="field-name-input"
                  />
                  <input
                    type="text"
                    value={component.description || ""}
                    onChange={(e) => updateComponent(index, "description", e.target.value)}
                    placeholder="Component description"
                    className="field-detail-input"
                  />
                  <input
                    type="text"
                    value={component.environment_impact || ""}
                    onChange={(e) => updateComponent(index, "environment_impact", e.target.value)}
                    placeholder="Environmental impact"
                    className="field-detail-input"
                  />
                </div>
                <button
                  type="button"
                  className="component-delete-btn component-delete-btn-default remove-button"
                  onClick={() => removeComponent(index)}
                  aria-label="Remove component"
                >
                  ×
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="action-container">
        <button
          data-testid="improve-button"
          className={isLoading ? "improve-button loading" : "improve-button"}
          type="button"
          onClick={() => {
            if (!isLoading) {
              appendMessage(
                new TextMessage({
                  content: "Improve the project",
                  role: Role.User,
                })
              );
            }
          }}
          disabled={isLoading}
        >
          {isLoading ? "Please Wait..." : "Improve with AI"}
        </button>
      </div>
    </form>
  );
}

function Ping() {
  return (
    <span className="ping-animation">
      <span className="ping-circle"></span>
      <span className="ping-dot"></span>
    </span>
  );
}
