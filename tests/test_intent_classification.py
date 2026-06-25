"""
Tests for JARVIS Intent Classification
Tests that natural language questions stay in chat mode,
memory operations work correctly, and tool execution is triggered properly.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch

from jarvis.core.agent import (
    Intent,
    classify_intent,
    JarvisAgent
)


class TestIntentClassification:
    """Test intent classification patterns."""

    def test_factual_questions_stay_in_chat(self):
        """Test that factual questions are classified as CHAT."""
        questions = [
            "what is machine learning",
            "who is the president",
            "what is Python",
            "why is the sky blue",
            "how does photosynthesis work",
            "what is the capital of France",
            "explain quantum computing",
        ]
        for q in questions:
            intent = classify_intent(q)
            assert intent == Intent.CHAT, f"'{q}' should be CHAT but got {intent}"

    def test_study_plans_stay_in_chat(self):
        """Test that study plan requests stay in chat mode."""
        requests = [
            "create a study plan for machine learning",
            "make a study plan for math",
            "help me study for the exam",
            "create a learning plan for Python",
            "give me a study guide for chemistry",
        ]
        for req in requests:
            intent = classify_intent(req)
            assert intent == Intent.CHAT, f"'{req}' should be CHAT but got {intent}"

    def test_memory_recall_patterns(self):
        """Test that memory recall requests are classified correctly."""
        patterns = [
            "what is my favorite color",
            "what's my favorite food",
            "do you remember my preferences",
            "recall my favorite food",
        ]
        for p in patterns:
            intent = classify_intent(p)
            assert intent == Intent.MEMORY_RECALL, f"'{p}' should be MEMORY_RECALL but got {intent}"

    def test_memory_store_patterns(self):
        """Test that memory store requests are classified correctly."""
        patterns = [
            "remember my favorite color is blue",
            "save that I like machine learning",
            "remember I prefer tea over coffee",
            "note that my birthday is in June",
            "remember my name is John",
            "save my email is test@example.com",
        ]
        for p in patterns:
            intent = classify_intent(p)
            assert intent == Intent.MEMORY_STORE, f"'{p}' should be MEMORY_STORE but got {intent}"

    def test_tool_execution_patterns(self):
        """Test that tool execution patterns are classified correctly."""
        patterns = [
            "read file /home/user/test.txt",
            "write file /tmp/notes.txt",
            "delete file /tmp/old.txt",
            "list files in /home",
            "ls -la /home/user",
            "run command ls -la",
            "cd /home/user",
            "mkdir new_folder",
            "rm file.txt",
            "search for pattern in file.txt",
        ]
        for p in patterns:
            intent = classify_intent(p)
            assert intent == Intent.TOOL_EXECUTION, f"'{p}' should be TOOL_EXECUTION but got {intent}"

    def test_casual_conversation_stays_in_chat(self):
        """Test that casual conversation stays in chat mode."""
        messages = [
            "hello jarvis",
            "hey, how are you?",
            "thanks for your help",
            "what do you think about AI?",
            "good morning",
            "hi there",
        ]
        for m in messages:
            intent = classify_intent(m)
            assert intent == Intent.CHAT, f"'{m}' should be CHAT but got {intent}"

    def test_explain_patterns(self):
        """Test that explain requests stay in chat mode."""
        patterns = [
            "explain what is machine learning",
            "tell me about Python",
            "describe how the internet works",
            "give me an overview of AI",
        ]
        for p in patterns:
            intent = classify_intent(p)
            assert intent == Intent.CHAT, f"'{p}' should be CHAT but got {intent}"

    def test_question_marks(self):
        """Test that any input ending with ? is chat."""
        inputs = [
            "what is this?",
            "how does it work?",
            "why is it like that?",
            "can you help me?",
        ]
        for inp in inputs:
            intent = classify_intent(inp)
            assert intent == Intent.CHAT, f"'{inp}' should be CHAT but got {intent}"


class TestAgentIntentRouting:
    """Test that the agent routes intents correctly."""

    @pytest.fixture
    def mock_agent(self):
        """Create a mock agent with mocked dependencies."""
        agent = JarvisAgent(
            config=MagicMock(),
            memory_manager=MagicMock(),
            tool_registry=MagicMock(),
            llm_client=MagicMock()
        )
        # Mock the LLM client
        agent.llm.generate_with_history = AsyncMock(return_value="Test response")
        agent.llm.generate = AsyncMock(return_value="Test response")
        
        # Mock executor
        agent.executor.execute = AsyncMock(return_value=MagicMock(
            success=True,
            summary="Task completed",
            error=None,
            completed_steps=[]
        ))
        
        # Mock memory manager
        agent.memory.remember = MagicMock()
        agent.memory.recall = MagicMock(return_value=[])
        agent.memory.add_user_message = MagicMock()
        agent.memory.add_assistant_message = MagicMock()
        
        return agent

    @pytest.mark.asyncio
    async def test_chat_question_does_not_use_tools(self, mock_agent):
        """Test that factual questions don't trigger tool execution."""
        # Override recall to return empty (no stored memory)
        mock_agent.memory.recall = MagicMock(return_value=[])
        
        response = await mock_agent.process("what is machine learning")
        
        # Should call LLM directly, not executor
        mock_agent.llm.generate_with_history.assert_called_once()
        mock_agent.executor.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_study_plan_does_not_use_tools(self, mock_agent):
        """Test that study plan requests don't trigger tools."""
        response = await mock_agent.process("create a study plan for machine learning")
        
        # Should call LLM directly, not executor
        mock_agent.llm.generate_with_history.assert_called_once()
        mock_agent.executor.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_tool_command_uses_executor(self, mock_agent):
        """Test that explicit tool commands use executor."""
        response = await mock_agent.process("ls -la /home")
        
        # Should call executor
        mock_agent.executor.execute.assert_called_once()
        mock_agent.llm.generate_with_history.assert_not_called()

    @pytest.mark.asyncio
    async def test_memory_store_calls_memory(self, mock_agent):
        """Test that memory store calls memory manager."""
        response = await mock_agent.process("remember my favorite color is blue")
        
        # Should call memory.remember
        mock_agent.memory.remember.assert_called()
        assert "blue" in response.lower() or "favorite" in response.lower()

    @pytest.mark.asyncio
    async def test_memory_recall_calls_memory(self, mock_agent):
        """Test that memory recall calls memory manager."""
        mock_agent.memory.recall = MagicMock(return_value=[
            {"key": "color", "value": "blue"}
        ])
        
        response = await mock_agent.process("what is my favorite color")
        
        # Should call memory.recall
        mock_agent.memory.recall.assert_called()


