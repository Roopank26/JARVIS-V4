"""Tests for JARVIS-V7 Evolution System."""

from __future__ import annotations

from jarvis.evolution.benchmark import (
    get_promotion_gate,
    reset_promotion_gate,
)
from jarvis.evolution.evolution_engine import (
    reset_evolution_engine,
)
from jarvis.evolution.experience_collector import (
    get_experience_collector,
    reset_experience_collector,
)
from jarvis.evolution.knowledge_graph_v2 import (
    get_knowledge_graph,
    reset_knowledge_graph,
)
from jarvis.evolution.learning_pipeline import (
    CandidateTrainer,
    DatasetFactory,
    TrainingDataset,
    get_learning_pipeline,
    reset_learning_pipeline,
)
from jarvis.evolution.model_registry import (
    ModelRecord,
    ModelStage,
    get_model_registry,
    reset_model_registry,
)
from jarvis.evolution.owner import (
    DEFAULT_OWNER,
    Permission,
    get_owner_model,
    reset_owner_model,
)
from jarvis.evolution.research_engine import (
    get_research_engine,
    reset_research_engine,
)
from jarvis.evolution.self_review import (
    get_self_review_engine,
    reset_self_review_engine,
)
from jarvis.evolution.v7_orchestrator import (
    get_v7_orchestrator,
    reset_v7_orchestrator,
)


def _reset_all():
    reset_owner_model()
    reset_experience_collector()
    reset_knowledge_graph()
    reset_model_registry()
    reset_promotion_gate()
    reset_self_review_engine()
    reset_research_engine()
    reset_learning_pipeline()
    reset_evolution_engine()
    reset_v7_orchestrator()


# Owner tests
class TestOwnerModel:
    def setup_method(self):
        _reset_all()

    def test_default_owner(self):
        owner = get_owner_model()
        assert owner.get_owner().name == DEFAULT_OWNER

    def test_owner_has_all_permissions(self):
        owner = get_owner_model()
        assert owner.has_permission(DEFAULT_OWNER, Permission.APPROVE_PROMOTION)

    def test_grant_permission(self):
        owner = get_owner_model()
        owner.grant_permission(DEFAULT_OWNER, "user1", [Permission.EXPORT_ALL_KNOWLEDGE.value])
        assert owner.has_permission("user1", Permission.EXPORT_ALL_KNOWLEDGE)

    def test_revoke_permission(self):
        owner = get_owner_model()
        owner.grant_permission(DEFAULT_OWNER, "user2", [Permission.DELETE_MEMORY.value])
        owner.revoke_permission(DEFAULT_OWNER, "user2")
        assert not owner.has_permission("user2", Permission.DELETE_MEMORY)

    def test_permission_denied_for_non_owner(self):
        owner = get_owner_model()
        assert not owner.has_permission("stranger", Permission.APPROVE_PROMOTION)

    def test_set_preference(self):
        owner = get_owner_model()
        owner.set_preference("research_enabled", True)
        assert owner.get_preference("research_enabled") is True


# Experience collector tests
class TestExperienceCollector:
    def setup_method(self):
        _reset_all()

    def test_record_task(self):
        collector = get_experience_collector()
        exp = collector.record_task("t1", "hello", "world", True, 100.0)
        assert exp.success is True
        assert exp.source == "orchestrator"

    def test_record_tool_use(self):
        collector = get_experience_collector()
        exp = collector.record_tool_use("bash", "ls", "file1", True)
        assert exp.tool == "bash"

    def test_insights(self):
        # Clear persistent store to avoid cross-test contamination
        from pathlib import Path
        store_path = Path.home() / ".jarvis" / "evolution" / "experiences.jsonl"
        if store_path.exists():
            store_path.unlink()
        collector = get_experience_collector()
        collector.store._recent = []
        collector.store.path.parent.mkdir(parents=True, exist_ok=True)
        collector.record_task("t1", "a", "b", True)
        collector.record_task("t2", "c", "d", False)
        insights = collector.get_insights()
        assert insights["total_experiences"] == 2
        assert abs(insights["success_rate"] - 0.5) < 0.01


# Knowledge graph tests
class TestKnowledgeGraph:
    def setup_method(self):
        _reset_all()

    def test_add_node(self):
        graph = get_knowledge_graph()
        node = graph.add_node("project", "JARVIS-V7")
        assert node.type == "project"

    def test_add_edge(self):
        graph = get_knowledge_graph()
        n1 = graph.add_node("project", "JARVIS-V7")
        n2 = graph.add_node("goal", "continuous_improvement")
        edge = graph.add_edge(n1.id, n2.id, "aims_for")
        assert edge is not None

    def test_search(self):
        graph = get_knowledge_graph()
        graph.add_node("project", "JARVIS-V7")
        results = graph.search("JARVIS")
        assert len(results) > 0

    def test_get_stats(self):
        graph = get_knowledge_graph()
        graph.add_node("test", "test_node")
        stats = graph.get_stats()
        assert stats["nodes"] >= 1


