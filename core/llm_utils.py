from transformers import pipeline

# Use Mistral-7B-Instruct
MODEL_NAME = "mistralai/Mistral-7B-Instruct-v0.1"

# Load pipeline with instruction tuning
generator = pipeline(
    "text-generation",
    model="microsoft/phi-2",  # or another open model
    torch_dtype="auto",
    device_map="auto",
    max_new_tokens=256,
    do_sample=True,
    temperature=0.7
)

def explain_log_entry(log_text):
    prompt = f"### Instruction: Explain this log entry as if to a junior sysadmin.\n### Input:\n{log_text}\n### Response:"
    result = generator(prompt)[0]['generated_text']
    # Remove the prompt portion if the model repeats it in the output
    if "### Response:" in result:
        return result.split("### Response:")[-1].strip()
    return result.strip()