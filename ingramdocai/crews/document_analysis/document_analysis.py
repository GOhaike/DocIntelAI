from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from ingramdocai.crews.document_analysis.document_analysis_output import DocumentAnalysisOutput

@CrewBase
class DocumentAnalysisCrew:
    """Crew to classify, extract, and map intelligence across uploaded documents."""

    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    @agent
    def document_analysis_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['document_analysis_agent'],
            verbose=True
        )

    @task
    def document_analysis_task(self) -> Task:
        return Task(
            config=self.tasks_config['document_analysis_task'],
            output_pydantic=DocumentAnalysisOutput,
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True
        )

