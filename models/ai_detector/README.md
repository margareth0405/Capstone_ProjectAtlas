# ATLAS AI detector files

Run this command from the project root on the development computer:

```powershell
python manage.py download_ai_model
```

The command downloads and validates the four deployment files from the pinned
`bsgcasa/ai-text-detector-distilbert` revision:

- `model_int8.onnx`
- `tokenizer.json`
- `tokenizer_config.json`
- `label_order.json`

Include those files in the repository or deployment artifact. Render must only
load them for inference; it must not download, export, or quantize a model at
startup.
