# System instructions define the model's persona
SYSTEM_INSTRUCTION_EXPERT_PATHOLOGIST = "You are an expert pathologist."
SYSTEM_INSTRUCTION_NOTE_TAKER = "You are an expert pathologist creating a detailed note for a marked Region of Interest on a whole-slide image."
SYSTEM_INSTRUCTION_CONCISE_OBSERVER = "You are an expert pathologist observing a specific region of a whole-slide image."

# User-facing prompts for different tasks
PROMPT_GLOBAL_SUMMARY = """
Provide a concise overview of this whole-slide image. Focus on key pathological features, tissue types, and any apparent abnormalities. Keep the summary to a maximum of 150 words.
"""

PROMPT_SNAPSHOT_SUMMARY = """
Briefly describe the most salient features in this image tile. What are the immediate observations? Limit your response to 1-2 sentences or a few bullet points (max 40 words).
"""

PROMPT_ROI_NOTE = """
Analyze the provided image region. Describe the cellular morphology, tissue architecture, and any notable pathological findings. If applicable, suggest potential differential diagnoses or areas for further investigation. Be comprehensive but structured.
"""
