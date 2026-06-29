"""Agent registry — central catalog of available agents."""

from __future__ import annotations

from terra.agents.base import Agent, AgentConfig


class AgentRegistry:
    """Registry that holds agent configurations and factories.

    Agents can be registered as classes (instantiated on demand) or
    as pre-built instances.
    """

    def __init__(self) -> None:
        self._agents: dict[str, type[Agent]] = {}
        self._configs: dict[str, AgentConfig] = {}

    def register(
        self,
        agent_cls: type[Agent],
        config: AgentConfig,
    ) -> None:
        """Register an agent class with its configuration.

        Args:
            agent_cls: The agent class to register.
            config: Default configuration for this agent.

        Raises:
            ValueError: If an agent with the same name is already registered.
        """
        if config.name in self._agents:
            msg = f"Agent '{config.name}' is already registered"
            raise ValueError(msg)
        self._agents[config.name] = agent_cls
        self._configs[config.name] = config

    def unregister(self, name: str) -> None:
        """Remove an agent from the registry."""
        self._agents.pop(name, None)
        self._configs.pop(name, None)

    def get_class(self, name: str) -> type[Agent] | None:
        """Look up an agent class by name."""
        return self._agents.get(name)

    def get_config(self, name: str) -> AgentConfig | None:
        """Look up an agent's default config by name."""
        return self._configs.get(name)

    def create(self, name: str, **config_overrides: object) -> Agent:
        """Instantiate an agent by name with optional config overrides.

        Raises:
            KeyError: If the agent is not registered.
        """
        agent_cls = self._agents.get(name)
        config = self._configs.get(name)
        if agent_cls is None or config is None:
            msg = f"Agent '{name}' not found in registry"
            raise KeyError(msg)

        if config_overrides:
            config = config.model_copy(update=config_overrides)

        return agent_cls(config)

    def list_names(self) -> list[str]:
        """Return names of all registered agents."""
        return list(self._agents.keys())

    def list_configs(self) -> list[AgentConfig]:
        """Return configs of all registered agents."""
        return list(self._configs.values())

    def __len__(self) -> int:
        return len(self._agents)

    def __contains__(self, name: str) -> bool:
        return name in self._agents


# Global default registry
agent_registry = AgentRegistry()
