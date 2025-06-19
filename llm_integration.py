#!/usr/bin/env python3
"""
Local LLM Integration for MeshAdmin Performance Analytics Suite

This module provides integration with local Large Language Models for enhanced
analytics, intelligent insights, and natural language processing capabilities.

Features:
- Local model loading from custom directory (/Volumes/Seagate-5TB/models)
- Performance analysis with LLM insights
- Natural language alerts and recommendations
- Intelligent data interpretation
- Customizable model selection
"""

import os
import sys
import json
import logging
import time
import re
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("llm-integration")

# =============================================================================
# Local LLM Configuration
# =============================================================================

@dataclass
class LLMConfig:
    """Configuration for Local LLM Integration"""
    models_path: str = "/Users/cnelson/models"
    default_model: str = "llama-3.2-8b"  # Adjustable based on available models
    max_tokens: int = 2048
    temperature: float = 0.7
    context_window: int = 4096
    enable_gpu: bool = True
    model_format: str = "gguf"  # Common format for local models
    
    def __post_init__(self):
        # Ensure models path exists
        if not os.path.exists(self.models_path):
            logger.warning(f"Models path {self.models_path} does not exist")

# =============================================================================
# Local LLM Interface
# =============================================================================

class LocalLLMInterface:
    """Interface for Local Large Language Models"""
    
    def __init__(self, config: LLMConfig = None):
        self.config = config or LLMConfig()
        self.model = None
        self.model_loaded = False
        self.available_models = []
        
        # Try to import local LLM libraries
        self.llm_library = self._detect_llm_library()
        
        # Scan for available models
        self._scan_available_models()
        
        logger.info(f"🤖 Local LLM Interface initialized")
        logger.info(f"   Models path: {self.config.models_path}")
        logger.info(f"   Available models: {len(self.available_models)}")
        logger.info(f"   LLM Library: {self.llm_library}")
    
    def _detect_llm_library(self) -> str:
        """Detect which local LLM library is available"""
        libraries = [
            ("llama_cpp", "llama-cpp-python"),
            ("transformers", "transformers + torch"),
            ("ctransformers", "ctransformers"),
            ("gpt4all", "GPT4All"),
            ("localai", "LocalAI")
        ]
        
        for lib_name, description in libraries:
            try:
                __import__(lib_name)
                logger.info(f"✅ Found {description}")
                return lib_name
            except ImportError:
                continue
        
        logger.warning("⚠️ No local LLM library found. Install one of: llama-cpp-python, transformers, ctransformers, gpt4all")
        return "none"
    
    def _scan_available_models(self) -> None:
        """Scan the models directory for available models"""
        if not os.path.exists(self.config.models_path):
            return
        
        model_extensions = ['.gguf', '.bin', '.safetensors', '.pt', '.pth']
        
        try:
            for root, dirs, files in os.walk(self.config.models_path):
                for file in files:
                    # Skip system/hidden files and small files
                    if (file.startswith('._') or file.startswith('.') or 
                        not any(file.lower().endswith(ext) for ext in model_extensions)):
                        continue
                    
                    model_path = os.path.join(root, file)
                    
                    # Skip files smaller than 100MB (likely not proper model files)
                    try:
                        file_size = os.path.getsize(model_path)
                        if file_size < 100 * 1024 * 1024:  # 100MB minimum
                            continue
                    except OSError:
                        continue
                        
                    relative_path = os.path.relpath(model_path, self.config.models_path)
                    
                    # Normalize model name by collapsing shards
                    original_name = os.path.splitext(file)[0]
                    display_name = re.sub(r"-0\d{3,}-of-\d{4,}", "", original_name)

                    model_info = {
                        'name': original_name,  # Keep original for file operations
                        'display_name': display_name,  # Clean name for display
                        'path': model_path,
                        'relative_path': relative_path,
                        'size_mb': round(file_size / (1024 * 1024), 1),
                        'format': os.path.splitext(file)[1][1:].lower()
                    }
                    self.available_models.append(model_info)
            
            # Sort by size (smaller models first for faster loading)
            self.available_models.sort(key=lambda x: x['size_mb'])
            
        except Exception as e:
            logger.error(f"Error scanning models directory: {e}")
    
    def list_available_models(self) -> List[Dict[str, Any]]:
        """Get list of available models"""
        return self.available_models
    
    def load_model(self, model_name: Optional[str] = None) -> bool:
        """Load a specific model or the default model"""
        if self.llm_library == "none":
            logger.error("No LLM library available for model loading")
            return False
        
        model_to_load = model_name or self.config.default_model
        
        # Find the model file
        model_file = None
        for model in self.available_models:
            if model_to_load.lower() in model['name'].lower():
                model_file = model['path']
                break
        
        if not model_file:
            logger.error(f"Model '{model_to_load}' not found in {self.config.models_path}")
            return False
        
        try:
            logger.info(f"🔄 Loading model: {model_to_load}")
            logger.info(f"   Path: {model_file}")
            
            if self.llm_library == "llama_cpp":
                self.model = self._load_llama_cpp_model(model_file)
            elif self.llm_library == "transformers":
                self.model = self._load_transformers_model(model_file)
            elif self.llm_library == "ctransformers":
                self.model = self._load_ctransformers_model(model_file)
            elif self.llm_library == "gpt4all":
                self.model = self._load_gpt4all_model(model_file)
            
            if self.model:
                self.model_loaded = True
                logger.info(f"✅ Model loaded successfully: {model_to_load}")
                return True
            else:
                logger.error(f"❌ Failed to load model: {model_to_load}")
                return False
                
        except Exception as e:
            logger.error(f"Error loading model {model_to_load}: {e}")
            return False
    
    def _load_llama_cpp_model(self, model_path: str):
        """Load model using llama-cpp-python"""
        try:
            from llama_cpp import Llama
            
            model = Llama(
                model_path=model_path,
                n_ctx=self.config.context_window,
                n_gpu_layers=-1 if self.config.enable_gpu else 0,
                verbose=False
            )
            return model
        except Exception as e:
            logger.error(f"Error loading with llama-cpp-python: {e}")
            return None
    
    def _load_transformers_model(self, model_path: str):
        """Load model using transformers library"""
        try:
            from transformers import AutoTokenizer, AutoModelForCausalLM
            import torch
            
            # Load tokenizer and model
            tokenizer = AutoTokenizer.from_pretrained(model_path)
            model = AutoModelForCausalLM.from_pretrained(
                model_path,
                torch_dtype=torch.float16 if self.config.enable_gpu else torch.float32,
                device_map="auto" if self.config.enable_gpu else "cpu"
            )
            
            return {'model': model, 'tokenizer': tokenizer}
        except Exception as e:
            logger.error(f"Error loading with transformers: {e}")
            return None
    
    def _load_ctransformers_model(self, model_path: str):
        """Load model using ctransformers"""
        try:
            from ctransformers import AutoModelForCausalLM
            
            model = AutoModelForCausalLM.from_pretrained(
                model_path,
                model_type="llama",  # Adjust based on model
                gpu_layers=40 if self.config.enable_gpu else 0
            )
            return model
        except Exception as e:
            logger.error(f"Error loading with ctransformers: {e}")
            return None
    
    def _load_gpt4all_model(self, model_path: str):
        """Load model using GPT4All"""
        try:
            from gpt4all import GPT4All
            
            model = GPT4All(model_path)
            return model
        except Exception as e:
            logger.error(f"Error loading with GPT4All: {e}")
            return None
    
    def generate_response(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        """Generate response from the loaded model"""
        if not self.model_loaded or not self.model:
            return "Model not loaded. Please load a model first."
        
        max_tokens = max_tokens or self.config.max_tokens
        
        try:
            if self.llm_library == "llama_cpp":
                response = self.model(
                    prompt,
                    max_tokens=max_tokens,
                    temperature=self.config.temperature,
                    stop=["</s>", "\n\n"]
                )
                return response['choices'][0]['text'].strip()
            
            elif self.llm_library == "transformers":
                tokenizer = self.model['tokenizer']
                model = self.model['model']
                
                inputs = tokenizer.encode(prompt, return_tensors="pt")
                
                with torch.no_grad():
                    outputs = model.generate(
                        inputs,
                        max_new_tokens=max_tokens,
                        temperature=self.config.temperature,
                        do_sample=True,
                        pad_token_id=tokenizer.eos_token_id
                    )
                
                response = tokenizer.decode(outputs[0], skip_special_tokens=True)
                return response[len(prompt):].strip()
            
            elif self.llm_library == "ctransformers":
                return self.model(prompt, max_new_tokens=max_tokens, temperature=self.config.temperature)
            
            elif self.llm_library == "gpt4all":
                return self.model.generate(prompt, max_tokens=max_tokens, temp=self.config.temperature)
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return f"Error generating response: {str(e)}"
    
    def is_available(self) -> bool:
        """Check if LLM integration is available and ready"""
        return self.llm_library != "none" and len(self.available_models) > 0

# =============================================================================
# Performance Analytics LLM Integration
# =============================================================================

class PerformanceAnalyticsLLM:
    """LLM Integration for Performance Analytics"""
    
    def __init__(self, config: LLMConfig = None):
        self.config = config or LLMConfig()
        self.llm = LocalLLMInterface(self.config)
        self.analysis_templates = self._load_analysis_templates()
        
        logger.info("🧠 Performance Analytics LLM Integration initialized")
    
    def _load_analysis_templates(self) -> Dict[str, str]:
        """Load prompt templates for different analysis types"""
        return {
            'performance_analysis': """
You are an expert system administrator analyzing performance metrics for a network infrastructure system.

Current Performance Data:
{metrics_data}

Please provide a concise analysis focusing on:
1. Key performance indicators and their current status
2. Any concerning trends or anomalies
3. Specific recommendations for optimization
4. Risk assessment (low/medium/high)

Keep the response practical and actionable.
""",
            
            'anomaly_explanation': """
You are analyzing an anomaly detected in network performance metrics.

Anomaly Details:
- Metric: {metric_name}
- Current Value: {current_value}
- Expected Range: {expected_range}
- Confidence: {confidence}
- Context: {context}

Please explain:
1. What this anomaly likely indicates
2. Potential root causes
3. Recommended investigation steps
4. Urgency level

Be specific and technical but clear.
""",
            
            'alert_summary': """
You are summarizing multiple performance alerts for a system administrator.

Current Alerts:
{alerts_data}

Please provide:
1. A brief executive summary of the current situation
2. Priority ranking of issues
3. Recommended immediate actions
4. Dependencies between alerts

Be concise but comprehensive.
""",
            
            'capacity_planning': """
You are providing capacity planning advice based on performance trends.

Performance Trends:
{trends_data}

Current Utilization:
{utilization_data}

Please advise on:
1. Current capacity utilization assessment
2. Projected capacity needs (next 30/90 days)
3. Scaling recommendations
4. Cost-benefit considerations

Focus on practical, data-driven recommendations.
"""
        }
    
    def start(self) -> bool:
        """Start the LLM integration"""
        if not self.llm.is_available():
            logger.warning("LLM integration not available - no models found")
            return False
        
        # Try to load the default model
        if not self.llm.model_loaded:
            success = self.llm.load_model()
            if not success:
                logger.warning("Failed to load default model, trying first available model")
                if self.llm.available_models:
                    first_model = self.llm.available_models[0]['name']
                    success = self.llm.load_model(first_model)
        
        return self.llm.model_loaded
    
    def analyze_performance_data(self, metrics_data: Dict[str, Any]) -> str:
        """Analyze performance data with LLM insights"""
        if not self.llm.model_loaded:
            return "LLM not available for analysis"
        
        # Format metrics data for LLM
        formatted_data = self._format_metrics_for_llm(metrics_data)
        
        prompt = self.analysis_templates['performance_analysis'].format(
            metrics_data=formatted_data
        )
        
        return self.llm.generate_response(prompt)
    
    def explain_anomaly(self, anomaly_data: Dict[str, Any]) -> str:
        """Get LLM explanation of an anomaly"""
        if not self.llm.model_loaded:
            return "LLM not available for anomaly explanation"
        
        prompt = self.analysis_templates['anomaly_explanation'].format(
            metric_name=anomaly_data.get('metric_name', 'Unknown'),
            current_value=anomaly_data.get('value', 'Unknown'),
            expected_range=anomaly_data.get('expected_range', 'Unknown'),
            confidence=anomaly_data.get('confidence', 'Unknown'),
            context=anomaly_data.get('context', 'No additional context')
        )
        
        return self.llm.generate_response(prompt)
    
    def summarize_alerts(self, alerts: List[Dict[str, Any]]) -> str:
        """Summarize multiple alerts with LLM"""
        if not self.llm.model_loaded:
            return "LLM not available for alert summarization"
        
        alerts_text = "\n".join([
            f"- {alert.get('title', 'Alert')}: {alert.get('message', 'No details')} (Severity: {alert.get('severity', 'Unknown')})"
            for alert in alerts[:10]  # Limit to first 10 alerts
        ])
        
        prompt = self.analysis_templates['alert_summary'].format(
            alerts_data=alerts_text
        )
        
        return self.llm.generate_response(prompt)
    
    def generate_capacity_recommendations(self, trends_data: Dict[str, Any], utilization_data: Dict[str, Any]) -> str:
        """Generate capacity planning recommendations"""
        if not self.llm.model_loaded:
            return "LLM not available for capacity planning"
        
        trends_text = self._format_trends_for_llm(trends_data)
        utilization_text = self._format_utilization_for_llm(utilization_data)
        
        prompt = self.analysis_templates['capacity_planning'].format(
            trends_data=trends_text,
            utilization_data=utilization_text
        )
        
        return self.llm.generate_response(prompt)
    
    def _format_metrics_for_llm(self, metrics_data: Dict[str, Any]) -> str:
        """Format metrics data for LLM consumption"""
        summary = metrics_data.get('performance_summary', {})
        
        formatted = []
        if 'total_network_flows' in summary:
            formatted.append(f"Network Flows: {summary['total_network_flows']}")
        if 'packet_rate' in summary:
            formatted.append(f"Packet Rate: {summary['packet_rate']:.1f} pps")
        if 'total_lb_connections' in summary:
            formatted.append(f"Load Balancer Connections: {summary['total_lb_connections']}")
        if 'average_response_time' in summary:
            formatted.append(f"Response Time: {summary['average_response_time']:.1f} ms")
        if 'error_rate' in summary:
            formatted.append(f"Error Rate: {summary['error_rate']*100:.2f}%")
        if 'health_score' in summary:
            formatted.append(f"Health Score: {summary['health_score']*100:.1f}%")
        
        return "\n".join(formatted) if formatted else "No performance data available"
    
    def _format_trends_for_llm(self, trends_data: Dict[str, Any]) -> str:
        """Format trends data for LLM"""
        # This would typically contain historical trend analysis
        return json.dumps(trends_data, indent=2)
    
    def _format_utilization_for_llm(self, utilization_data: Dict[str, Any]) -> str:
        """Format utilization data for LLM"""
        # This would contain current resource utilization metrics
        return json.dumps(utilization_data, indent=2)
    
    def get_model_status(self) -> Dict[str, Any]:
        """Get current model status and information"""
        return {
            'available': self.llm.is_available(),
            'model_loaded': self.llm.model_loaded,
            'library': self.llm.llm_library,
            'models_path': self.config.models_path,
            'available_models': len(self.llm.available_models),
            'model_list': [
                {
                    'name': model['name'],
                    'size_mb': model['size_mb'],
                    'format': model['format']
                }
                for model in self.llm.available_models
            ]
        }

# =============================================================================
# Factory Functions
# =============================================================================

def create_llm_integration(config: LLMConfig = None) -> PerformanceAnalyticsLLM:
    """Factory function to create LLM integration"""
    return PerformanceAnalyticsLLM(config)

# =============================================================================
# Command Line Interface
# =============================================================================

def main():
    """Main entry point for testing LLM integration"""
    print("🤖 Local LLM Integration for MeshAdmin Performance Analytics")
    print("=" * 65)
    
    # Create LLM integration
    config = LLMConfig(
        models_path="/Volumes/Seagate-5TB/models",
        default_model="llama"  # Will match any model with "llama" in the name
    )
    
    llm_analytics = create_llm_integration(config)
    
    # Get status
    status = llm_analytics.get_model_status()
    print(f"📊 LLM Status:")
    print(f"  Available: {status['available']}")
    print(f"  Library: {status['library']}")
    print(f"  Models path: {status['models_path']}")
    print(f"  Available models: {status['available_models']}")
    
    if status['model_list']:
        print(f"\n📚 Available Models:")
        for model in status['model_list'][:5]:  # Show first 5
            print(f"  - {model['name']} ({model['size_mb']} MB, {model['format']})")
    
    # Try to start LLM
    if status['available']:
        print(f"\n🔄 Attempting to load model...")
        success = llm_analytics.start()
        
        if success:
            print(f"✅ LLM model loaded successfully!")
            
            # Test with sample data
            sample_metrics = {
                'performance_summary': {
                    'total_network_flows': 1500,
                    'packet_rate': 2500.0,
                    'total_lb_connections': 150,
                    'average_response_time': 125.5,
                    'error_rate': 0.02,
                    'health_score': 0.95
                }
            }
            
            print(f"\n🧠 Testing LLM analysis...")
            analysis = llm_analytics.analyze_performance_data(sample_metrics)
            print(f"Analysis preview: {analysis[:200]}...")
            
        else:
            print(f"❌ Failed to load LLM model")
    else:
        print(f"\n⚠️ LLM integration not available")
        print(f"   Ensure models are available in: {config.models_path}")
        print(f"   Install an LLM library: pip install llama-cpp-python")

if __name__ == "__main__":
    main()

