from transformers import T5ForConditionalGeneration, T5Tokenizer
import torch

# Load once globally (not inside the function)
print("🔹 Loading T5 model... (this will take a few seconds the first time)")
model_name = "t5-small"
tokenizer = T5Tokenizer.from_pretrained(model_name)
model = T5ForConditionalGeneration.from_pretrained(model_name)
print("✅ T5 model loaded successfully!")

def summarize_code_snippet(snippet: str) -> str:
    """
    Converts a code snippet into a short natural-language summary.
    """
    try:
        prompt = "summarize this python function: " + snippet
        inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)
        summary_ids = model.generate(**inputs, max_length=50, num_beams=2)
        return tokenizer.decode(summary_ids[0], skip_special_tokens=True)
    except Exception as e:
        return f"Error: {e}"
