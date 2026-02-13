import torch

def check_gpu():
    if torch.cuda.is_available():
        num_gpus = torch.cuda.device_count()
        print(f"사용 가능한 GPU 수: {num_gpus}")
        for i in range(num_gpus):
            gpu_name = torch.cuda.get_device_name(i)
            total_mem = torch.cuda.get_device_properties(i).total_memory / (1024 ** 3)  # GB 단위
            print(f"GPU {i}: {gpu_name}, 메모리: {total_mem:.2f} GB")
    else:
        print("사용 가능한 GPU가 없습니다. CPU를 사용합니다.")
        print(f"CPU: {torch.get_num_threads()} threads")


def main() -> None:
    check_gpu()


if __name__ == "__main__":
    main()