class TestMemoryOperations:
    """Test memory store and recall handlers."""

    @pytest.fixture
    def agent_with_memory(self):
        """Create agent with real memory manager."""
        agent = JarvisAgent(
            memory_manager=MagicMock()
        )
        agent.memory.remember = MagicMock()
        agent.memory.recall = MagicMock(return_value=[])
        return agent

    @pytest.mark.asyncio
    async def test_memory_store_extracts_key_value(self, agent_with_memory):
        """Test that memory store extracts key and value correctly."""
        await agent_with_memory._handle_memory_store("remember my favorite color is blue")
        
        agent_with_memory.memory.remember.assert_called()
        call_args = agent_with_memory.memory.remember.call_args
        # Key should contain "color" 
        key = call_args[0][0] if call_args[0] else call_args[1].get("key")
        assert "color" in key.lower()

    @pytest.mark.asyncio
    async def test_memory_recall_returns_info(self, agent_with_memory):
        """Test that memory recall returns stored information."""
        agent_with_memory.memory.recall = MagicMock(return_value=[
            {"key": "color", "value": "blue"}
        ])
        
        response = await agent_with_memory._handle_memory_recall("what is my favorite color")
        
        assert "blue" in response or "color" in response.lower()

    @pytest.mark.asyncio
    async def test_memory_recall_not_found(self, agent_with_memory):
        """Test that memory recall handles not found case."""
        agent_with_memory.memory.recall = MagicMock(return_value=[])
        
        response = await agent_with_memory._handle_memory_recall("what is my favorite food")
        
        assert "don't" in response.lower() or "don't" in response.lower() or "not" in response.lower()


class TestEdgeCases:
    """Test edge cases in intent classification."""

    def test_ambiguous_remember_pattern(self):
        """Test that 'remember' without ? is memory store."""
        intent = classify_intent("remember the meeting is at 3pm")
        assert intent == Intent.MEMORY_STORE

    def test_remember_with_question(self):
        """Test that 'remember?' is recall."""
        intent = classify_intent("do you remember my name?")
        assert intent == Intent.MEMORY_RECALL

    def test_create_file_vs_create_plan(self):
        """Test that 'create file' is tool but 'create plan' is chat."""
        # Create file should be tool
        assert classify_intent("create file test.txt") == Intent.TOOL_EXECUTION
        
        # Create study plan should be chat
        assert classify_intent("create study plan") == Intent.CHAT

    def test_explain_vs_explain_file(self):
        """Test that 'explain X' is chat but 'explain file' context matters."""
        # Plain explain is chat
        assert classify_intent("explain quantum physics") == Intent.CHAT

    def test_short_inputs(self):
        """Test that short inputs default to chat."""
        assert classify_intent("hi") == Intent.CHAT
        assert classify_intent("ok") == Intent.CHAT
        assert classify_intent("yes") == Intent.CHAT

    def test_empty_input(self):
        """Test empty input defaults to chat."""
        assert classify_intent("") == Intent.CHAT
        assert classify_intent("   ") == Intent.CHAT


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
