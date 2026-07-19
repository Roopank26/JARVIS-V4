"""
Example JARVIS Plugin

This demonstrates how to create a plugin for JARVIS.
"""

import logging
from typing import Any, Dict, List, Optional
from jarvis.plugins.plugin_manager import (
    IntentPlugin,
    ToolPlugin,
    MemoryPlugin,
)

logger = logging.getLogger(__name__)


class WeatherPlugin(IntentPlugin):
    """
    Example plugin that provides weather information.
    
    Demonstrates IntentPlugin - handles custom intents.
    """
    
    PLUGIN_ID = "weather"
    PLUGIN_NAME = "Weather Information"
    PLUGIN_VERSION = "1.0.0"
    PLUGIN_DESCRIPTION = "Provides weather information for any location"
    PLUGIN_AUTHOR = "JARVIS Team"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._weather_api_key = self.config.get("api_key", "")
    
    async def initialize(self, jarvis_instance: Any) -> bool:
        """Initialize the weather plugin."""
        await super().initialize(jarvis_instance)
        logger.info(f"Weather plugin initialized with API key: {bool(self._weather_api_key)}")
        return True
    
    async def match_intent(self, text: str) -> Optional[str]:
        """Match weather-related queries."""
        weather_keywords = [
            "weather", "temperature", "forecast", "rain", "sunny",
            "hot", "cold", "humid", "climate"
        ]
        
        text_lower = text.lower()
        
        # Check for weather intent patterns
        patterns = [
            r"\bweather\b",
            r"\bhow\s+is\s+the\s+(?:weather|temperature)\b",
            r"\bwhat(?:\'s| is)\s+the\s+(?:weather|temperature|forecast)\b",
            r"\b(?:temperature|forecast)\s+(?:in|for)\s+\w+\b",
        ]
        
        import re
        for pattern in patterns:
            if re.search(pattern, text_lower):
                return "weather_query"
        
        # Check for keywords
        if any(kw in text_lower for kw in weather_keywords):
            return "weather_query"
        
        return None
    
    async def handle_intent(self, text: str, context: Dict[str, Any]) -> str:
        """Handle weather queries."""
        import re
        
        # Extract location
        location_match = re.search(
            r"(?:in|for|at)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
            text
        )
        location = location_match.group(1) if location_match else "current location"
        
        # Mock weather data
        conditions = ["sunny", "partly cloudy", "cloudy", "rainy", "clear"]
        temps = range(15, 35)
        
        import random
        condition = random.choice(conditions)
        temp = random.choice(list(temps))
        
        return f"""[Weather Report]
📍 Location: {location}
🌡️ Temperature: {temp}°C ({temp * 9 // 5 + 32}°F)
🌤️ Conditions: {condition.title()}

Note: This is a demo. Connect a real weather API for live data."""


class CalculatorToolPlugin(ToolPlugin):
    """
    Example plugin that provides calculation tools.
    
    Demonstrates ToolPlugin - adds executable tools.
    """
    
    PLUGIN_ID = "calculator"
    PLUGIN_NAME = "Calculator Tools"
    PLUGIN_VERSION = "1.0.0"
    PLUGIN_DESCRIPTION = "Provides mathematical calculation tools"
    PLUGIN_AUTHOR = "JARVIS Team"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
    
    async def initialize(self, jarvis_instance: Any) -> bool:
        """Initialize the calculator plugin."""
        await super().initialize(jarvis_instance)
        return True
    
    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Return tool definitions."""
        return [
            {
                "name": "calculate",
                "description": "Evaluate a mathematical expression",
                "parameters": {
                    "expression": {
                        "type": "string",
                        "description": "Mathematical expression (e.g., '2+2', 'sqrt(16)')"
                    }
                }
            },
            {
                "name": "convert_units",
                "description": "Convert between units",
                "parameters": {
                    "value": {"type": "number", "description": "Value to convert"},
                    "from_unit": {"type": "string", "description": "Source unit"},
                    "to_unit": {"type": "string", "description": "Target unit"}
                }
            }
        ]
    
    async def execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        """Execute a calculator tool."""
        if tool_name == "calculate":
            return self._calculate(args.get("expression", ""))
        elif tool_name == "convert_units":
            return self._convert_units(
                args.get("value", 0),
                args.get("from_unit", ""),
                args.get("to_unit", "")
            )
        return {"error": f"Unknown tool: {tool_name}"}
    
    def _calculate(self, expression: str) -> Dict[str, Any]:
        """Evaluate mathematical expression."""
        try:
            # Safe evaluation using ast
            import ast
            import operator
            
            ops = {
                ast.Add: operator.add,
                ast.Sub: operator.sub,
                ast.Mult: operator.mul,
                ast.Div: operator.truediv,
                ast.Pow: operator.pow,
                ast.USub: operator.neg,
            }
            
            def eval_expr(node):
                if isinstance(node, ast.Num):
                    return node.n
                elif isinstance(node, ast.BinOp):
                    return ops[type(node.op)](eval_expr(node.left), eval_expr(node.right))
                elif isinstance(node, ast.UnaryOp):
                    return ops[type(node.op)](eval_expr(node.operand))
                else:
                    raise ValueError(f"Unsupported operation: {node}")
            
            tree = ast.parse(expression, mode="eval")
            result = eval_expr(tree.body)
            
            return {"success": True, "expression": expression, "result": result}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _convert_units(self, value: float, from_unit: str, to_unit: str) -> Dict[str, Any]:
        """Convert between units."""
        conversions = {
            ("km", "miles"): 0.621371,
            ("miles", "km"): 1.60934,
            ("celsius", "fahrenheit"): (lambda x: x * 9/5 + 32),
            ("fahrenheit", "celsius"): (lambda x: (x - 32) * 5/9),
            ("kg", "lbs"): 2.20462,
            ("lbs", "kg"): 0.453592,
        }
        
        key = (from_unit.lower(), to_unit.lower())
        
        if key in conversions:
            factor = conversions[key]
            if callable(factor):
                result = factor(value)
            else:
                result = value * factor
            
            return {
                "success": True,
                "from": f"{value} {from_unit}",
                "to": f"{result:.2f} {to_unit}"
            }
        
        return {"success": False, "error": f"Conversion {from_unit} to {to_unit} not supported"}


class NotesMemoryPlugin(MemoryPlugin):
    """
    Example plugin for storing notes.
    
    Demonstrates MemoryPlugin - extends memory capabilities.
    """
    
    PLUGIN_ID = "notes"
    PLUGIN_NAME = "Notes Memory"
    PLUGIN_VERSION = "1.0.0"
    PLUGIN_DESCRIPTION = "Store and recall notes"
    PLUGIN_AUTHOR = "JARVIS Team"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._notes: Dict[str, Dict[str, Any]] = {}
    
    async def initialize(self, jarvis_instance: Any) -> bool:
        """Initialize the notes plugin."""
        await super().initialize(jarvis_instance)
        return True
    
    async def store(self, key: str, value: Any, metadata: Optional[Dict] = None) -> bool:
        """Store a note."""
        self._notes[key] = {
            "value": value,
            "metadata": metadata or {},
        }
        return True
    
    async def recall(self, key: str) -> Optional[Any]:
        """Recall a note by key."""
        note = self._notes.get(key)
        return note["value"] if note else None
    
    async def search(self, query: str) -> List[Any]:
        """Search notes."""
        results = []
        query_lower = query.lower()
        
        for key, note in self._notes.items():
            if query_lower in key.lower():
                results.append({"key": key, **note})
            elif query_lower in str(note["value"]).lower():
                results.append({"key": key, **note})
        
        return results
