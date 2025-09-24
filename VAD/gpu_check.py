#%%
import torch
print(torch.__version__)
print(f'cuda is available {torch.cuda.is_available()}')

#%%
def check_torch_env():
    """
    PyTorch 환경(버전, CUDA, MPS, GPU 정보 등)을 확인하여 문자열로 반환하는 함수입니다.
    """
    import torch

    lines = []
    lines.append(f"PyTorch version: {torch.__version__}")
    lines.append(f"CUDA is available: {torch.cuda.is_available()}")
    
    # CUDA 관련 정보 출력
    if torch.cuda.is_available():
        lines.append(f"CUDA version: {torch.version.cuda}")
        count = torch.cuda.device_count()
        for i in range(count):
            lines.append(f"GPU {i}: {torch.cuda.get_device_name(i)}")
        lines.append(f"GPU count: {count}")
        try:
            a = torch.rand(3).to('cuda')
            lines.append(f"Sample tensor on CUDA: {a}")
        except Exception as e:
            lines.append(f"Error moving tensor to CUDA: {e}")
    else:
        lines.append("CUDA not available.")

    # MPS 관련 정보 출력
    lines.append(f"MPS built: {torch.backends.mps.is_built()}")
    lines.append(f"MPS available: {torch.backends.mps.is_available()}")
    # CUDA 빌드 여부 출력
    lines.append(f"CUDA built: {torch.backends.cuda.is_built()}")

    return "\n".join(lines)


if __name__ == "__main__":
    # 직접 실행할 때 환경 정보를 출력합니다.
    print(check_torch_env())
