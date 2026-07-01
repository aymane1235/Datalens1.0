# DataLens 1.0 📊🤖

DataLens is an intelligent data analysis platform that transforms raw datasets (CSV/Excel) into interactive visual dashboards and automated, AI-driven business insights. Built with a clean architectural pattern, the platform handles everything from secure data ingestion to advanced reporting.

## 🚀 Features

- **Smart Data Ingestion:** Seamless parsing and automated validation of tabular files using Pandas.
- **Dynamic Visualization:** Interactive, real-time charts and visual analysis powered by Chart.js.
- **AI-Driven Analytics:** Deep data trends extraction and textual insights orchestrated via NVIDIA NIM / Groq APIs.
- **Automated Reporting:** Generates and compiles visual charts alongside AI summaries into a downloadable PDF report.

## 🛠️ Tech Stack

- **Backend:** Python (Flask/Django), Pandas, NumPy
- **Frontend:** HTML5, CSS3, JavaScript, Chart.js
- **AI Integration:** NVIDIA NIM / Groq Cloud API
- **Version Control:** Git & GitHub

## 📁 Project Structure

```text
├── models/         # Data layer and schema management
├── routes/         # HTTP request routing and endpoints
├── services/       # Core business logic (AI, PDF generation, Parsing)
├── static/         # CSS style sheets and client-side JavaScript
├── templates/      # UI HTML structure pages
├── app.py          # Main application entry point
├── config.py       # API keys and system configurations
└── .gitignore      # Ignored files and directories
