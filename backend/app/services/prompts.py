# app/prompts/prompts.py

def dataset_summary_system_prompt() -> str:
    return (
        "You are a senior data analyst. Create a brief, high-signal summary of a dataset. "
        "Prioritize clarity and actionability. Avoid restating raw tables; synthesize insights."
    )

def dataset_summary_user_prompt(
    description: str,
    head10: list,
    tail10: list,
    rand10: list,
    numeric_desc: dict,
    object_desc: dict,
    meta: dict,
) -> str:
    """
    head10, tail10, rand10 should be lists of row dicts (orient='records')
    numeric_desc/object_desc are dicts from df.describe().to_dict()
    meta can include shape, columns, dtypes_sample counts, missing counts, etc.
    """
    return f"""
Dataset description (user-provided):
{description}

Meta:
{meta}

First 10 rows (sampled records):
{head10}

Last 10 rows (sampled records):
{tail10}

Random 10 rows (sampled records):
{rand10}

Descriptive statistics (numeric):
{numeric_desc}

Descriptive statistics (object/category):
{object_desc}

Instructions:
- Provide a concise executive summary (3–6 bullet points).
- Mention notable patterns, data quality issues (missing/outliers), and likely variable types.
- Suggest 2–4 relevant visualizations that could reveal key insights.
- If a potential target variable is evident from columns, suggest 2–3 candidate algorithms (only if clear).
- Keep it under 180 words.
"""

# def visualization_system_prompt() -> str:
#     return (
#         "You are a data visualization recommender. Given dataset metadata and sample stats, "
#         "return a JSON array of chart specifications only. No prose. Each item must follow "
#         "this exact schema (no comments, no code fences). Only output JSON array, nothing else.\n\n"
#         "Each object must contain these keys with the specified types:\n"
#         "- title: string\n"
#         "- type: one of [\"hist\", \"box\", \"bar\", \"count\", \"scatter\", \"line\", \"violin\", \"heatmap\"]\n"
#         "- x: string or null\n"
#         "- y: string or null\n"
#         "- hue: string or null\n"
#         "- bins: integer or null\n"
#         "- agg: string or null\n"
#         "- top_k: integer or null\n"
#         "- description: string\n\n"
#         "Example output (must match this JSON structure exactly):\n"
#         "[\n"
#         "  {\n"
#         "    \"title\": \"Histogram of Age\",\n"
#         "    \"type\": \"hist\",\n"
#         "    \"x\": \"age\",\n"
#         "    \"y\": null,\n"
#         "    \"hue\": null,\n"
#         "    \"bins\": 30,\n"
#         "    \"agg\": null,\n"
#         "    \"top_k\": null,\n"
#         "    \"description\": \"Distribution of age across observations\"\n"
#         "  }\n"
#         "]\n"
#         "If multiple charts, return an array with 3-8 items. Use null for unused fields. Do not include explanations, markdown, or comments."
#     )

# def visualization_user_prompt(meta: dict, describe_numeric: dict, describe_object: dict) -> str:
#     return f"""
# Dataset meta:
# {meta}

# Descriptive statistics (numeric):
# {describe_numeric}

# Descriptive statistics (object/category):
# {describe_object}

# Instructions:
# - Only return valid JSON as described in the schema.
# - Choose 3–8 diverse charts covering univariate distributions and key relationships.
# - Prefer hist/box for numeric, count/bar for categorical, scatter/line for relationships.
# - If many categories, apply top_k of 15 by frequency.
# - Use null for any unused fields.
# """

def viz_system_prompt_simple() -> str:
    return (
        "You are a business analyst who creates meaningful visualizations. Return ONLY chart specs, one JSON object per line.\n"
        "Do NOT return a JSON array, no prose, no markdown, and no code fences.\n"
        "Each line must be a single JSON object with this schema: {\n"
        '  "title": string,\n'
        '  "type": one of ["hist","box","bar","scatter","line","heatmap(always for corelation)"],\n'
        '  "x": string,\n'
        '  "y": string (avoid counts),\n'
        '  "hue": string or null\n'
        "}\n"
        "Return atleast 5-6 charts and a heatmap for corelation analysis\n"
    )
def viz_user_prompt_simple(meta: dict, numeric_desc: dict, object_desc: dict) -> str:
    return f"""
Dataset meta:
{meta}

Numeric describe:
{numeric_desc}

Categorical describe:
{object_desc}

Instructions:
- Return ONLY chart specs, one JSON object per line (not an array). Each line must follow the schema in the system prompt.
"""

