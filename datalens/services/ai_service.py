from groq import Groq
import pandas as pd
import numpy as np
import json
import re
from typing import Dict, List, Any, Optional
import os

class AIService:
    
    def __init__(self):
        """Initialize AI service with NVIDIA NIM (DeepSeek-v4-flash) or fallback"""
        self.api_key = os.getenv('NVIDIA_API_KEY', '') or os.getenv('GEMINI_API_KEY', '') or os.getenv('GROQ_API_KEY', '')
        # Check if key is configured and not a placeholder
        self.is_configured_flag = bool(self.api_key and not self.api_key.startswith('YOUR_'))
        self.model = os.getenv('NVIDIA_MODEL', 'meta/llama-3.1-8b-instruct')
        self.fallback_models = self._unique_models([
            self.model,
            'nvidia/llama-3.1-nemotron-nano-8b-v1',
            'deepseek-ai/deepseek-v4-flash',
        ])
        self.base_url = "https://integrate.api.nvidia.com/v1/chat/completions"
        self._api_unavailable = False
        self.last_error = None

    def is_configured(self) -> bool:
        """Check if AI service is properly configured"""
        return self.is_configured_flag
    
    def _call_groq(self, prompt: str, system_prompt: str = "You are a data analysis expert.", max_tokens: int = 2000) -> str:
        """Call NVIDIA NIM API using HTTPX"""
        if not self.is_configured_flag:
            raise Exception(self._configuration_message())
        if self._api_unavailable:
            raise Exception("AI service is temporarily unavailable after a previous API failure.")
            
        import httpx
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        errors = []

        for model in self.fallback_models:
            payload = {
                "model": model,
                "messages": messages,
                "temperature": 0.4,
                "top_p": 0.9,
                "max_tokens": min(max_tokens, 4096)
            }

            try:
                timeout = httpx.Timeout(30.0, connect=8.0)
                with httpx.Client(timeout=timeout) as client:
                    response = client.post(self.base_url, headers=headers, json=payload)
                    response.raise_for_status()
                    data = response.json()
                    self.model = model
                    return data['choices'][0]['message']['content']
            except Exception as e:
                errors.append(f"{model}: {self._format_api_error(e)}")
                continue

        self._api_unavailable = True
        self.last_error = "NVIDIA API request failed for all models. " + " | ".join(errors)
        print(f"NVIDIA NIM API Error: {self.last_error}")
        raise Exception(self.last_error)

    def _unique_models(self, models: List[str]) -> List[str]:
        unique = []
        for model in models:
            if model and model not in unique:
                unique.append(model)
        return unique

    def _configuration_message(self) -> str:
        return "AI service is not configured. Set NVIDIA_API_KEY in .env, then restart the application."

    def _format_api_error(self, error: Exception) -> str:
        response = getattr(error, 'response', None)
        if response is not None:
            status_code = getattr(response, 'status_code', None)
            try:
                detail = response.text[:300]
            except Exception:
                detail = str(error)
            return f"NVIDIA API returned HTTP {status_code}: {detail}"
        error_text = str(error).strip()
        if error_text:
            return f"NVIDIA API request failed: {error_text}"
        return f"NVIDIA API request failed: {type(error).__name__}"
    
    def analyze_dataset_overview(self, df: pd.DataFrame, dataset_name: str) -> Dict[str, Any]:
        """Generate AI-powered overview of the dataset"""
        if not self.is_configured():
            return self._fallback_analysis(df)
        
        try:
            # Prepare dataset summary for AI
            summary = self._prepare_dataset_summary(df, dataset_name)
            
            prompt = f"""
            Analyze this dataset and provide insights in JSON format:
            
            Dataset Summary:
            {summary}
            
            Provide analysis in this exact JSON format:
            {{
                "overview": "Brief description of what this dataset contains",
                "key_insights": ["insight 1", "insight 2", "insight 3"],
                "data_quality": "excellent/good/fair/poor",
                "potential_uses": ["use case 1", "use case 2"],
                "recommendations": ["recommendation 1", "recommendation 2"],
                "interesting_patterns": ["pattern 1", "pattern 2"]
            }}
            
            Be specific and actionable. Focus on business insights.
            """
            
            response_text = self._call_groq(prompt)
            return self._parse_ai_response(response_text)
            
        except Exception as e:
            print(f"AI Analysis failed: {e}")
            return self._fallback_analysis(df)
    
    def suggest_visualizations(self, df: pd.DataFrame, user_goal: str = "") -> List[Dict[str, Any]]:
        """AI-powered chart recommendations"""
        if not self.is_configured():
            return self._fallback_visualizations(df)
        
        try:
            summary = self._prepare_dataset_summary(df, "Dataset")
            
            prompt = f"""
            Based on this dataset, suggest the best visualizations:
            
            Dataset Summary:
            {summary}
            
            User Goal: {user_goal if user_goal else "General data exploration"}
            
            Suggest exactly 3-5 visualizations in this JSON format:
            [
                {{
                    "chart_type": "bar/line/pie/scatter/histogram/heatmap",
                    "title": "Descriptive chart title",
                    "description": "Why this chart is useful",
                    "x_column": "column_name",
                    "y_column": "column_name" if applicable,
                    "insight": "What this chart will reveal"
                }}
            ]
            
            Choose the most impactful visualizations for understanding the data.
            """
            
            response_text = self._call_groq(prompt)
            return self._parse_ai_response(response_text)
            
        except Exception as e:
            print(f"AI Visualization failed: {e}")
            return self._fallback_visualizations(df)
    
    def natural_language_query(self, df: pd.DataFrame, question: str) -> Dict[str, Any]:
        """Answer natural language questions about the data"""
        if not self.is_configured():
            return self._fallback_query(question)
        
        try:
            summary = self._prepare_dataset_summary(df, "Dataset")
            
            prompt = f"""
            Answer this question about the dataset:
            
            Question: {question}
            
            Dataset Summary:
            {summary}
            
            Provide answer in this JSON format:
            {{
                "answer": "Direct answer to the question",
                "confidence": "high/medium/low",
                "suggested_visualization": {{
                    "chart_type": "type",
                    "title": "title",
                    "description": "why"
                }} if applicable,
                "related_columns": ["col1", "col2"],
                "follow_up_questions": ["question 1", "question 2"]
            }}
            
            Be helpful and specific. If you cannot answer confidently, say so.
            """
            
            response_text = self._call_groq(prompt)
            return self._parse_ai_response(response_text)
            
        except Exception as e:
            print(f"AI Query failed: {e}")
            return self._fallback_query(question)
    
    def data_cleaning_suggestions(self, df: pd.DataFrame) -> Dict[str, Any]:
        """AI-powered data cleaning recommendations"""
        if not self.is_configured():
            return self._fallback_cleaning(df)
        
        try:
            summary = self._prepare_dataset_summary(df, "Dataset")
            
            prompt = f"""
            Analyze this dataset for data quality issues and suggest cleaning:
            
            Dataset Summary:
            {summary}
            
            Provide recommendations in this JSON format:
            {{
                "overall_quality": "excellent/good/fair/poor",
                "issues_found": [
                    {{
                        "issue_type": "missing_values/duplicates/outliers/data_types",
                        "column": "column_name",
                        "severity": "high/medium/low",
                        "description": "what's wrong",
                        "recommendation": "how to fix"
                    }}
                ],
                "cleaning_priority": ["issue1", "issue2"],
                "estimated_effort": "low/medium/high"
            }}
            
            Focus on actionable cleaning steps.
            """
            
            response_text = self._call_groq(prompt)
            return self._parse_ai_response(response_text)
            
        except Exception as e:
            print(f"AI Cleaning failed: {e}")
            return self._fallback_cleaning(df)
    
    def generate_report(self, df: pd.DataFrame, report_type: str = "summary") -> str:
        """Generate comprehensive AI-powered data report (Markdown; render to HTML in the route)."""
        self.last_error = None
        if not self.is_configured():
            self.last_error = self._configuration_message()
            return self._fallback_report(df)
        
        try:
            summary = self._prepare_dataset_summary(df, "Dataset")
            md_rules = """
            Respond in clean Markdown only (no HTML wrapper):
            - Use ## for main sections and ### for subsections
            - Use bullet lists with - for items
            - Use **bold** for emphasis on key metrics
            - Use a short table when comparing several metrics (Markdown pipe table)
            - Do not wrap the answer in ``` fences for the whole document
            """
            
            if report_type == "executive":
                prompt = f"""
                Generate an executive summary report for this dataset.
                
                Dataset Summary:
                {summary}
                
                Structure:
                ## Executive overview
                2–3 sentences for leadership.
                ## Key findings
                3–5 bullets with concrete numbers from the summary where possible.
                ## Business implications
                2–3 bullets tied to decisions or risks.
                ## Recommendations
                3–4 numbered, actionable next steps.
                
                {md_rules}
                Keep it concise and business-focused.
                """
            elif report_type == "quality":
                prompt = f"""
                Produce a data quality and profiling report for this dataset.
                
                Dataset Summary:
                {summary}
                
                Structure:
                ## Quality scorecard
                Short assessment (completeness, uniqueness risk, type consistency).
                ## Missing and sparse fields
                Bullets referencing columns with notable missing % from the summary.
                ## Outliers and distribution risks
                What to verify on numeric columns (based on min/max/mean in summary).
                ## Duplicates and integrity
                What duplicate or key issues might exist; how to validate.
                ## Remediation plan
                Numbered prioritized actions.
                
                {md_rules}
                Be specific to the columns listed in the summary.
                """
            else:
                prompt = f"""
                Generate a comprehensive data analysis report.
                
                Dataset Summary:
                {summary}
                
                Structure:
                ## Dataset overview
                ## Data quality assessment
                ## Key insights and patterns
                ## Statistical highlights
                Use a small Markdown table for 3–5 key numeric columns (min / max / mean) if applicable.
                ## Recommendations for deeper analysis
                ## Potential business applications
                
                {md_rules}
                Be detailed but readable.
                """
            
            response_text = self._call_groq(prompt, max_tokens=4096)
            return response_text.strip() if response_text else self._fallback_report(df)

        except Exception as e:
            if not self.last_error:
                self.last_error = self._format_api_error(e)
            print(f"AI Report failed: {self.last_error}")
            return self._fallback_report(df)
    
    def _prepare_dataset_summary(self, df: pd.DataFrame, dataset_name: str) -> str:
        """Prepare a summary of the dataset for AI analysis"""
        summary = f"""
Dataset Name: {dataset_name}
Shape: {df.shape[0]} rows, {df.shape[1]} columns

Columns:
"""
        
        for col in df.columns:
            dtype = str(df[col].dtype)
            unique_count = df[col].nunique()
            missing_count = df[col].isnull().sum()
            missing_pct = (missing_count / len(df)) * 100
            
            summary += f"- {col} ({dtype}): {unique_count} unique values, {missing_pct:.1f}% missing\n"
            
            # Show sample values for categorical columns
            if df[col].dtype == 'object' and unique_count <= 10:
                sample_values = df[col].dropna().unique()[:5].tolist()
                summary += f"  Sample values: {sample_values}\n"
        
        # Add some basic statistics for numeric columns
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            summary += f"\nNumeric Columns Summary:\n"
            for col in numeric_cols[:5]:  # Limit to first 5 numeric columns
                summary += f"- {col}: min={df[col].min():.2f}, max={df[col].max():.2f}, mean={df[col].mean():.2}\n"
        
        return summary
    
    def _parse_ai_response(self, response_text: str) -> Any:
        """Parse AI response and extract JSON robustly"""
        if not response_text:
            return {}
            
        # Clean any markdown code blocks
        cleaned_text = response_text.strip()
        if cleaned_text.startswith("```"):
            # Remove start fence
            first_newline = cleaned_text.find("\n")
            if first_newline != -1:
                cleaned_text = cleaned_text[first_newline:].strip()
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3].strip()

        # Remove thinking block if present
        if "<think>" in cleaned_text:
            end_think = cleaned_text.find("</think>")
            if end_think != -1:
                cleaned_text = cleaned_text[end_think + 8:].strip()

        # Find first [ and { to determine which is the outer container
        idx_brace = cleaned_text.find("{")
        idx_bracket = cleaned_text.find("[")

        try:
            if idx_bracket != -1 and (idx_brace == -1 or idx_bracket < idx_brace):
                # Looks like an array
                last_bracket = cleaned_text.rfind("]")
                if last_bracket != -1:
                    json_str = cleaned_text[idx_bracket:last_bracket + 1]
                    return json.loads(json_str)
            
            if idx_brace != -1:
                # Looks like an object
                last_brace = cleaned_text.rfind("}")
                if last_brace != -1:
                    json_str = cleaned_text[idx_brace:last_brace + 1]
                    return json.loads(json_str)
                    
            return json.loads(cleaned_text)
        except Exception as e:
            print(f"JSON parsing error: {e}. Text was: {cleaned_text[:500]}")
            return {"response": response_text, "parse_error": True}
    
    def _fallback_analysis(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Fallback analysis when AI is not available"""
        return {
            "overview": f"Dataset with {df.shape[0]} rows and {df.shape[1]} columns",
            "key_insights": [
                f"Dataset contains {len(df.select_dtypes(include=[np.number]).columns)} numeric columns",
                f"Dataset contains {len(df.select_dtypes(include=['object']).columns)} categorical columns",
                f"Overall data completeness: {((1 - df.isnull().sum().sum() / (df.shape[0] * df.shape[1])) * 100):.1f}%"
            ],
            "data_quality": "good" if df.isnull().sum().sum() < (df.shape[0] * df.shape[1] * 0.1) else "fair",
            "potential_uses": ["Data exploration", "Statistical analysis"],
            "recommendations": ["Handle missing values", "Explore correlations"],
            "interesting_patterns": ["Patterns may exist in the data"]
        }
    
    def _fallback_visualizations(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Fallback visualization suggestions"""
        suggestions = []
        
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        categorical_cols = df.select_dtypes(include=['object']).columns
        
        if len(categorical_cols) > 0:
            col = categorical_cols[0]
            suggestions.append({
                "chart_type": "bar" if df[col].nunique() > 6 else "pie",
                "title": f"Distribution of {col}",
                "description": "Show the frequency of different categories",
                "x_column": col,
                "insight": "Understand the composition of categories"
            })
        
        if len(numeric_cols) > 0:
            col = numeric_cols[0]
            suggestions.append({
                "chart_type": "histogram",
                "title": f"Distribution of {col}",
                "description": "Show the frequency distribution of values",
                "x_column": col,
                "insight": "Understand the data distribution"
            })
        
        if len(numeric_cols) >= 2:
            suggestions.append({
                "chart_type": "scatter",
                "title": f"{numeric_cols[0]} vs {numeric_cols[1]}",
                "description": "Explore relationship between variables",
                "x_column": numeric_cols[0],
                "y_column": numeric_cols[1],
                "insight": "Identify correlations and patterns"
            })
        
        return suggestions
    
    def _fallback_query(self, question: str) -> Dict[str, Any]:
        """Fallback query response"""
        return {
            "answer": "AI service is unavailable. Set NVIDIA_API_KEY in .env and restart the application, or check that the NVIDIA API endpoint is reachable.",
            "confidence": "low",
            "related_columns": [],
            "follow_up_questions": []
        }
    
    def _fallback_cleaning(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Fallback cleaning suggestions"""
        missing_pct = (df.isnull().sum().sum() / (df.shape[0] * df.shape[1])) * 100
        duplicate_count = df.duplicated().sum()
        
        issues = []
        if missing_pct > 5:
            issues.append({
                "issue_type": "missing_values",
                "severity": "medium" if missing_pct < 20 else "high",
                "description": f"{missing_pct:.1f}% of data is missing",
                "recommendation": "Consider imputation or removal of missing values"
            })
        
        if duplicate_count > 0:
            issues.append({
                "issue_type": "duplicates",
                "severity": "medium",
                "description": f"{duplicate_count} duplicate rows found",
                "recommendation": "Remove duplicate rows"
            })
        
        return {
            "overall_quality": "good" if len(issues) == 0 else "fair",
            "issues_found": issues,
            "cleaning_priority": ["missing_values"] if missing_pct > 5 else [],
            "estimated_effort": "low" if len(issues) == 0 else "medium"
        }
    
    def _fallback_report(self, df: pd.DataFrame) -> str:
        """Fallback report generation"""
        if not self.is_configured():
            note = "*Note: AI service is not configured. Set **NVIDIA_API_KEY** in `.env`, then restart the application.*"
        elif self.last_error:
            note = "*Note: an AI key is configured, but the external AI request failed. This is a local fallback report; see the warning above for details.*"
        else:
            note = "*Note: this is a local fallback report.*"

        return f"""
# Data Analysis Report

## Dataset Overview
- **Shape**: {df.shape[0]} rows × {df.shape[1]} columns
- **Memory Usage**: {df.memory_usage(deep=True).sum() / 1024:.1f} KB
- **Data Quality**: {((1 - df.isnull().sum().sum() / (df.shape[0] * df.shape[1])) * 100):.1f}% complete

## Column Summary
- **Numeric Columns**: {len(df.select_dtypes(include=[np.number]).columns)}
- **Categorical Columns**: {len(df.select_dtypes(include=['object']).columns)}
- **Missing Values**: {df.isnull().sum().sum()} cells

## Recommendations
1. Handle missing values appropriately
2. Explore data distributions
3. Check for correlations between variables
4. Consider data visualization for insights

{note}
        """
