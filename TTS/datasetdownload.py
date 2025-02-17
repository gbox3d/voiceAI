#%%
from datasets import load_dataset
from datasets import load_from_disk

#%%
# "Bingsu/KSS_Dataset" 데이터셋 다운로드 및 로드
dataset = load_dataset("Bingsu/KSS_Dataset")

# 데이터셋의 구성 확인 (예: train/validation/test splits)
print(dataset)

# %%
print(dataset.cache_files)

# %%

# 저장된 Hugging Face 데이터셋 불러오기
dataset_path = "./datasets/Bingsu___kss_dataset"
dataset = load_dataset(dataset_path)

# 데이터셋 정보 확인
print(dataset)


# %%
# KSS Dataset 예시 (실제 경로/이름은 사용 중인 repo를 확인해주세요)
dataset = load_dataset("KSS_Dataset", data_dir="./") 
print(dataset)
# %%
