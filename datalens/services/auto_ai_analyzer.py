import pandas as pd
import numpy as np
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from services.ai_assistant import DataLensAIAssistant
from groq import Groq
import os

@dataclass
class AutoAnalysisReport:
    """Structure for automatic AI analysis reports"""
    report_type: str  # 'financial', 'sales', 'inventory', 'general', 'hr', 'marketing'
    title: str
    summary: str
    key_metrics: List[Dict[str, Any]]
    insights: List[str]
    recommendations: List[str]
    formatted_report: str  # HTML formatted report
    raw_data_summary: Dict[str, Any]
    charts_suggestions: List[Dict[str, str]]

class AutoAIAnalyzer:
    """
    Automatic AI Analyzer - Analyzes uploaded files and generates 
    formatted balance sheets/reports based on data type
    """
    
    def __init__(self):
        self.ai_assistant = DataLensAIAssistant()
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
    
    def _call_groq(self, prompt: str, system_prompt: str = "You are a data analysis expert.") -> str:
        """Call NVIDIA NIM API using HTTPX"""
        if not self.is_configured:
            raise Exception("AI service not configured. Please set NVIDIA_API_KEY in .env.")
        if self._api_unavailable:
            raise Exception("AI service is temporarily unavailable.")
            
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
                "max_tokens": 1000
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
    
    def detect_data_type(self, df: pd.DataFrame, filename: str) -> str:
        """Detect the type of data based on columns and content"""
        columns = [col.lower() for col in df.columns]
        column_str = ' '.join(columns)
        
        # Financial data detection
        financial_keywords = ['montant', 'amount', 'prix', 'price', 'coût', 'cost', 'revenu', 'revenue', 
                             'dépense', 'expense', 'budget', 'profit', 'perte', 'loss', 'solde', 'balance',
                             'paiement', 'payment', 'facture', 'invoice', 'taxe', 'tax', 'total', 'subtotal']
        
        # Sales data detection
        sales_keywords = ['vente', 'sale', 'produit', 'product', 'quantité', 'quantity', 'client', 'customer',
                         'commande', 'order', 'achat', 'purchase', 'revenu', 'revenue', 'chiffre', 'turnover']
        
        # HR/Employee data detection
        hr_keywords = ['employé', 'employee', 'salaire', 'salary', 'prénom', 'first name', 'nom', 'last name',
                      'poste', 'position', 'département', 'department', 'embauche', 'hire', 'ancienneté', 'seniority']
        
        # Inventory/Stock data detection
        inventory_keywords = ['stock', 'inventory', 'produit', 'product', 'quantité', 'quantity', 
                             'entrepôt', 'warehouse', 'fournisseur', 'supplier', 'référence', 'sku']
        
        # Marketing data detection
        marketing_keywords = ['campagne', 'campaign', 'lead', 'prospect', 'conversion', 'clic', 'click',
                             'impression', 'ctr', 'cpc', 'cpa', 'roas', 'email', 'newsletter']
        
        # Count matches
        financial_score = sum(1 for kw in financial_keywords if kw in column_str)
        sales_score = sum(1 for kw in sales_keywords if kw in column_str)
        hr_score = sum(1 for kw in hr_keywords if kw in column_str)
        inventory_score = sum(1 for kw in inventory_keywords if kw in column_str)
        marketing_score = sum(1 for kw in marketing_keywords if kw in column_str)
        
        # Also check filename
        filename_lower = filename.lower()
        if any(word in filename_lower for word in ['finance', 'compta', 'accounting', 'budget', 'bilan']):
            financial_score += 3
        elif any(word in filename_lower for word in ['vente', 'sales', 'chiffre', 'revenue']):
            sales_score += 3
        elif any(word in filename_lower for word in ['employe', 'hr', 'payroll', 'salaire']):
            hr_score += 3
        elif any(word in filename_lower for word in ['stock', 'inventory', 'produit']):
            inventory_score += 3
        elif any(word in filename_lower for word in ['marketing', 'campaign', 'lead']):
            marketing_score += 3
        
        # Determine type based on highest score
        scores = {
            'financial': financial_score,
            'sales': sales_score,
            'hr': hr_score,
            'inventory': inventory_score,
            'marketing': marketing_score
        }
        
        max_type = max(scores, key=scores.get)
        max_score = scores[max_type]
        
        # If no clear match, return general
        if max_score == 0:
            return 'general'
        
        return max_type
    
    def analyze_and_generate_report(self, df: pd.DataFrame, filename: str, 
                                    dataset_id: int) -> AutoAnalysisReport:
        """Main method: detect data type and generate formatted report"""
        
        # Step 1: Detect data type
        data_type = self.detect_data_type(df, filename)
        
        # Step 2: Generate type-specific analysis
        if data_type == 'financial':
            return self._generate_financial_report(df, filename, dataset_id)
        elif data_type == 'sales':
            return self._generate_sales_report(df, filename, dataset_id)
        elif data_type == 'hr':
            return self._generate_hr_report(df, filename, dataset_id)
        elif data_type == 'inventory':
            return self._generate_inventory_report(df, filename, dataset_id)
        elif data_type == 'marketing':
            return self._generate_marketing_report(df, filename, dataset_id)
        else:
            return self._generate_general_report(df, filename, dataset_id)
    
    def _generate_financial_report(self, df: pd.DataFrame, filename: str, 
                                   dataset_id: int) -> AutoAnalysisReport:
        """Generate financial balance sheet report"""
        
        # Calculate financial metrics
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        
        total_amount = 0
        avg_amount = 0
        if numeric_cols:
            # Try to find amount/revenue column
            amount_col = None
            for col in numeric_cols:
                if any(keyword in col.lower() for keyword in ['montant', 'amount', 'total', 'revenu', 'revenue']):
                    amount_col = col
                    break
            
            if amount_col:
                total_amount = df[amount_col].sum()
                avg_amount = df[amount_col].mean()
        
        # Calculate row count and date range
        row_count = len(df)
        
        # Try to find date column
        date_col = None
        for col in df.columns:
            if 'date' in col.lower() or 'time' in col.lower():
                date_col = col
                break
        
        date_range = "Non spécifié"
        if date_col:
            try:
                df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
                min_date = df[date_col].min()
                max_date = df[date_col].max()
                if pd.notna(min_date) and pd.notna(max_date):
                    date_range = f"{min_date.strftime('%d/%m/%Y')} - {max_date.strftime('%d/%m/%Y')}"
            except:
                pass
        
        key_metrics = [
            {"label": "Total des transactions", "value": f"{row_count:,}", "icon": "📊"},
            {"label": "Montant total", "value": f"{total_amount:,.2f} €", "icon": "💰"},
            {"label": "Montant moyen", "value": f"{avg_amount:,.2f} €", "icon": "📈"},
            {"label": "Période", "value": date_range, "icon": "📅"}
        ]
        
        # AI-generated insights
        insights = []
        if self.is_configured:
            try:
                prompt = f"""
                Analyse ces données financières et donne 3 insights clés:
                - Total: {total_amount:.2f}€
                - Transactions: {row_count}
                - Moyenne: {avg_amount:.2f}€
                
                Réponds en JSON: {{"insights": ["insight 1", "insight 2", "insight 3"]}}
                """
                response_text = self._call_groq(prompt)
                data = self.ai_assistant._parse_response(response_text)
                insights = data.get('insights', [])
            except:
                insights = [
                    "Volume total de transactions analysé",
                    "Moyenne par transaction calculée", 
                    f"Période couverte: {date_range}"
                ]
        else:
            insights = [
                "Volume total de transactions analysé",
                "Moyenne par transaction calculée",
                f"Période couverte: {date_range}"
            ]
        
        # Generate formatted HTML report
        formatted_report = self._create_financial_html_report(df, filename, key_metrics, insights)
        
        return AutoAnalysisReport(
            report_type='financial',
            title=f"📊 Bilan Financier - {filename}",
            summary=f"Analyse financière de {row_count} transactions sur la période {date_range}",
            key_metrics=key_metrics,
            insights=insights,
            recommendations=[
                "Vérifier les anomalies dans les montants élevés",
                "Comparer avec la période précédente",
                "Identifier les tendances mensuelles"
            ],
            formatted_report=formatted_report,
            raw_data_summary={
                "rows": row_count,
                "columns": len(df.columns),
                "numeric_cols": len(numeric_cols),
                "total_amount": float(total_amount),
                "avg_amount": float(avg_amount)
            },
            charts_suggestions=[
                {"type": "line", "title": "Évolution temporelle", "x": date_col or "index"},
                {"type": "bar", "title": "Distribution des montants", "x": amount_col or numeric_cols[0] if numeric_cols else "index"},
                {"type": "pie", "title": "Répartition par catégorie", "x": df.select_dtypes(include=['object']).columns[0] if len(df.select_dtypes(include=['object']).columns) > 0 else "index"}
            ]
        )
    
    def _generate_sales_report(self, df: pd.DataFrame, filename: str, 
                              dataset_id: int) -> AutoAnalysisReport:
        """Generate sales analysis report"""
        
        row_count = len(df)
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        
        # Find sales amount column
        sales_total = 0
        sales_col = None
        for col in numeric_cols:
            if any(keyword in col.lower() for keyword in ['montant', 'amount', 'total', 'prix', 'price']):
                sales_col = col
                sales_total = df[col].sum()
                break
        
        # Find quantity column
        quantity_total = row_count
        qty_col = None
        for col in numeric_cols:
            if any(keyword in col.lower() for keyword in ['quantité', 'quantity', 'qty', 'nombre']):
                qty_col = col
                quantity_total = df[col].sum()
                break
        
        key_metrics = [
            {"label": "Total des ventes", "value": f"{row_count:,}", "icon": "🛍️"},
            {"label": "Chiffre d'affaires", "value": f"{sales_total:,.2f} €", "icon": "💶"},
            {"label": "Quantité totale", "value": f"{quantity_total:,.0f}", "icon": "📦"},
            {"label": "Panier moyen", "value": f"{sales_total/row_count if row_count > 0 else 0:,.2f} €", "icon": "🛒"}
        ]
        
        insights = [
            f"{row_count} ventes analysées",
            f"CA total: {sales_total:,.2f} €",
            "Performance commerciale évaluée"
        ]
        
        formatted_report = self._create_sales_html_report(df, filename, key_metrics, insights)
        
        return AutoAnalysisReport(
            report_type='sales',
            title=f"📈 Rapport des Ventes - {filename}",
            summary=f"Analyse de {row_count} ventes avec un CA de {sales_total:,.2f} €",
            key_metrics=key_metrics,
            insights=insights,
            recommendations=[
                "Identifier les produits les plus vendus",
                "Analyser la saisonnalité des ventes",
                "Segmenter la clientèle"
            ],
            formatted_report=formatted_report,
            raw_data_summary={
                "rows": row_count,
                "sales_total": float(sales_total),
                "quantity_total": float(quantity_total)
            },
            charts_suggestions=[
                {"type": "bar", "title": "Ventes par produit", "x": "product"},
                {"type": "line", "title": "Évolution des ventes", "x": "date"},
                {"type": "pie", "title": "Répartition par catégorie", "x": "category"}
            ]
        )
    
    def _generate_hr_report(self, df: pd.DataFrame, filename: str, 
                           dataset_id: int) -> AutoAnalysisReport:
        """Generate HR/Employee report"""
        
        employee_count = len(df)
        
        # Find salary column
        salary_col = None
        total_salary = 0
        avg_salary = 0
        
        for col in df.select_dtypes(include=[np.number]).columns:
            if any(keyword in col.lower() for keyword in ['salaire', 'salary', 'revenu', 'income']):
                salary_col = col
                total_salary = df[col].sum()
                avg_salary = df[col].mean()
                break
        
        # Find department column
        dept_col = None
        departments = []
        for col in df.select_dtypes(include=['object']).columns:
            if any(keyword in col.lower() for keyword in ['département', 'department', 'service', 'division']):
                dept_col = col
                departments = df[col].value_counts().to_dict()
                break
        
        key_metrics = [
            {"label": "Total employés", "value": f"{employee_count}", "icon": "👥"},
            {"label": "Masse salariale", "value": f"{total_salary:,.2f} €", "icon": "💵"},
            {"label": "Salaire moyen", "value": f"{avg_salary:,.2f} €", "icon": "💼"},
            {"label": "Départements", "value": f"{len(departments)}", "icon": "🏢"}
        ]
        
        insights = [f"Effectif total: {employee_count} personnes"]
        if departments:
            top_dept = max(departments.items(), key=lambda x: x[1])
            insights.append(f"Plus grand département: {top_dept[0]} ({top_dept[1]} personnes)")
        insights.append(f"Répartition analysée")
        
        formatted_report = self._create_hr_html_report(df, filename, key_metrics, insights, departments)
        
        return AutoAnalysisReport(
            report_type='hr',
            title=f"👥 Rapport RH - {filename}",
            summary=f"Analyse de {employee_count} employés sur {len(departments)} départements",
            key_metrics=key_metrics,
            insights=insights,
            recommendations=[
                "Analyser la répartition par département",
                "Évaluer la structure des salaires",
                "Identifier les besoins en recrutement"
            ],
            formatted_report=formatted_report,
            raw_data_summary={
                "employee_count": employee_count,
                "total_salary": float(total_salary),
                "avg_salary": float(avg_salary),
                "departments": len(departments)
            },
            charts_suggestions=[
                {"type": "pie", "title": "Répartition par département", "x": dept_col or "department"},
                {"type": "bar", "title": "Distribution des salaires", "x": salary_col or "salary"},
                {"type": "bar", "title": "Effectif par service", "x": dept_col or "department"}
            ]
        )
    
    def _generate_inventory_report(self, df: pd.DataFrame, filename: str, 
                                    dataset_id: int) -> AutoAnalysisReport:
        """Generate inventory/stock report"""
        
        product_count = len(df)
        
        # Find quantity and value columns
        qty_col = None
        total_qty = 0
        value_col = None
        total_value = 0
        
        for col in df.select_dtypes(include=[np.number]).columns:
            if any(keyword in col.lower() for keyword in ['quantité', 'quantity', 'qty', 'stock']):
                qty_col = col
                total_qty = df[col].sum()
            if any(keyword in col.lower() for keyword in ['valeur', 'value', 'prix', 'price', 'coût', 'cost']):
                value_col = col
                total_value = df[col].sum()
        
        # Low stock detection
        low_stock_count = 0
        if qty_col:
            low_threshold = df[qty_col].quantile(0.25) if len(df) > 0 else 0
            low_stock_count = len(df[df[qty_col] <= low_threshold])
        
        key_metrics = [
            {"label": "Total produits", "value": f"{product_count}", "icon": "📦"},
            {"label": "Quantité totale", "value": f"{total_qty:,.0f}", "icon": "📊"},
            {"label": "Valeur stock", "value": f"{total_value:,.2f} €", "icon": "💰"},
            {"label": "Stock faible", "value": f"{low_stock_count}", "icon": "⚠️"}
        ]
        
        insights = [
            f"{product_count} produits en stock",
            f"Valeur totale: {total_value:,.2f} €",
            f"{low_stock_count} produits nécessitent réapprovisionnement"
        ]
        
        formatted_report = self._create_inventory_html_report(df, filename, key_metrics, insights)
        
        return AutoAnalysisReport(
            report_type='inventory',
            title=f"📦 Rapport d'Inventaire - {filename}",
            summary=f"Analyse de {product_count} produits avec une valeur stock de {total_value:,.2f} €",
            key_metrics=key_metrics,
            insights=insights,
            recommendations=[
                "Réapprovisionner les stocks faibles",
                "Analyser la rotation des produits",
                "Optimiser les niveaux de stock"
            ],
            formatted_report=formatted_report,
            raw_data_summary={
                "product_count": product_count,
                "total_quantity": float(total_qty),
                "total_value": float(total_value),
                "low_stock": low_stock_count
            },
            charts_suggestions=[
                {"type": "bar", "title": "Quantité par produit", "x": qty_col or "quantity"},
                {"type": "pie", "title": "Valeur par catégorie", "x": "category"},
                {"type": "scatter", "title": "Stock vs Valeur", "x": qty_col or "qty", "y": value_col or "value"}
            ]
        )
    
    def _generate_marketing_report(self, df: pd.DataFrame, filename: str, 
                                  dataset_id: int) -> AutoAnalysisReport:
        """Generate marketing/campaign report"""
        
        campaign_count = len(df)
        
        # Marketing metrics
        impressions = 0
        clicks = 0
        conversions = 0
        
        for col in df.select_dtypes(include=[np.number]).columns:
            if 'impression' in col.lower():
                impressions = df[col].sum()
            if 'click' in col.lower():
                clicks = df[col].sum()
            if 'conversion' in col.lower():
                conversions = df[col].sum()
        
        ctr = (clicks / impressions * 100) if impressions > 0 else 0
        conversion_rate = (conversions / clicks * 100) if clicks > 0 else 0
        
        key_metrics = [
            {"label": "Campagnes", "value": f"{campaign_count}", "icon": "📢"},
            {"label": "Impressions", "value": f"{impressions:,.0f}", "icon": "👁️"},
            {"label": "CTR", "value": f"{ctr:.2f}%", "icon": "🖱️"},
            {"label": "Conversions", "value": f"{conversions:,.0f}", "icon": "✅"}
        ]
        
        insights = [
            f"{campaign_count} campagnes analysées",
            f"CTR moyen: {ctr:.2f}%",
            f"Taux de conversion: {conversion_rate:.2f}%"
        ]
        
        formatted_report = self._create_marketing_html_report(df, filename, key_metrics, insights)
        
        return AutoAnalysisReport(
            report_type='marketing',
            title=f"📢 Rapport Marketing - {filename}",
            summary=f"Analyse de {campaign_count} campagnes avec {impressions:,.0f} impressions",
            key_metrics=key_metrics,
            insights=insights,
            recommendations=[
                "Optimiser les campagnes au plus fort CTR",
                "Analyser les canaux les plus performants",
                "Améliorer le taux de conversion"
            ],
            formatted_report=formatted_report,
            raw_data_summary={
                "campaign_count": campaign_count,
                "impressions": float(impressions),
                "clicks": float(clicks),
                "conversions": float(conversions),
                "ctr": float(ctr),
                "conversion_rate": float(conversion_rate)
            },
            charts_suggestions=[
                {"type": "bar", "title": "Performance des campagnes", "x": "campaign"},
                {"type": "line", "title": "Évolution CTR", "x": "date"},
                {"type": "pie", "title": "Répartition par canal", "x": "channel"}
            ]
        )
    
    def _generate_general_report(self, df: pd.DataFrame, filename: str, 
                                dataset_id: int) -> AutoAnalysisReport:
        """Generate general data analysis report"""
        
        row_count = len(df)
        col_count = len(df.columns)
        numeric_count = len(df.select_dtypes(include=[np.number]).columns)
        categorical_count = len(df.select_dtypes(include=['object']).columns)
        
        # Completeness
        total_cells = row_count * col_count
        missing_cells = df.isnull().sum().sum()
        completeness = ((total_cells - missing_cells) / total_cells * 100) if total_cells > 0 else 0
        
        key_metrics = [
            {"label": "Lignes", "value": f"{row_count:,}", "icon": "📊"},
            {"label": "Colonnes", "value": f"{col_count}", "icon": "📋"},
            {"label": "Complétude", "value": f"{completeness:.1f}%", "icon": "✅"},
            {"label": "Types", "value": f"{numeric_count}N / {categorical_count}C", "icon": "🔢"}
        ]
        
        insights = [
            f"Dataset de {row_count} lignes et {col_count} colonnes",
            f"Qualité des données: {completeness:.1f}%",
            f"{numeric_count} colonnes numériques, {categorical_count} catégorielles"
        ]
        
        formatted_report = self._create_general_html_report(df, filename, key_metrics, insights)
        
        return AutoAnalysisReport(
            report_type='general',
            title=f"📊 Analyse de Données - {filename}",
            summary=f"Analyse générale de {row_count} enregistrements avec {completeness:.1f}% de données complètes",
            key_metrics=key_metrics,
            insights=insights,
            recommendations=[
                "Explorer les distributions des variables",
                "Identifier les corrélations potentielles",
                "Visualiser les données pour mieux comprendre"
            ],
            formatted_report=formatted_report,
            raw_data_summary={
                "rows": row_count,
                "columns": col_count,
                "numeric": numeric_count,
                "categorical": categorical_count,
                "completeness": float(completeness)
            },
            charts_suggestions=[
                {"type": "bar", "title": "Distribution principale", "x": df.columns[0]},
                {"type": "histogram", "title": "Histogramme", "x": df.select_dtypes(include=[np.number]).columns[0] if numeric_count > 0 else df.columns[0]},
                {"type": "pie", "title": "Répartition", "x": df.select_dtypes(include=['object']).columns[0] if categorical_count > 0 else df.columns[0]}
            ]
        )
    
    # HTML Report Generators
    def _create_financial_html_report(self, df, filename, metrics, insights):
        html = f"""
        <div class="report-container financial-report">
            <div class="report-header">
                <h1>📊 Bilan Financier</h1>
                <p class="report-filename">{filename}</p>
            </div>
            
            <div class="metrics-grid">
        """
        for metric in metrics:
            html += f"""
                <div class="metric-card">
                    <div class="metric-icon">{metric['icon']}</div>
                    <div class="metric-label">{metric['label']}</div>
                    <div class="metric-value">{metric['value']}</div>
                </div>
            """
        
        html += "</div>"
        
        html += """
            <div class="report-section">
                <h2>💡 Insights Clés</h2>
                <ul class="insights-list">
        """
        for insight in insights:
            html += f"<li>{insight}</li>"
        
        html += """
                </ul>
            </div>
            
            <div class="report-section">
                <h2>📈 Recommandations</h2>
                <ul class="recommendations-list">
                    <li>Vérifier les anomalies dans les montants élevés</li>
                    <li>Comparer avec la période précédente</li>
                    <li>Identifier les tendances mensuelles</li>
                </ul>
            </div>
        </div>
        """
        return html
    
    def _create_sales_html_report(self, df, filename, metrics, insights):
        html = f"""
        <div class="report-container sales-report">
            <div class="report-header">
                <h1>📈 Rapport des Ventes</h1>
                <p class="report-filename">{filename}</p>
            </div>
            
            <div class="metrics-grid">
        """
        for metric in metrics:
            html += f"""
                <div class="metric-card">
                    <div class="metric-icon">{metric['icon']}</div>
                    <div class="metric-label">{metric['label']}</div>
                    <div class="metric-value">{metric['value']}</div>
                </div>
            """
        
        html += "</div></div>"
        return html
    
    def _create_hr_html_report(self, df, filename, metrics, insights, departments):
        html = f"""
        <div class="report-container hr-report">
            <div class="report-header">
                <h1>👥 Rapport RH</h1>
                <p class="report-filename">{filename}</p>
            </div>
            
            <div class="metrics-grid">
        """
        for metric in metrics:
            html += f"""
                <div class="metric-card">
                    <div class="metric-icon">{metric['icon']}</div>
                    <div class="metric-label">{metric['label']}</div>
                    <div class="metric-value">{metric['value']}</div>
                </div>
            """
        
        html += "</div>"
        
        if departments:
            html += """
                <div class="report-section">
                    <h2>🏢 Répartition par Département</h2>
                    <table class="dept-table">
                        <tr><th>Département</th><th>Effectif</th></tr>
            """
            for dept, count in sorted(departments.items(), key=lambda x: x[1], reverse=True):
                html += f"<tr><td>{dept}</td><td>{count}</td></tr>"
            html += "</table></div>"
        
        html += "</div>"
        return html
    
    def _create_inventory_html_report(self, df, filename, metrics, insights):
        html = f"""
        <div class="report-container inventory-report">
            <div class="report-header">
                <h1>📦 Rapport d'Inventaire</h1>
                <p class="report-filename">{filename}</p>
            </div>
            
            <div class="metrics-grid">
        """
        for metric in metrics:
            html += f"""
                <div class="metric-card">
                    <div class="metric-icon">{metric['icon']}</div>
                    <div class="metric-label">{metric['label']}</div>
                    <div class="metric-value">{metric['value']}</div>
                </div>
            """
        
        html += "</div></div>"
        return html
    
    def _create_marketing_html_report(self, df, filename, metrics, insights):
        html = f"""
        <div class="report-container marketing-report">
            <div class="report-header">
                <h1>📢 Rapport Marketing</h1>
                <p class="report-filename">{filename}</p>
            </div>
            
            <div class="metrics-grid">
        """
        for metric in metrics:
            html += f"""
                <div class="metric-card">
                    <div class="metric-icon">{metric['icon']}</div>
                    <div class="metric-label">{metric['label']}</div>
                    <div class="metric-value">{metric['value']}</div>
                </div>
            """
        
        html += "</div></div>"
        return html
    
    def _create_general_html_report(self, df, filename, metrics, insights):
        html = f"""
        <div class="report-container general-report">
            <div class="report-header">
                <h1>📊 Analyse de Données</h1>
                <p class="report-filename">{filename}</p>
            </div>
            
            <div class="metrics-grid">
        """
        for metric in metrics:
            html += f"""
                <div class="metric-card">
                    <div class="metric-icon">{metric['icon']}</div>
                    <div class="metric-label">{metric['label']}</div>
                    <div class="metric-value">{metric['value']}</div>
                </div>
            """
        
        html += "</div></div>"
        return html
