from transformers import T5ForConditionalGeneration, T5Tokenizer
import torch

# ✅ Load model globally
print("🔹 Loading T5-small model for summarization...")
model_name = "t5-small"
tokenizer = T5Tokenizer.from_pretrained(model_name)
model = T5ForConditionalGeneration.from_pretrained(model_name)
print("✅ Model loaded successfully!")

def summarize_code_snippet(snippet: str) -> str:
    """Generate a concise natural language explanation for a code snippet."""
    try:
        prompt = "summarize this python function: " + snippet
        inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)
        summary_ids = model.generate(**inputs, max_length=50, num_beams=2)
        return tokenizer.decode(summary_ids[0], skip_special_tokens=True)
    except Exception as e:
        return f"Error generating summary: {e}"
