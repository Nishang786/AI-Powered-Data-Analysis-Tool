# Data Science Platform

An end-to-end data science web application combining FastAPI, Google Gemini AI, and Streamlit. Upload datasets, perform automated analysis, apply intelligent preprocessing, and generate AI-assisted visualizations—all through a simple web interface.

## ✨ Features

### 📁 Dataset Upload & Management
- Support for multiple formats: CSV, XLS/XLSX, JSON, TSV
- Validation and metadata capture
- Dataset versioning and tracking

### 🔍 Automated Analysis
- **Data sampling**: First 10, last 10, and random 10 rows
- **Statistical summaries**: Descriptive statistics for numeric and categorical columns
- **AI-powered insights**: Concise, actionable summaries using Google Gemini

### 🛠️ Intelligent Preprocessing
- Automatic column role inference (numeric, categorical, datetime, text, ID)
- Missing value profiling with suggested imputations
- Outlier detection using IQR and z-score methods
- Smart encoding and scaling recommendations
- Preview changes in-memory before applying
- Persist results with versioning or overwrite options

### 📊 AI-Assisted Visualization
- Minimal JSON specification for chart definitions
- AI-suggested chart types: histogram, box plot, bar chart, count plot, scatter, line, violin, pie, and heatmap
- Automatic correlation heatmap generation
- Server-side sampling for optimal performance on large datasets
- Base64-encoded images for seamless frontend display

## 🏗️ Tech Stack

- **Backend**: FastAPI, Pydantic, Uvicorn
- **Data Processing**: Pandas, NumPy, Scikit-learn
- **Visualization**: Seaborn, Matplotlib
- **AI**: Google Gemini (via google-genai)
- **Frontend**: Streamlit
- **Storage**: Local filesystem

## 📂 Repository Structure

```
backend/
  app/
    core/
      config.py
    controllers/
      upload_controller.py
      analysis_controller.py
      preprocessing_controller.py
      visualization_controller.py
      llm_controller.py
    models/
      dataset_model.py
      llm_model.py
    prompts/
      prompts.py
    services/
      dataset_service.py
      analysis_service.py
      preprocessing_service.py
      visualization_service.py
      llm_service.py
    storage/
      uploads/
      processed/
    main.py
  requirements.txt
  .env

streamlit_app.py
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Google Gemini API key ([Get one from AI Studio](https://aistudio.google.com/))

### Backend Setup

1. **Navigate to backend directory and create virtual environment:**
   ```bash
   cd backend
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # macOS/Linux
   source venv/bin/activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables:**
   
   Create `backend/.env`:
   ```
   GEMINI_API_KEY=your_gemini_api_key_here
   ```

4. **Run the API server:**
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

5. **Access API documentation:**
   - Swagger UI: http://localhost:8000/docs
   - OpenAPI: http://localhost:8000/openapi.json

### Streamlit Frontend

1. **Install Streamlit dependencies:**
   ```bash
   pip install streamlit requests pandas
   ```

2. **Run the Streamlit app:**
   ```bash
   streamlit run streamlit_app.py
   ```

3. **Configure API connection (optional):**
   
   Create `.streamlit/secrets.toml`:
   ```toml
   [general]
   API_BASE = "http://localhost:8000/api"
   ```
   
   Or set the `API_BASE` environment variable, or edit the default in `streamlit_app.py`.

## 🔄 Core Workflows

### 1. Upload Dataset
- Select a file from your local system
- Provide a description
- Server stores the file and metadata in `app/storage/uploads`

### 2. Analyze Data
- Automatically samples data (head, tail, random rows)
- Computes descriptive statistics using `describe()`
- Generates AI-powered summary with Gemini

### 3. Preprocess Data
- Profiles missing values, unique counts, data types, and outliers
- Suggests appropriate imputations (mean, median, most frequent, constant)
- Recommends encodings (one-hot) and scaling methods (standard, minmax)
- **Preview mode**: Apply transformations in-memory without saving
- **Persist mode**: Save results with two options:
  - `versioned`: Creates new file as `{id}_v{n}.ext`
  - `overwrite`: Replaces the original file

### 4. Generate Visualizations
- AI suggests optimal chart types based on data characteristics
- Charts use minimal JSON specification:
  ```json
  {
    "title": "Chart Title",
    "type": "hist|box|bar|count|scatter|line|violin|pie|heatmap",
    "x": "column_name",
    "y": "column_name",
    "hue": "category_column"
  }
  ```
- Correlation heatmap automatically included
- Renders as base64 PNG images
- Slider controls sample size for performance optimization

## 🔌 API Reference

### Upload
```http
POST /api/upload/dataset
Content-Type: multipart/form-data

file: <File>
description: <string>
```

### List Datasets
```http
GET /api/upload/datasets
```

### Analysis
```http
POST /api/analysis/{dataset_id}/summary
```

### Preprocessing Profile
```http
POST /api/preprocessing/{dataset_id}/profile
```

### Apply Preprocessing
```http
POST /api/preprocessing/{dataset_id}/apply?persist=false&persist_mode=versioned
Content-Type: application/json

{
  "custom_plan": {...}  // Optional
}
```

### Visualization Suggestions
```http
GET /api/visualization/{dataset_id}/suggest
```

### Render Charts
```http
POST /api/visualization/{dataset_id}/render?points=5000
Content-Type: application/json

[
  {
    "title": "Distribution",
    "type": "hist",
    "x": "age",
    "y": null,
    "hue": null
  }
]
```

## ⚙️ Environment Variables

### Required
- `GEMINI_API_KEY`: Your Google Gemini API key for AI features

### Optional (Streamlit)
- `API_BASE`: Backend API base URL (default: `http://localhost:8000/api`)

## 🎨 Key Design Decisions

### MVC Architecture
- **Controllers**: Handle API routes and request/response
- **Services**: Contain business logic for data processing, AI, and visualization
- **Models**: Define request/response schemas and internal data structures
- **Prompts**: Centralized prompt engineering for better maintainability

### Safe Preprocessing Pipeline
- Preview transformations before applying
- Explicit persistence modes to prevent accidental data loss
- Version control for processed datasets

### Minimal Visualization Schema
- Simple, validated chart specifications
- Easier to extend and maintain
- Reduced attack surface for rendering
- Consistent correlation heatmap for exploratory data analysis

## 📝 License

[Add your license here]

## 🤝 Contributing

[Add contribution guidelines here]

## 📧 Contact

[Add contact information here]