# Model registry tests
class TestModelRegistry:
    def setup_method(self):
        _reset_all()

    def test_register_model(self):
        registry = get_model_registry()
        model = ModelRecord(name="test_model", stage=ModelStage.EXPERIMENTAL.value)
        registered = registry.register(model)
        assert registered.model_id == model.model_id

    def test_promote_model(self):
        registry = get_model_registry()
        model = ModelRecord(name="test_model", stage=ModelStage.EXPERIMENTAL.value)
        registry.register(model)
        promoted = registry.promote(model.model_id, ModelStage.CANDIDATE.value, "good metrics")
        assert promoted.stage == ModelStage.CANDIDATE.value

    def test_get_by_name(self):
        registry = get_model_registry()
        model = ModelRecord(name="unique_name", stage=ModelStage.PRODUCTION.value)
        registry.register(model)
        assert registry.get_by_name("unique_name") is not None

    def test_get_production(self):
        registry = get_model_registry()
        model = ModelRecord(name="prod_model", stage=ModelStage.PRODUCTION.value)
        registry.register(model)
        prod = registry.get_production()
        assert prod is not None
        assert prod.name == "prod_model"

    def test_rollback(self):
        registry = get_model_registry()
        model = ModelRecord(name="rollback_model", stage=ModelStage.PRODUCTION.value)
        registry.register(model)
        rolled = registry.rollback(model.model_id)
        assert rolled.stage == ModelStage.ARCHIVE.value

    def test_add_benchmark(self):
        registry = get_model_registry()
        model = ModelRecord(name="bench_model")
        registry.register(model)
        registry.add_benchmark(model.model_id, "v1", {"score": 0.9})
        loaded = registry.get(model.model_id)
        assert len(loaded.benchmark_history) == 1


# Benchmark tests
class TestBenchmark:
    def setup_method(self):
        _reset_all()

    def test_evaluate(self):
        gate = get_promotion_gate()
        result = gate.engine.evaluate("model1", {"reasoning": 0.8, "coding": 0.9})
        assert result.passed is True

    def test_should_promote_when_better(self):
        gate = get_promotion_gate()
        prod = gate.engine.evaluate("prod", {"reasoning": 0.7}, latency_ms=1000)
        cand = gate.engine.evaluate("cand", {"reasoning": 0.85}, latency_ms=800)
        should_promote, _ = gate.engine.should_promote(cand, prod)
        assert should_promote is True

    def test_should_not_promote_when_worse(self):
        gate = get_promotion_gate()
        prod = gate.engine.evaluate("prod", {"reasoning": 0.9}, latency_ms=1000)
        cand = gate.engine.evaluate("cand", {"reasoning": 0.5}, latency_ms=800)
        should_promote, _ = gate.engine.should_promote(cand, prod)
        assert should_promote is False


# Self review tests
class TestSelfReview:
    def setup_method(self):
        _reset_all()

    def test_review_success(self):
        reviewer = get_self_review_engine()
        review = reviewer.review("t1", "desc", "success output", 100.0)
        assert review.success is True
        assert review.severity == "low"

    def test_review_failure(self):
        reviewer = get_self_review_engine()
        review = reviewer.review("t1", "desc", "error occurred", 5000.0)
        assert review.success is False
        assert "overall_execution" in review.failed_components

    def test_improvement_suggestions(self):
        reviewer = get_self_review_engine()
        for i in range(10):
            reviewer.review(f"t{i}", "desc", "error", 5000.0)
        suggestions = reviewer.get_improvement_suggestions()
        assert len(suggestions) >= 1


# Research engine tests
class TestResearchEngine:
    def setup_method(self):
        _reset_all()

    def test_engine_creation(self):
        engine = get_research_engine()
        assert engine is not None

    def test_queue_task(self):
        engine = get_research_engine()
        engine.queue_task("web_search", "AI trends")
        assert not engine._queue.empty()


# Learning pipeline tests
class TestLearningPipeline:
    def setup_method(self):
        _reset_all()

    def test_dataset_factory_build(self):
        factory = DatasetFactory()
        experiences = [
            {"input_text": "hello", "output_text": "world", "success": True, "source": "orchestrator"},
        ]
        dataset = factory.build_from_experiences(experiences)
        assert dataset.metadata.get("sample_count") == 1

    def test_training_run(self):
        trainer = CandidateTrainer()
        dataset = TrainingDataset(name="test", samples=[{"input": "a", "output": "b", "success": True}])
        run = trainer.simulate_finetune("m1", "base", dataset)
        assert run.status in ("complete", "failed")

    def test_pipeline_run(self):
        pipeline = get_learning_pipeline()
        experiences = [{"input_text": "q", "output_text": "r", "success": True, "category": "general"}]
        run = pipeline.run_pipeline(experiences, "candidate", "base")
        assert run is not None
        assert len(pipeline.runs) == 1


# V7 orchestrator tests
class TestV7Orchestrator:
    def setup_method(self):
        _reset_all()

    def test_get_orchestrator(self):
        v7 = get_v7_orchestrator()
        assert v7 is not None

    def test_evolution_status(self):
        v7 = get_v7_orchestrator()
        status = v7.get_evolution_status()
        assert "evolution_engine" in status
        assert "model_registry" in status
        assert "knowledge_graph" in status

    def test_autonomous_status(self):
        v7 = get_v7_orchestrator()
        status = v7.get_autonomous_status()
        assert "running" in status
