from groq import Groq
import pandas as pd
import json
from typing import Dict, List, Any, Optional
import os
from dataclasses import dataclass

@dataclass
class AIAssistantResponse:
    """Structure for AI assistant responses"""
    message: str
    action_suggestions: List[Dict[str, str]]
    insights: List[str]
    confidence: str

class DataLensAIAssistant:
    """
    AI Assistant for DataLens platform
    Provides contextual help, data analysis guidance, and smart recommendations
    """
    
    def __init__(self):
        """Initialize the AI Assistant with NVIDIA NIM (DeepSeek-v4-flash) or fallback"""
        self.api_key = os.getenv('NVIDIA_API_KEY', '') or os.getenv('GEMINI_API_KEY', '') or os.getenv('GROQ_API_KEY', '')
        self.is_configured = bool(self.api_key and not self.api_key.startswith('YOUR_'))
        self.model = os.getenv('NVIDIA_MODEL', 'meta/llama-3.1-8b-instruct')
        self.fallback_models = self._unique_models([
            self.model,
            'nvidia/llama-3.1-nemotron-nano-8b-v1',
            'deepseek-ai/deepseek-v4-flash',
        ])
        self.base_url = "https://integrate.api.nvidia.com/v1/chat/completions"
        self._api_unavailable = False
    
    def _call_groq(self, prompt: str, system_prompt: str = "You are a helpful AI assistant for data analysis.") -> str:
        """Call NVIDIA NIM API using HTTPX"""
        if not self.is_configured:
            raise Exception("AI Assistant not configured. Please set NVIDIA_API_KEY in .env.")
        if self._api_unavailable:
            raise Exception("AI Assistant is temporarily unavailable.")
            
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
                "max_tokens": 2048
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
                errors.append(f"{model}: {e}")
                continue

        self._api_unavailable = True
        error_message = "NVIDIA API request failed for all models. " + " | ".join(errors)
        print(f"NVIDIA NIM API Error: {error_message}")
        raise Exception(error_message)

    def _unique_models(self, models: List[str]) -> List[str]:
        unique = []
        for model in models:
            if model and model not in unique:
                unique.append(model)
        return unique
    
    def get_welcome_message(self, user_name: str = "User") -> AIAssistantResponse:
        """Generate personalized welcome message"""
        if not self.is_configured:
            return AIAssistantResponse(
                message=f"👋 Bonjour {user_name}! Bienvenue sur DataLens. Je suis votre assistant IA.\n\n"
                        "Pour activer mes fonctionnalités avancées, configurez NVIDIA_API_KEY dans votre fichier .env puis redémarrez l’application.",
                action_suggestions=[
                    {"label": "📊 Charger un dataset", "action": "upload", "url": "/upload"},
                    {"label": "📖 Voir le guide", "action": "guide", "url": "/guide"},
                    {"label": "⚙️ Configuration", "action": "settings", "url": "/settings"}
                ],
                insights=["DataLens vous permet d'analyser vos données facilement"],
                confidence="high"
            )
        
        return AIAssistantResponse(
            message=f"👋 Bonjour {user_name}! Je suis votre assistant IA DataLens.\n\n"
                    "Je peux vous aider à:\n"
                    "• 📊 Analyser et comprendre vos données\n"
                    "• 📈 Créer des visualisations pertinentes\n"
                    "• 🔍 Découvrir des insights cachés\n"
                    "• 🧹 Nettoyer et améliorer vos données\n\n"
                    "Comment puis-je vous aider aujourd'hui ?",
            action_suggestions=[
                {"label": "📁 Charger des données", "action": "upload", "url": "/upload"},
                {"label": "📊 Voir mes datasets", "action": "dashboard", "url": "/dashboard"},
                {"label": "❓ Poser une question", "action": "ask", "url": "#ask-ai"}
            ],
            insights=["Je suis prêt à analyser vos données dès que vous les chargez"],
            confidence="high"
        )
    
    def analyze_dataset_context(self, df: pd.DataFrame, dataset_name: str, 
                               current_view: str = "overview") -> AIAssistantResponse:
        """Provide contextual analysis based on current dataset view"""
        if not self.is_configured:
            return self._fallback_analysis(df, current_view)
        
        try:
            # Prepare dataset context
            context = self._prepare_dataset_context(df, dataset_name)
            
            prompt = f"""
            En tant qu'assistant IA pour DataLens, analyse ce dataset et donne des conseils contextuels.
            
            Contexte actuel: {current_view}
            
            Dataset:
            {context}
            
            Fournis une réponse en JSON avec:
            {{
                "message": "Message personnalisé et utile en français",
                "action_suggestions": [
                    {{"label": "Description du bouton", "action": "type_action", "url": "/chemin"}}
                ],
                "insights": ["Insight 1", "Insight 2"],
                "next_steps": ["Étape suggérée 1", "Étape suggérée 2"]
            }}
            
            Adapte les suggestions selon le contexte actuel ({current_view}).
            Sois chaleureux et encourageant.
            """
            
            response_text = self._call_groq(prompt)
            data = self._parse_response(response_text)
            
            return AIAssistantResponse(
                message=data.get('message', 'Analyse disponible'),
                action_suggestions=data.get('action_suggestions', []),
                insights=data.get('insights', []),
                confidence="high"
            )
            
        except Exception as e:
            print(f"AI Assistant error: {e}")
            return self._fallback_analysis(df, current_view)
    
    def suggest_next_actions(self, df: pd.DataFrame, 
                            current_action: str = None) -> AIAssistantResponse:
        """Suggest intelligent next steps based on current state"""
        if not self.is_configured:
            return AIAssistantResponse(
                message="💡 Actions suggérées basées sur l'analyse de vos données",
                action_suggestions=[
                    {"label": "📊 Créer un graphique", "action": "visualize", "url": "#"},
                    {"label": "🔍 Analyse détaillée", "action": "analyze", "url": "#"},
                    {"label": "📄 Générer un rapport", "action": "report", "url": "#"}
                ],
                insights=["Analyse des tendances disponible"],
                confidence="medium"
            )
        
        try:
            numeric_cols = len(df.select_dtypes(include=['number']).columns)
            categorical_cols = len(df.select_dtypes(include=['object']).columns)
            missing_pct = (df.isnull().sum().sum() / (df.shape[0] * df.shape[1])) * 100
            
            prompt = f"""
            Suggère les prochaines actions intelligentes pour cet utilisateur DataLens.
            
            État actuel:
            - Action en cours: {current_action or 'Aucune'}
            - Colonnes numériques: {numeric_cols}
            - Colonnes catégorielles: {categorical_cols}
            - Données manquantes: {missing_pct:.1f}%
            - Taille: {df.shape[0]} lignes × {df.shape[1]} colonnes
            
            Réponds en JSON:
            {{
                "message": "Message contextuel en français",
                "action_suggestions": [{{"label": "...", "action": "...", "priority": "high/medium/low"}}],
                "insights": ["Insight contextuel"],
                "tip": "Conseil pro"
            }}
            """
            
            response_text = self._call_groq(prompt)
            data = self._parse_response(response_text)
            
            return AIAssistantResponse(
                message=data.get('message', 'Voici mes suggestions'),
                action_suggestions=data.get('action_suggestions', []),
                insights=data.get('insights', []),
                confidence="high"
            )
            
        except Exception as e:
            return self._fallback_suggestions(df, current_action)
    
    def explain_chart_recommendation(self, chart_type: str, x_col: str, 
                                   y_col: str = None, purpose: str = None) -> AIAssistantResponse:
        """Explain why a specific chart is recommended"""
        if not self.is_configured:
            return AIAssistantResponse(
                message=f"Ce graphique {chart_type} vous aidera à visualiser la distribution de {x_col}.",
                action_suggestions=[
                    {"label": "✅ Créer ce graphique", "action": "create_chart"},
                    {"label": "📊 Voir d'autres options", "action": "more_charts"}
                ],
                insights=[f"Le graphique {chart_type} est adapté pour {x_col}"],
                confidence="medium"
            )
        
        try:
            prompt = f"""
            Explique pourquoi ce graphique est recommandé en français.
            
            Type: {chart_type}
            Colonne X: {x_col}
            Colonne Y: {y_col or 'Non applicable'}
            Objectif: {purpose or 'Visualisation des données'}
            
            Réponds en JSON:
            {{
                "explanation": "Pourquoi ce graphique est pertinent",
                "what_it_shows": "Ce que révèle ce graphique",
                "when_to_use": "Quand utiliser ce type de graphique",
                "interpretation_tips": ["Conseil 1", "Conseil 2"],
                "alternatives": ["Alternative 1", "Alternative 2"]
            }}
            """
            
            response_text = self._call_groq(prompt)
            data = self._parse_response(response_text)
            
            explanation = data.get('explanation', '')
            what_it_shows = data.get('what_it_shows', '')
            
            message = f"📊 **{chart_type.capitalize()}**\n\n"
            message += f"{explanation}\n\n"
            message += f"**Ce que cela montre:**\n{what_it_shows}\n\n"
            
            if 'interpretation_tips' in data:
                message += "**💡 Conseils d'interprétation:**\n"
                for tip in data['interpretation_tips']:
                    message += f"• {tip}\n"
            
            return AIAssistantResponse(
                message=message,
                action_suggestions=[
                    {"label": "✅ Créer ce graphique", "action": "create_chart"},
                    {"label": "📊 Voir les alternatives", "action": "alternatives"},
                    {"label": "❓ Poser une question", "action": "ask"}
                ],
                insights=data.get('interpretation_tips', []),
                confidence="high"
            )
            
        except Exception as e:
            return AIAssistantResponse(
                message=f"Ce graphique {chart_type} est recommandé pour visualiser {x_col}.",
                action_suggestions=[
                    {"label": "✅ Créer", "action": "create_chart"},
                    {"label": "❓ En savoir plus", "action": "help"}
                ],
                insights=[f"Graphique {chart_type} adapté pour {x_col}"],
                confidence="medium"
            )
    
    def help_with_data_cleaning(self, df: pd.DataFrame, 
                                specific_issue: str = None) -> AIAssistantResponse:
        """Provide AI-powered data cleaning guidance"""
        if not self.is_configured:
            return AIAssistantResponse(
                message="🧹 Voici comment nettoyer vos données efficacement",
                action_suggestions=[
                    {"label": "🔍 Détecter les problèmes", "action": "detect_issues"},
                    {"label": "✨ Nettoyer automatiquement", "action": "auto_clean"},
                    {"label": "📖 Guide de nettoyage", "action": "guide"}
                ],
                insights=["Le nettoyage améliore la qualité d'analyse de 40%"],
                confidence="medium"
            )
        
        try:
            missing_data = df.isnull().sum()
            total_missing = missing_data.sum()
            
            prompt = f"""
            Donne des conseils de nettoyage de données personnalisés.
            
            Problème spécifique: {specific_issue or 'Général'}
            Données manquantes totales: {total_missing}
            Pourcentage manquant: {(total_missing / (df.shape[0] * df.shape[1]) * 100):.1f}%
            Colonnes avec données manquantes: {len(missing_data[missing_data > 0])}
            
            Réponds en JSON:
            {{
                "assessment": "Évaluation de la qualité des données",
                "priorities": ["Priorité 1", "Priorité 2"],
                "techniques": [
                    {{"technique": "Nom de la technique", "applies_to": "colonnes", "benefit": "Bénéfice"}}
                ],
                "step_by_step": ["Étape 1", "Étape 2", "Étape 3"],
                "warnings": ["Attention 1"]
            }}
            """
            
            response_text = self._call_groq(prompt)
            data = self._parse_response(response_text)
            
            message = f"🧹 **Évaluation du nettoyage**\n\n"
            message += f"{data.get('assessment', '')}\n\n"
            
            if 'priorities' in data:
                message += "**🎯 Priorités:**\n"
                for i, priority in enumerate(data['priorities'], 1):
                    message += f"{i}. {priority}\n"
                message += "\n"
            
            if 'step_by_step' in data:
                message += "**📋 Étapes recommandées:**\n"
                for i, step in enumerate(data['step_by_step'], 1):
                    message += f"{i}. {step}\n"
            
            return AIAssistantResponse(
                message=message,
                action_suggestions=[
                    {"label": "🔍 Analyser les problèmes", "action": "analyze"},
                    {"label": "✨ Appliquer les corrections", "action": "apply"},
                    {"label": "📖 Guide détaillé", "action": "guide"}
                ],
                insights=data.get('priorities', []),
                confidence="high"
            )
            
        except Exception as e:
            return AIAssistantResponse(
                message="Je peux vous aider à nettoyer vos données. Commençons par identifier les problèmes.",
                action_suggestions=[
                    {"label": "🔍 Analyser", "action": "analyze"},
                    {"label": "✨ Auto-nettoyage", "action": "auto_clean"}
                ],
                insights=["Le nettoyage des données est essentiel"],
                confidence="medium"
            )
    
    def answer_general_question(self, question: str, 
                                context: Dict = None) -> AIAssistantResponse:
        """Answer general questions about DataLens and data analysis"""
        if not self.is_configured:
            return AIAssistantResponse(
                message="Je suis là pour vous aider ! Posez-moi des questions sur DataLens ou l'analyse de données.",
                action_suggestions=[
                    {"label": "📖 Guide d'utilisation", "action": "guide", "url": "/guide"},
                    {"label": "❓ FAQ", "action": "faq", "url": "/faq"}
                ],
                insights=["Le support est disponible 24/7"],
                confidence="medium"
            )
        
        try:
            context_str = ""
            if context:
                context_str = f"\nContexte: {json.dumps(context, indent=2)}"
            
            prompt = f"""
            Réponds à cette question en tant qu'assistant IA DataLens.
            
            Question: {question}
            {context_str}
            
            Sois utile, précis et chaleureux. Réponds en français.
            Si la question concerne DataLens, donne des instructions spécifiques.
            Si c'est sur l'analyse de données, donne des conseils pratiques.
            
            Réponds en JSON:
            {{
                "answer": "Réponse complète et utile",
                "related_topics": ["Sujet lié 1", "Sujet lié 2"],
                "suggested_actions": [{{"label": "Action", "url": "/chemin"}}],
                "resources": ["Ressource 1", "Ressource 2"]
            }}
            """
            
            response_text = self._call_groq(prompt)
            data = self._parse_response(response_text)
            
            return AIAssistantResponse(
                message=data.get('answer', 'Je suis là pour vous aider'),
                action_suggestions=data.get('suggested_actions', []),
                insights=data.get('related_topics', []),
                confidence="high"
            )
            
        except Exception as e:
            return AIAssistantResponse(
                message=f"Je comprends votre question sur '{question}'. Laissez-moi vous aider avec cela.",
                action_suggestions=[
                    {"label": "📖 Documentation", "action": "docs"},
                    {"label": "💬 Support", "action": "support"}
                ],
                insights=["Support personnalisé disponible"],
                confidence="medium"
            )
    
    def _prepare_dataset_context(self, df: pd.DataFrame, dataset_name: str) -> str:
        """Prepare dataset summary for AI context"""
        lines = [
            f"Nom: {dataset_name}",
            f"Dimensions: {df.shape[0]} lignes × {df.shape[1]} colonnes",
            f"Colonnes numériques: {len(df.select_dtypes(include=['number']).columns)}",
            f"Colonnes catégorielles: {len(df.select_dtypes(include=['object']).columns)}",
            f"Données manquantes: {df.isnull().sum().sum()} cellules",
        ]
        return "\n".join(lines)
    
    def _parse_response(self, text: str) -> Dict:
        """Parse AI response and extract JSON robustly"""
        if not text:
            return {}
            
        # Clean any markdown code blocks
        cleaned_text = text.strip()
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
            print(f"JSON parsing error in AI Assistant: {e}. Text was: {cleaned_text[:500]}")
            return {}
    
    def _fallback_analysis(self, df: pd.DataFrame, view: str) -> AIAssistantResponse:
        """Fallback when AI is not configured"""
        numeric_count = len(df.select_dtypes(include=['number']).columns)
        categorical_count = len(df.select_dtypes(include=['object']).columns)
        
        message = f"📊 Vue {view} du dataset\n\n"
        message += f"**Statistiques:**\n"
        message += f"• {df.shape[0]} lignes, {df.shape[1]} colonnes\n"
        message += f"• {numeric_count} colonnes numériques\n"
        message += f"• {categorical_count} colonnes catégorielles\n"
        message += f"• Complétude: {((1 - df.isnull().sum().sum() / (df.shape[0] * df.shape[1])) * 100):.1f}%\n\n"
        
        return AIAssistantResponse(
            message=message,
            action_suggestions=[
                {"label": "📈 Visualiser", "action": "visualize", "url": "#visualize"},
                {"label": "📊 Statistiques", "action": "stats", "url": "#stats"},
                {"label": "🔍 Explorer", "action": "explore", "url": "#explore"}
            ],
            insights=["Dataset chargé avec succès"],
            confidence="medium"
        )
    
    def _fallback_suggestions(self, df: pd.DataFrame, 
                             current_action: str) -> AIAssistantResponse:
        """Fallback suggestions"""
        return AIAssistantResponse(
            message="Voici les actions recommandées pour votre dataset",
            action_suggestions=[
                {"label": "📊 Créer des graphiques", "action": "visualize"},
                {"label": "🔍 Analyser les données", "action": "analyze"},
                {"label": "📄 Générer un rapport", "action": "report"},
                {"label": "🧹 Nettoyer les données", "action": "clean"}
            ],
            insights=["Analyse recommandée disponible"],
            confidence="medium"
        )
