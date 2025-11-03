import tiktoken
import json

model_name = "gpt-4.1-nano"  # or whichever the identifier is
enc = tiktoken.encoding_for_model(model_name)

text_payload = json.dumps({"messages": "hello"}, ensure_ascii=False)
token_count = len(enc.encode(text_payload))
