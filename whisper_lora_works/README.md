# whisper lora works

## train
```bash
accelerate launch --num_processes 1 train_whisper_lora.py    --model_name openai/whisper-small    --manifest datasets/Sample/manifest.jsonl    --output_dir outputs/small_lora    --max_steps 20    --batch_size 2    --grad_accum 16

CUDA_VISIBLE_DEVICES=0,1 accelerate launch --num_processes 2 train_whisper_lora.py   --model_name openai/whisper-small   --manifest datasets/Sample/manifest.jsonl   --output_dir outputs/small_lora   --max_steps 20   --batch_size 12   --grad_accum 8   --fp16   --max_audio_sec 20

```
