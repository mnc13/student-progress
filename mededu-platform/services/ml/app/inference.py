import os
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

MODEL_ID = os.getenv("MODEL_ID", "google/medgemma-4b-it")

class MedModel:
    def __init__(self):
        self.tok = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
        self.model = AutoModelForCausalLM.from_pretrained(
            MODEL_ID, torch_dtype="auto", device_map="auto"
        )
        self.pipe = pipeline("text-generation", model=self.model, tokenizer=self.tok, max_new_tokens=256)

    def generate(self, prompt: str) -> str:
        return self.pipe(prompt)[0]["generated_text"]

_model = None
def get_model():
    global _model
    if _model is None:
        _model = MedModel()
    return _model
