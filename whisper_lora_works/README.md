# whisper lora works

## train
```bash
accelerate launch --num_processes 1 train_whisper_lora.py    --model_name openai/whisper-small    --manifest datasets/Sample/manifest.jsonl    --output_dir outputs/small_lora    --max_steps 20    --batch_size 2    --grad_accum 16

CUDA_VISIBLE_DEVICES=0,1 accelerate launch --num_processes 2 train_whisper_lora.py   --model_name openai/whisper-small   --manifest datasets/Sample/manifest.jsonl   --output_dir outputs/small_lora   --max_steps 20   --batch_size 12   --grad_accum 8   --fp16   --max_audio_sec 20


CUDA_VISIBLE_DEVICES=0,1 accelerate launch --num_processes 2 train_whisper_lora.py   --model_name openai/whisper-large-v3   --manifest datasets/Sample/manifest.jsonl   --output_dir outputs/largev3_lora   --max_steps 300   --batch_size 1   --grad_accum 32   --fp16   --max_audio_sec 8   --dataloader_workers 0

 CUDA_VISIBLE_DEVICES=1 accelerate launch --num_processes 1 train_whisper_lora.py   --model_name openai/whisper-large-v3   --manifest datasets/Sample/manifest.jsonl   --output_dir outputs/largev3_lora   --max_steps 300   --batch_size 16   --grad_accum 16   --fp16   --max_audio_sec 20   --use_gradient_checkpointing   --dataloader_workers 0

```
