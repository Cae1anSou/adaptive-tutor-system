"""
Utility script to restructure the raw “Untitled form.csv” questionnaire export
into analysis-friendly tables:

1. participants.csv – background metadata and general suggestions
2. module_feedback_long.csv – all module free-text answers in tidy format
3. scale_responses_long.csv – SUS, NASA-TLX, and self-efficacy items in tidy format
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
RAW_PATH = BASE_DIR / "Untitled form.csv"
OUTPUT_DIR = BASE_DIR / "cleaned"


@dataclass(frozen=True)
class ScaleItem:
    scale: str
    code: str
    column: str


# Column mappings for demographics/basic info
DEMOGRAPHIC_COLUMNS: Dict[str, str] = {
    "Please enter your experiment ID. ": "participant_id",
    "Please enter your gender:": "gender",
    "Please enter your major:": "major",
    "How many years has it been since you first started learning programming? ": "years_programming",
    "What is your current level of education?  ": "education_level",
    "Have you ever studied front-end development or taken related courses?": "studied_frontend",
    "If you have any further suggestions, please write them below.": "general_suggestion",
}

# Repeated module question triplets
MODULE_QUESTION_MAP: Dict[str, Dict[str, str]] = {
    "interest_generation": {
        "advantage": "Is the Interest-based Generation Module helpful to you? What advantages do you think it has?",
        "difficulty": "Did you have difficulties when using the Interest-based Generation Module? What disadvantages do you think it has?",
        "suggestion": "What suggestions do you have to improve the Interest-based Generation Module?  ",
    },
    "open_exploration": {
        "advantage": "Is the Open-ended Exploration Module helpful to you? What advantages do you think it has?",
        "difficulty": "Did you have difficulties when using the Open-ended Exploration Module? What disadvantages do you think it has?",
        "suggestion": "What suggestions do you have to improve the Open-ended Exploration Module?  ",
    },
    "progressive_unfolding": {
        "advantage": "Is the Progressive Knowledge Unfolding Module helpful to you? What advantages do you think it has?",
        "difficulty": "Did you have difficulties when using the Progressive Knowledge Unfolding Module?What disadvantages do you think it has?",
        "suggestion": "What suggestions do you have to improve the  Progressive Knowledge Unfolding Module ?  ",
    },
    "programming_module": {
        "advantage": "Is the Programming Module  helpful to you? What advantages do you think it has?",
        "difficulty": "Did you have difficulties when using the Programming Module?What disadvantages do you think it has?",
        "suggestion": "What suggestions do you have to improve the Programming Module?  ",
    },
    "ai_teaching_assistant": {
        "advantage": "Is the Al Teaching Assistant Module  helpful to you? What advantages do you think it has?",
        "difficulty": "Did you have difficulties when using the Al Teaching Assistant Module?What disadvantages do you think it has?",
        "suggestion": "What suggestions do you have to improve the  Al Teaching Assistant Module?  ",
    },
}

SUS_ITEMS: List[ScaleItem] = [
    ScaleItem("SUS", "SUS_Q1", "I think that I would like to use this system frequently.  "),
    ScaleItem("SUS", "SUS_Q2", "I found the system unnecessarily complex.  "),
    ScaleItem("SUS", "SUS_Q3", "I thought the system was easy to use. "),
    ScaleItem("SUS", "SUS_Q4", "I think that I would need the support of a technical person to be able to use this system. "),
    ScaleItem("SUS", "SUS_Q5", "I found the various functions in this system were well integrated. "),
    ScaleItem("SUS", "SUS_Q6", "I thought there was too much inconsistency in this system. "),
    ScaleItem("SUS", "SUS_Q7", "I would imagine that most people would learn to use this system very quickly. "),
    ScaleItem("SUS", "SUS_Q8", "I found the system very cumbersome to use. "),
    ScaleItem("SUS", "SUS_Q9", "I felt very confident using the system. "),
    ScaleItem("SUS", "SUS_Q10", "I needed to learn a lot of things before I could get going with this system. "),
]

NASA_TLX_ITEMS: List[ScaleItem] = [
    ScaleItem("NASA_TLX", "NASA_Q1_MentalDemand", "  How much mental and perceptual activity was required (e.g., thinking, deciding, calculating, remembering, looking, searching, etc.)?  "),
    ScaleItem("NASA_TLX", "NASA_Q2_PhysicalDemand", "How much physical activity was required (e.g., pushing, pulling, turning, controlling, activating, etc.)? "),
    ScaleItem("NASA_TLX", "NASA_Q3_TemporalDemand", "How much time pressure did you feel due to the rate or pace at which the tasks occurred? "),
    ScaleItem("NASA_TLX", "NASA_Q4_Performance", "How successful do you think you were in accomplishing the goals of the task set by the experimenter (or yourself)? How satisfied were you with your performance in accomplishing these goals? "),
    ScaleItem("NASA_TLX", "NASA_Q5_Effort", "How hard did you have to work (mentally and physically) to accomplish your level of performance? "),
    ScaleItem("NASA_TLX", "NASA_Q6_Frustration", "How insecure, discouraged, irritated, stressed, and annoyed versus secure, gratified, content, relaxed, and complacent did you feel during the task? "),
]

SELF_EFFICACY_ITEMS: List[ScaleItem] = [
    ScaleItem("SelfEfficacy", "SE_Q1", "  I can understand the basic logical structure of HTML, CSS, and JavaScript code.  "),
    ScaleItem("SelfEfficacy", "SE_Q2", "  I can understand how conditional statements (e.g., if...else) work with AI support.  "),
    ScaleItem("SelfEfficacy", "SE_Q3", "I can predict the result of a JavaScript program when given specific input values. "),
    ScaleItem("SelfEfficacy", "SE_Q4", "  I can identify and correct errors in my HTML, CSS, or JavaScript code with the help of AI.  "),
    ScaleItem("SelfEfficacy", "SE_Q5", "I can understand error messages and AI-generated explanations when my code does not run correctly. "),
    ScaleItem("SelfEfficacy", "SE_Q6", "I can improve my programming skills by learning from AI debugging suggestions. "),
    ScaleItem("SelfEfficacy", "SE_Q7", "I can write a simple web page using HTML, CSS, and JavaScript with AI guidance. "),
    ScaleItem("SelfEfficacy", "SE_Q8", "I can use AI to help me apply loops, conditions, or functions in JavaScript. "),
    ScaleItem("SelfEfficacy", "SE_Q9", "I can combine AI suggestions with my own knowledge to solve a programming task. "),
    ScaleItem("SelfEfficacy", "SE_Q10", "I feel confident that I can complete programming exercises with AI support. "),
    ScaleItem("SelfEfficacy", "SE_Q11", "I believe I can continue learning web development effectively with AI assistance. "),
    ScaleItem("SelfEfficacy", "SE_Q12", "I can work more efficiently by dividing tasks between myself and AI (e.g., I focus on design, AI helps with debugging). "),
]


def load_raw() -> pd.DataFrame:
    if not RAW_PATH.exists():
        raise FileNotFoundError(f"Raw CSV not found at {RAW_PATH}")
    df = pd.read_csv(RAW_PATH)
    df = df.rename(columns=DEMOGRAPHIC_COLUMNS)
    df["participant_id"] = df["participant_id"].str.strip()
    df["group"] = (
        df["participant_id"]
        .str.lower()
        .str.extract(r"^(exp|baseline)", expand=False)
        .fillna("unknown")
    )
    df["timestamp_utc"] = parse_timestamp_series(df["Timestamp"])
    return df


def parse_timestamp_series(series: pd.Series) -> pd.Series:
    cleaned = (
        series.fillna("")
        .astype(str)
        .str.replace("GMT", "UTC", regex=False)
        .str.strip()
        .str.replace(
            r"(UTC)([+-])(\d{1,2})(?!\d)",
            lambda m: f"UTC{m.group(2)}{int(m.group(3)):02d}00",
            regex=True,
        )
    )
    parsed = pd.to_datetime(
        cleaned, errors="coerce", utc=True, format="%Y/%m/%d %I:%M:%S %p UTC%z"
    )
    return parsed


def build_participants_table(df: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "participant_id",
        "group",
        "Timestamp",
        "gender",
        "major",
        "years_programming",
        "education_level",
        "studied_frontend",
        "general_suggestion",
        "timestamp_utc",
    ]
    participants = df[cols].copy()
    participants.rename(
        columns={"Timestamp": "timestamp_local_raw"}, inplace=True
    )
    participants["timestamp_utc_iso"] = participants["timestamp_utc"].dt.strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    participants.sort_values(["group", "participant_id"], inplace=True)
    return participants


def build_module_feedback(df: pd.DataFrame) -> pd.DataFrame:
    records = []
    for module_key, question_map in MODULE_QUESTION_MAP.items():
        for question_type, column in question_map.items():
            for _, row in df[["participant_id", "group", column]].iterrows():
                text = row[column]
                if pd.isna(text):
                    continue
                text = str(text).strip()
                if not text:
                    continue
                records.append(
                    {
                        "participant_id": row["participant_id"],
                        "group": row["group"],
                        "module": module_key,
                        "question_type": question_type,
                        "question_text": column,
                        "response": text,
                    }
                )
    return pd.DataFrame.from_records(records)


def build_scale_responses(df: pd.DataFrame) -> pd.DataFrame:
    items = SUS_ITEMS + NASA_TLX_ITEMS + SELF_EFFICACY_ITEMS
    records = []
    for item in items:
        values = pd.to_numeric(df[item.column], errors="coerce")
        for idx, value in values.items():
            if pd.isna(value):
                continue
            records.append(
                {
                    "participant_id": df.at[idx, "participant_id"],
                    "group": df.at[idx, "group"],
                    "scale": item.scale,
                    "item_code": item.code,
                    "item_text": item.column.strip(),
                    "value": float(value),
                }
            )
    return pd.DataFrame.from_records(records)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df = load_raw()

    participants = build_participants_table(df)
    participants.to_csv(OUTPUT_DIR / "participants.csv", index=False)

    module_feedback = build_module_feedback(df)
    module_feedback.to_csv(OUTPUT_DIR / "module_feedback_long.csv", index=False)

    scale_responses = build_scale_responses(df)
    scale_responses.to_csv(OUTPUT_DIR / "scale_responses_long.csv", index=False)

    print("Saved:")
    print(f" - participants.csv ({len(participants)} rows)")
    print(f" - module_feedback_long.csv ({len(module_feedback)} rows)")
    print(f" - scale_responses_long.csv ({len(scale_responses)} rows)")


if __name__ == "__main__":
    main()
