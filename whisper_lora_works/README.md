# whisper lora works

## make manifest

이 과정은 학습하기위한 데이터셋의 메타정보를 담은 manifest 파일을 생성합니다.


```bash
python make_manifest.py --root ./datasets/Sample --wav_dir wav --label_dir lb
```

## train
```bash

torchrun --nproc_per_node=2 train_whisper_lora.py   --model_name "openai/whisper-large-v3"   --manifest "/home/agent01/works/dataset/71557/data/Training/manifest.jsonl"   --eval_manifest "/home/agent01/works/dataset/71557/data/Validation/manifest.jsonl"   --output_dir "outputs/large_v3_ddp"   --batch_size 32 --grad_accum 4 --fp16 --lr 1e-4   --use_gradient_checkpointing --max_audio_sec 30.0   --eval_steps 300  --max_steps 3000




 # 단일 GPU
python train_whisper_lora.py --model_name "openai/whisper-small" --manifest "datasets/Sample/manifest.jsonl" --output_dir "outputs/small_lora" --batch_size 16 --grad_accum 2 --max_steps 300 --fp16 --lr 1e-4
python train_whisper_lora.py --model_name "openai/whisper-small" --manifest "datasets/Sample/manifest.jsonl" --output_dir "outputs/small_lora" --batch_size 16 --grad_accum 2 --max_steps 300 --fp16 --lr 1e-4 --eval_manifest "datasets/Sample/manifest.jsonl" --eval_steps 50

# GPU 전력 제한 (옵션)
sudo nvidia-smi -i 1 -pl 280
```

## tensorboard
```bash
tensorboard --logdir outputs/large_v3_ddp_retry
```


## evaluate
```bash

python eval_dataset_lora.py --manifest datasets/Sample/manifest.jsonl --base_model openai/whisper-small --lora_dir outputs/small_lora --output_csv comparison_results.csv
python eval_dataset_lora.py --manifest /home/agent01/works/dataset/71557/data/Validation/manifest.jsonl --base_model openai/whisper-large-v3 --lora_dir outputs/large_v3_ddp --output_csv outputs/comparison_results.csv --max_samples 200

```

## merge lora weights to base model

```bash
 python merge_peft.py
```



## convert to ct2

추론 전용 모델로 변환 합니다.  

**--quantization int8_float16: 가중치는 8비트로 줄이고 연산은 16비트로 하여 속도와 정확도를 모두 잡습니다.**   

```bash
ct2-transformers-converter --model outputs/merged_small --output_dir outputs/ct2_small --quantization int8_float16 --force

```

